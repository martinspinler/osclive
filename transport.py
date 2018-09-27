#!/usr/bin/env python
import os
import argparse
import tempfile
import queue
import sys
import threading
import queue
import threading

import sounddevice as sd
import soundfile as sf

class NullTransport():
	def __init__(self):
		pass
	def setStatusCallback(self, callback):
		pass
	def isPlaying(self):
		return False
	def isRecording(self):
		return False

	def playStart(self, filename):
		pass
	def playStop(self):
		pass
	def playSkip(self, seconds):
		pass

	def recStart(self, filename):
		pass
	def recStop(self):
		pass

class Transport():
	def __init__(self, device = "default", samplerate = 44100, channels = []):
		self.callbacks = []
		self.control = 0
		self.status = 0
		self.device = device
		self.samplerate = samplerate
		self.rq = queue.Queue()
		self.currentTime = 0
		self.channels = channels

		# Playback parameters
		self.buffersize = 4
		self.blocksize = 2048

		# TODO
		if self.device == "ASIO PreSonus FireStudio":
			self.asioSettings = sd.AsioSettings(self.channels)
		else:
			self.asioSettings = None

	def setStatusCallback(self, callback):
		self.callbacks += [callback]

	def isPlaying(self):
		return self.status == 2
	def isRecording(self):
		return self.status == 1

	def playStart(self, filename):
		if self.control != 0 or self.status != 0:
			return
		self.control = 2
		self.currentTime = 0
		self._playStart(filename)
	def playStop(self):
		assert self.control == 2
		self.control = 0
	def playSkip(self, seconds):
		if not self.isPlaying():
			return

		currentPos = self.fplay.tell()
		posDiff = seconds * self.samplerate
		if currentPos + posDiff > self.total:
			posDiff = self.total - currentPos
		elif currentPos + posDiff < 0:
			posDiff = -currentPos

		self.fplay.seek(posDiff, sf.SEEK_CUR)

	def _playStart(self, filename):
		self.pq = queue.Queue(maxsize=self.buffersize)
		event = threading.Event()

		with sf.SoundFile(filename) as f:
			f.seek(0, sf.SEEK_END)
			self.total = f.tell()
			f.seek(0, sf.SEEK_SET)

			self.fplay = f
			self.status = 2
			for _ in range(self.buffersize):
				data = f.buffer_read(self.blocksize, dtype='float32')
				if not data:
					break
				self.pq.put_nowait(data)  # Pre-fill queue

			stream = sd.RawOutputStream(
				samplerate=f.samplerate, blocksize=self.blocksize,
				device=self.device, channels=f.channels, dtype='float32',
				callback=self.playCallback, finished_callback=event.set)

			try:
				with stream:
					print("Start playing file", filename)
					timeout = self.blocksize * self.buffersize / f.samplerate
					while data and self.control == 2:
						data = f.buffer_read(self.blocksize, dtype='float32')
						self.pq.put(data, timeout=timeout)
						self.currentTime = f.tell()
					event.wait()  # Wait until playback is finished
					print("Stop playing")
			except queue.Full:
				print("Timeout occured in playback")

			self.fplay = None
			self.status = 0
			self.control = 0
			for cb in self.callbacks:
				cb()

	def recStart(self, filename):
		if self.control != 0 or self.status != 0:
			return
		self.control = 1
		self.currentTime = 0
		self.recThread = threading.Thread(target = self.recStartThread, kwargs = {"filename":filename}).start()
	def recStop(self):
		assert self.control == 1
		self.control = 0

	def recStartThread(self, filename):
		try:
			with sf.SoundFile(filename, mode='w', samplerate=self.samplerate, channels=len(self.channels)) as file:
				stream = sd.InputStream(samplerate=self.samplerate, device=self.device, channels=len(self.channels), callback=self.recCallback, extra_settings=self.asioSettings)
				with stream:
					self.status = 1
					print("Start recording to file", filename)
					while self.control == 1:
						file.write(self.rq.get())
					print("Stop recording")
					for cb in self.callbacks:
						cb()


		except Exception as e:
			print(e)
			self.status = 0

	def playCallback(self, outdata, frames, time, status):
		assert frames == self.blocksize
		if status.output_underflow:
			print('Output underflow: increase blocksize?', file=sys.stderr)
			raise sd.CallbackAbort
		assert not status
		try:
			data = self.pq.get_nowait()
		except queue.Empty:
			print('Buffer is empty: increase buffersize?', file=sys.stderr)
			raise sd.CallbackAbort

		if len(data) < len(outdata):
			outdata[:len(data)] = data
			outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
			raise sd.CallbackStop
		else:
			outdata[:] = data

		for cb in self.callbacks:
			cb()

	def recCallback(self, indata, frames, time, status):
		self.currerntTime = self.currentTime + frames
		if status:
			print(status, file=sys.stderr)
		self.rq.put(indata.copy())
		for cb in self.callbacks:
			cb()
