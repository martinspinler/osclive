import threading
import struct
import time
import raw1394

from dataclasses import dataclass
from .SLBackend import *


def _val_from_nibble_pair(data, dataType):
    value = (data[0] << 4 | data[1])# / 256
    if dataType in [SLTypeFloat, SLTypeGain]:
        # The raw value is in range 0 - 255
        value /= 255
    return value

def _val_to_nibble_pair(value, dataType):
    if dataType in [SLTypeFloat, SLTypeGain]:
        value = value * 255
    value = max(0, min(255, int(value)))
    return [(value >> 4) & 0x0F, (value >> 0) & 0x0F]

def _set_bit_val(data, byte, bit, val):
    if val:
        data[byte] |= (1 << bit)
    else:
        data[byte] &= (1 << bit) ^ 0xff

def _get_bit_val(data, byte, bit):
    return 1 if data[byte] & (1 << bit) else 0

class SLRaw1394Backend(SLBackend):
    def __init__(self, device):
        SLBackend.__init__(self, device.backends["raw1394"])

        self.lock = threading.Lock()
        self.raw1394 = None

        for ch in self.channels.values():
            ch.raw = None

        self.last_status = [0] * 0xc*4
        self.sel_channel = -1

    def _send_msg(self, wd):
        wa = 0xFFFFe0f00408
        self.raw1394.write(wa, bytearray(wd))
        #try:
        #    self.raw1394.write(wa, bytearray(wd))
        #except Exception as e:
        #    print(e)

    def _recv_msg(self, dwords, allow_fail = False):
        i = 0
        ra = 0xFFFFe0f0091c
        rd = list(self.raw1394.read(ra, dwords))
        while rd[0] == 0xfe and not allow_fail and i < 20:
            rd = list(self.raw1394.read(ra, dwords))
            i += 1
            time.sleep(0.002 if i < 8 else 0.1)
        if i > 15:
            assert False,"recv_msg - transfer error: 0xFE in the first byte (%d times)" % i
        return rd

    def _transceive_msg(self, write_data, read_dwords):
        assert len(write_data) > 0

        self.lock.acquire()
        data = None

        try:
            if self.raw1394 == None:
                raise SystemError("No raw1394, maybe StudioLive unexpectedly disconected?")
            self._send_msg(write_data)
            if read_dwords > 0:
                data = self._recv_msg(read_dwords*4)
        finally:
            self.lock.release()

        return data

    def _read_data(self, cmd, length, status = None):
        cmd = [0xf0] + cmd + [0xf7]
        if len(cmd) % 4:
            cmd += [0xf7] * (4 - len(cmd) % 4)
        data = self._transceive_msg(cmd, int((length + 2 + 3) / 4))
        if status:
            assert data[1] == status, "StudioLive: unexpected status for cmd %x: expected %x, got %x" % (cmd[0], status, data[1])
        assert data[length-1] == 0xF7, "StudioLive: no EOF byte for cmd %x" % (cmd[1])
        return data[:length-1]

    def _write_data(self, cmd, status = None):
        cmd = [0xf0] + cmd + [0xf7]
        data = self._transceive_msg(cmd, 1)
        if status:
            assert data[1] == status, "StudioLive: unexpected status for cmd %x: expected %x, got %x" % (cmd[0], status, data[1])
        assert data[2] == 0xF7, "StudioLive: no EOF byte for cmd %x" % (cmd[1])

    def _write_raw(self, cmd):
        cmd = [0xf0] + cmd + [0xf7]
        self._transceive_msg(cmd, 0)
        time.sleep(0.1)

    def _read_status(self):
        return self._read_data([0x38, 0x03], 47, 0x39)[:-2]

    def _read_faders(self):
        return self._read_data([0x6e], 0x0b*4, 0x6e)[2:-1]

    def route_source_1516(self, main_mix=False):
        if main_mix:
             # Route main mix output to FireWire stream 15/16
            self._write_raw([0x52, 0x13, 0x0e, 0x02, 0x00, 0x00, 0x00])
        else:
             # Route analog input 15/16 to FireWire stream 15/16
            self._write_raw([0x52, 0x13, 0x0e, 0x00, 0x0e, 0x00, 0x00])

    def _read_input_channel(self, ch):
        data = self._read_data([0x6b, ch.info.index], 124, 0x6b)
        assert data[2] == ch.info.index, "StudioLive: unexpected channel for cmd %x: expected %x, got %x" % (0x6b, ch, data[2])
        return data

    def _read_master(self):
        return self._read_data([0x60], 60, 0x60)

    def _read_fx(self, ch):
        return self._read_data([0x6d, 3, ch.info.index], 20, 0x6c)

    def _read_geq(self, ch):
        return self._read_data([0x6d, 1, ch.info.index], 69, 0x6c)

    def _write_input_channel(self, ch):
        self._write_data([0x6a] + ch.raw[2:-1], 0x10)

    def _write_geq(self, ch):
        self._write_data([0x6c] + ch.raw[2:-1], 0x10)

    def _write_fx(self, ch):
        self._write_data([0x6c] + ch.raw[2:-1], 0x10)

    def _write_master(self, ch):
        self._write_data([0x6f] + ch.raw[2:-1], 0x10)

    def _read_channel(self, ch):
        if type(ch.info) == SLInputChannel:
            return self._read_input_channel(ch)
        elif type(ch.info) == SLGeq:
            return self._read_geq(ch)
        elif type(ch.info) == SLFx:
            return self._read_fx(ch)
        elif type(ch.info) == SLMasters:
            return self._read_master()
        else:
            print("Unknown channel type to read")
            return [0]

    def _write_channel(self, ch):
        if type(ch.info) == SLInputChannel:
            self._write_input_channel(ch)
        elif type(ch.info) == SLGeq:
            self._write_geq(ch)
        elif type(ch.info) == SLFx:
            self._write_fx(ch)
        elif type(ch.info) == SLMasters:
            return self._write_master(ch)
        else:
            print("No write for channel:", ch)

    def _update_levels(self, levels):
        i = 0
        for ch in self.channels.values():
            if type(ch.info) == SLInputChannel:
                # TODO: Max value?
                if ch.info.stereo:
                    if i + 1 < len(levels):
                        ch.level = (levels[i], levels[i+1])
                    i += 2
                else:
                    if i < len(levels):
                        ch.level = levels[i]
                    i += 1
        super()._update_levels()

    def _update_faders(self, faders):
        for ch in self.channels.values():
            if type(ch.info) == SLInputChannel:
                control = "gain"
                value = _val_from_nibble_pair(faders[ch.info.index*2:ch.info.index*2+2], SLTypeGain)
                self._update_control(ch, control, value)

    def _update_channel(self, ch, data):
        handled = False

        for control, pos in ch.info.ctrls.items():
            if type(pos) == SLNibblePair:
                value = _val_from_nibble_pair(data[pos.byte:pos.byte+2], pos.dataType) 
            elif type(pos) == SLBit:
                value = _get_bit_val(data, pos.byte, pos.bit)
            else:
                print("StudioLive: Unknown control type")

            if self._update_control(ch, control, value):
                handled = True

        for i in range(len(data)):
            if self.debug and ch.raw and ch.raw[i] != data[i] and not handled:
                print("StudioLive: Channel %s change: byte %d, oldval = %x, newval = %x" % (ch.name, i, ch.raw[i], data[i]))
        ch.raw = data

    def _update_process(self):
        while not self._stop_event.is_set():
            try:
                #status = self._read_data([0x38, 0x03], 48, 0x39)
                status = self._read_status()
                self._update_levels(status[22:22+23])
                #print("xyz", status)

                #if self.debug and self.last_status != status:
                #    print("StudioLive: INDEX   ", " ".join("%02d" % b for b in range(64)))
                #    print("StudioLive: Status: ", " ".join("%02x" % b for b in status))

                #status[4]: Selected channel
                #if self.sel_channel != status[4]:
                #    self.sel_channel = status[4]
                #    print("Selected channel: %x" % self.sel_channel)

                #status[5]: Input/Output/GR/Locale buttons
                #if self.last_status[5] != status[5] and self.debug:
                #    print("Meters mode:", self.last_status[5])
                #    pass
                    
                #status[19]: (only) faders moved
                if status[19]:
                    self._update_faders(self._read_faders())
                #status[20]: GEQ button?

                for ch in self.channels.values():
                    if type(ch.info) in self.device.sbo:
                        byte = self.device.sbo[type(ch.info)] - int(ch.info.index / 4)
                        bit = ch.info.index % 4
                        if status[byte] & (1 << bit):
                            self._update_channel(ch, self._read_channel(ch))

                self.last_status = status
                time.sleep(0.1)

            except SystemError as e:
                self.raw1394 = None
                print("SystemError, trying connect_hw:", e)
                self.connect_hw()
            except Exception as e:
                print("Exception:", e)

    def set_control(self, ch, control, value):
        pos = ch.info.ctrls[control]
        if type(pos) == SLNibblePair:
            ch.raw[pos.byte:pos.byte + 2] = _val_to_nibble_pair(value, pos.dataType)
        elif type(pos) == SLBit:
            _set_bit_val(ch.raw, pos.byte, pos.bit, value >= 0.5)
        else:
            print("StudioLive: Unknown control type")

        try:
            self._write_channel(ch)
        except SystemError as ee:
            print("Device not responding, client request unsuccessfull.")
            #time.sleep(5)

    def connect(self):
        SLBackend.connect(self)
        assert not self.raw1394

        wait = True
        self.connect_hw()

        if not self.raw1394:
            raise SystemError("Device not found")

        self.update_thread = threading.Thread(target=self._update_process)
        self.update_thread.start()

    def connect_hw(self, wait = True):
        self.raw1394 = None
        while not self.raw1394:
            try:
                self.raw1394 = raw1394.Raw1394()
                self.init_data()
            except SystemError as ee:
                print("Device not found, trying again in 5 secs...")
                time.sleep(5)
            except RuntimeError as ee:
                print("Device not responding, trying again in 5 secs...")
                time.sleep(5)
            except:
                import sys
                print("Unexpected error:", sys.exc_info()[0])

            if not wait:
                break

        print("StudioLive: connected")

    def init_data(self):
        # Clean internal data register (from previous communication)
        tries = 0
        while self._recv_msg(0x01 * 4, True)[0] != 0xfe and tries < 100:
            tries += 1

        # Read state of all channels
        for ch in self.channels.values():
            self._update_channel(ch, self._read_channel(ch))
