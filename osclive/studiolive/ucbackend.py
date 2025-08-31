import time
import threading
import struct
from socket import *

from .backend import SLBackend

def SLparsestr(s, n=None):
    assert b'\x00' in s
    if n is not None:
        assert len(s) == n
    return (s[:s.find(b'\x00')]).decode()

# UniversalControl backend: based on https://github.com/jeffkaufman/vsl1818
class SLUcBackend(SLBackend):

    def __init__(self, device, host, port = None, name = "SL-Remote", ident = "1BE8DC6BF62EA577B"):
        SLBackend.__init__(self, device.backends["uc"])

        self.host = host
        self.port = port if port else self.device.port
        self.ident = ident
        self.name = name

        self._connect_event = threading.Event()
        self.connection = None

        self._channel_int = {i.info.index: i for i in self.channels.values()}
        for ch in self.channels.values():
            ch.info._control_rev = {i:n for n,i in ch.info.ctrls.items()}

    # Low-level send & receive functions
    def recv(self, n):
        if not self.connection:
            return ""
        s = b""
        def remaining():
            return n-len(s)
        while remaining() > 0:
            s += self.connection.recv(remaining())
        return s

    def readmsg(self):
        signature, l = struct.unpack("II", self.recv(8))
        assert signature == 0xaa550011
        return self.recv(l)

    def sendmsg(self, message):
        if not self.connection:
            return
        self.connection.send(struct.pack("II", 0xaa550011, len(message)) + message)

    # Main functions
    def connect(self):
        assert not self.connection
        if not self.host:
            return
        self.connection = socket(AF_INET, SOCK_STREAM)
        print(self.host, self.port)
        self.connection.connect((self.host, self.port))
        self.sendmsg(struct.pack("IIHH32s32s", self.device.magic[0], self.device.magic[1], 3, self.device.magic[2], self.ident.encode(), self.name.encode()))

        print("StudioLive: starting update thread")
        self.update_thread = threading.Thread(target=self.update_process)
        self.update_thread.start()

        while not self._connect_event.is_set():
            time.sleep(0.1)

    def update(self, message_header, message_body):
        unknown1, unknown2, category, unknown3 = struct.unpack("IIHH", message_header)
        assert unknown1 == self.device.magic[0]
        assert unknown2 == self.device.magic[1]
        assert unknown3 == self.device.magic[2]

        if category == 5:
            self._connect_event.set()
            levels = struct.unpack("128B", message_body)

            i = 0
            for ch in self.channels.values():
                if ch.info.stereo:
                    ch.level = (levels[i], levels[i+1])
                    i += 2
                else:
                    ch.level = levels[i]
                    i += 1
            super()._update_levels()

        elif category == 4:
            unknown4, channel_id, channel_name = struct.unpack("HH48s", message_body)
            channel_name = SLparsestr(channel_name)

            assert unknown4 == 0
            #self.channel_names[channel_id] = channel_name
            #if(self.debug):
            #    print("StudioLive: recv channel ID %02d name: '%s'" % (channel_id, self.channel_names[channel_id]))

        elif category == 2:
            control_id, value, channel_id = struct.unpack("=Hd32s", message_body)
            channel_id = SLparsestr(channel_id)
            if(channel_id not in self._channel_int):
                print("StudioLive: recv control update for unknown channel %s" % channel_id)
                return

            channel = self._channel_int[channel_id]
            if(control_id not in channel.info._control_rev):
                print("StudioLive: recv unknown control update %d for channel %s with value %.2f" % (control_id, channel.name, value))
                return

            control = channel.info._control_rev[control_id]
            self._update_control(channel, control, value) # TODO!!!!!
            channel.ctrls[control] = value

        elif category == 7:
            print("StudioLive: recv unknown category %s, message size %d" % (category, len(message_body)))
            # Connected clients?
            pass
        elif category == 13:
            print("StudioLive: recv unknown category %s, message size %d" % (category, len(message_body)))
            # Number of presets from the disk?
            pass
        elif category == 14:
            print("StudioLive: recv unknown category %s, message size %d" % (category, len(message_body)))
            # Presets from the disk
            pass
        elif category == 17:
            print("StudioLive: recv unknown category %s, message size %d" % (category, len(message_body)))
            # New connected client?
            pass
        else:
            if self.debug:
                print("StudioLive: recv unknown category %s, message size %d" % (category, len(message_body)))
                #print(message_body)
            pass

    def update_process(self):
        assert self.connection
        while not self._stop_event.is_set():
            message = self.readmsg()
            self.update(message[:12], message[12:])

    def set_control(self, ch, control, value):
        if ch.name == "geq0":
            print("StudioLive: Upd control of channel %s is not supported" % ch)
            return
        header = struct.pack("IIHH", self.device.magic[0], self.device.magic[1], 2, self.device.magic[2])
        body = struct.pack("=Hd32s", ch.info.ctrls[control], value, ch.info.index.encode())
        self.sendmsg(header + body)
