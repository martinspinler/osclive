import threading
import time
import raw1394
import mido

from typing import Optional

from .backend import SLBackend, SLChannel, SLType, SLTypeGain, SLTypeFloat, SLValue
#from .backend import SLInputChannel, SLGeq, SLFx, SLMasters, SLInputChannel, SLGeq, SLFx, SLMasters, SLInputChannel, SLNibblePair
from .raw import RawInputChannel, RawGeq, RawFx, RawMasters

from .raw import RawChannel, RawStudioLiveDevice, SLNibblePair, SLBit


def _val_from_nibble_pair(data: list[int], dataType: type[SLType]) -> float:
    value: float
    value = (data[0] << 4 | data[1])
    if dataType in [SLTypeFloat, SLTypeGain]:
        # The raw value is in range 0 - 255
        value /= 255
    return value


def _val_to_nibble_pair(value: float, dataType: type[SLType]) -> list[int]:
    if dataType in [SLTypeFloat, SLTypeGain]:
        value = value * 255
    value = max(0, min(255, int(value)))
    return [(value >> 4) & 0x0F, (value >> 0) & 0x0F]


def _set_bit_val(data: list[int], byte: int, bit: int, val: bool) -> None:
    if val:
        data[byte] |= (1 << bit)
    else:
        data[byte] &= (1 << bit) ^ 0xff


def _get_bit_val(data: list[int], byte: int, bit: int) -> int:
    return 1 if data[byte] & (1 << bit) else 0


class AbstractAdapter():
    def write(self, wd: list[int]) -> None:
        raise NotImplementedError

    def read(self, num_bytes: int) -> list[int]:
        raise NotImplementedError


class PortNotFoundError(SystemError):
    pass


class MidiAdapter(AbstractAdapter):
    def __init__(self, name: str) -> None:
        self._portout: mido.ports.BaseOutput
        self._portin: mido.ports.BaseInput
        self._port_name = name

        def findSubstr(strings: list[str], substr: str) -> str:
            for i in strings:
                if substr in i:
                    return i
            raise PortNotFoundError(f'MIDI port {substr} not found in: ' + ", ".join(strings))
        self._input_port_name = findSubstr(mido.get_input_names(), self._port_name)
        self._output_port_name = findSubstr(mido.get_output_names(), self._port_name)

        self._client_name = None
        self._virtual = False

        api = None

        self._portout = mido.open_output(self._output_port_name, client_name=self._client_name, virtual=self._virtual, api=api)
        self._portin = mido.open_input(self._input_port_name, client_name=self._client_name, virtual=self._virtual, api=api)

        self._in_buffer: list[int] = []
        self._portin.callback = self._input_callback

        self.write([0xf0, 0x33, 0xf7])
        self._read(10)

    def write(self, data: list[int]) -> None:
        msg = mido.Message.from_bytes(bytes(data))
        self._portout.send(msg)

    def read(self, num_bytes: int) -> list[int]:
        return self._read()

    def _read(self, timeout: float = 2) -> list[int]:
        tm = time.time() + timeout

        while 0xf7 not in self._in_buffer:
            if time.time() > tm:
                raise SystemError()
            time.sleep(0.01)

        pos = self._in_buffer.index(0xf7)
        b = self._in_buffer[:pos + 1]
        self._in_buffer[:pos + 1] = []
        return list(b)

    def _input_callback(self, msg: mido.Message) -> None:
        if msg.type == 'sysex':
            self._in_buffer += [0xf0] + list(msg.data[:]) + [0xf7]


class Raw1394Adapter(AbstractAdapter):
    def __init__(self) -> None:
        self._handle = raw1394.Raw1394()

        # Clean internal data register (from previous communication)
        retries = 0
        while self._recv_msg(0x01, True)[0] != 0xfe and retries < 100:
            retries += 1

    def write(self, wd: list[int]) -> None:
        if len(wd) % 4:
            wd += [0xf7] * (4 - len(wd) % 4)
        wa = 0xFFFFe0f00408
        self._handle.write(wa, bytearray(wd))

    def read(self, num_bytes: int) -> list[int]:
        return self._recv_msg(num_bytes)

    def _recv_msg(self, read_bytes: int, allow_fail: bool = False) -> list[int]:
        aligned_bytes = int((read_bytes + 3) / 4) * 4
        i = 0
        ra = 0xFFFFe0f0091c
        rd = list(self._handle.read(ra, aligned_bytes))
        while rd[0] == 0xfe and not allow_fail and i < 20:
            rd = list(self._handle.read(ra, aligned_bytes))
            i += 1
            time.sleep(0.002 if i < 8 else 0.1)
        if i > 15:
            raise Exception("recv_msg - transfer error: 0xFE in the first byte (%d times)" % i)
        return rd


class SLRawBackend(SLBackend):
    def __init__(self, device: type[RawStudioLiveDevice], midi: Optional[str] = None) -> None:
        super().__init__()
        self.device = device
        self.channels = {n: RawChannel(n, {n: 0 for n in i.ctrls.keys()}, i) for n, i in self.device.channels.items()}

        self._midi = midi

        self.lock = threading.Lock()
        self._adapter: Optional[AbstractAdapter] = None

        self.last_status = [0] * 0xc*4
        self.sel_channel = -1

    def _transceive_msg(self, write_data: list[int], read_bytes: int) -> list[int]:
        assert len(write_data) > 0

        self.lock.acquire()
        data: list[int] = []

        try:
            if self._adapter is None:
                raise SystemError("No raw1394, maybe StudioLive unexpectedly disconected?")
            self._adapter.write(write_data)
            if read_bytes > 0:
                data = self._adapter.read(read_bytes)
        finally:
            self.lock.release()

        return data

    def _read_data(self, cmd: list[int], length: int, status: Optional[int] = None) -> list[int]:
        cmd = [0xf0] + cmd + [0xf7]
        data = self._transceive_msg(cmd, int((length + 2)))
        if status:
            assert data[1] == status, "StudioLive: unexpected status for cmd %x: expected %x, got %x" % (cmd[0], status, data[1])
        assert data[length+1] == 0xf7, "StudioLive: no EOF byte for cmd %x" % (cmd[1])
        return data[:length+1]

    def _write_data(self, cmd: list[int], status: Optional[int] = None) -> None:
        cmd = [0xf0] + cmd + [0xf7]
        data = self._transceive_msg(cmd, 1)
        if status:
            assert data[1] == status, "StudioLive: unexpected status for cmd %x: expected %x, got %x" % (cmd[0], status, data[1])
        assert data[2] == 0xf7, "StudioLive: no EOF byte for cmd %x" % (cmd[1])

    def _write_raw(self, cmd: list[int]) -> None:
        cmd = [0xf0] + cmd + [0xf7]
        self._transceive_msg(cmd, 0)
        time.sleep(0.1)

    def _read_status(self) -> list[int]:
        return self._read_data([0x38, 0x03], 45, 0x39)[:-2]

    def _read_faders(self) -> list[int]:
        return self._read_data([0x6e], 42, 0x6e)[2:-1]

    def route_source_1516(self, main_mix: bool = False) -> None:
        if main_mix:
            # Route main mix output to FireWire stream 15/16
            self._write_raw([0x52, 0x13, 0x0e, 0x02, 0x00, 0x00, 0x00])
        else:
            # Route analog input 15/16 to FireWire stream 15/16
            self._write_raw([0x52, 0x13, 0x0e, 0x00, 0x0e, 0x00, 0x00])

    def _read_input_channel(self, ch: RawChannel) -> list[int]:
        data = self._read_data([0x6b, ch.info.index], 122, 0x6b)
        assert data[2] == ch.info.index, "StudioLive: unexpected channel for cmd %x: expected %x, got %x" % (0x6b, ch.info.index, data[2])
        return data

    def _read_master(self) -> list[int]:
        return self._read_data([0x60], 58, 0x60)

    def _read_fx(self, ch: RawChannel) -> list[int]:
        return self._read_data([0x6d, 3, ch.info.index], 18, 0x6c)

    def _read_geq(self, ch: RawChannel) -> list[int]:
        return self._read_data([0x6d, 1, ch.info.index], 67, 0x6c)

    def _write_input_channel(self, ch: RawChannel) -> None:
        self._write_data([0x6a] + ch.raw[2:-1], 0x10)

    def _write_geq(self, ch: RawChannel) -> None:
        self._write_data([0x6c] + ch.raw[2:-1], 0x10)

    def _write_fx(self, ch: RawChannel) -> None:
        self._write_data([0x6c] + ch.raw[2:-1], 0x10)

    def _write_master(self, ch: RawChannel) -> None:
        self._write_data([0x6f] + ch.raw[2:-1], 0x10)

    def _read_channel(self, ch: RawChannel) -> list[int]:
        if isinstance(ch.info, RawInputChannel):
            return self._read_input_channel(ch)
        elif isinstance(ch.info, RawGeq):
            return self._read_geq(ch)
        elif isinstance(ch.info, RawFx):
            return self._read_fx(ch)
        elif isinstance(ch.info, RawMasters):
            return self._read_master()
        else:
            print("Unknown channel type to read")
            return [0]

    def _write_channel(self, ch: RawChannel) -> None:
        if isinstance(ch.info, RawInputChannel):
            self._write_input_channel(ch)
        elif isinstance(ch.info, RawGeq):
            self._write_geq(ch)
        elif isinstance(ch.info, RawFx):
            self._write_fx(ch)
        elif isinstance(ch.info, RawMasters):
            return self._write_master(ch)
        else:
            print("No write for channel:", ch)

    def _update_levels_from_status(self, levels: list[int]) -> None:
        i = 0
        for ch in self.channels.values():
            assert isinstance(ch, RawChannel)
            if isinstance(ch.info, RawInputChannel):
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

    def _update_faders(self, faders: list[int]) -> None:
        for ch in self.channels.values():
            assert isinstance(ch, RawChannel)
            if isinstance(ch.info, RawInputChannel):
                control = "gain"
                value = _val_from_nibble_pair(faders[ch.info.index*2:ch.info.index*2+2], SLTypeGain)
                self._update_control(ch, control, value)

    def _update_channel(self, ch: RawChannel, data: list[int]) -> None:
        handled = False

        for control, pos in ch.info.ctrls.items():
            if isinstance(pos, SLNibblePair):
                value = _val_from_nibble_pair(data[pos.byte:pos.byte+2], pos.dataType)
            elif isinstance(pos, SLBit):
                value = _get_bit_val(data, pos.byte, pos.bit)
            else:
                print("StudioLive: Unknown control type")

            if self._update_control(ch, control, value):
                handled = True

        for i in range(len(data)):
            if self.debug and ch.raw and ch.raw[i] != data[i] and not handled:
                print("StudioLive: Channel %s change: byte %d, oldval = %x, newval = %x" % (ch.name, i, ch.raw[i], data[i]))
        ch.raw = data

    def _update_process(self) -> None:
        while not self._stop_event.is_set():
            try:
                #status = self._read_data([0x38, 0x03], 48, 0x39)
                status = self._read_status()
                self._update_levels_from_status(status[22:22+23])
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
                    assert isinstance(ch, RawChannel)
                    #ch: RawChannel = channel
                    if type(ch.info) in self.device.sbo:
                        byte = self.device.sbo[type(ch.info)] - int(ch.info.index / 4)
                        bit = ch.info.index % 4
                        if status[byte] & (1 << bit):
                            self._update_channel(ch, self._read_channel(ch))

                self.last_status = status
                time.sleep(0.1)

            except SystemError as e:
                self._adapter = None
                print("SystemError, trying connect_hw:", e)
                self.connect_hw()
            except Exception as e:
                print("Exception:", e)
                raise

    def set_control(self, ch: SLChannel, control: str, value: SLValue) -> None:
        assert isinstance(ch, RawChannel)
        pos = ch.info.ctrls[control]
        if isinstance(pos, SLNibblePair):
            ch.raw[pos.byte:pos.byte + 2] = _val_to_nibble_pair(value, pos.dataType)
        elif isinstance(pos, SLBit):
            _set_bit_val(ch.raw, pos.byte, pos.bit, value >= 0.5)
        else:
            print("StudioLive: Unknown control type")

        try:
            self._write_channel(ch)
        except SystemError:
            print("Device not responding, client request unsuccessfull.")
            #time.sleep(5)

    def connect(self) -> None:
        SLBackend.connect(self)
        assert not self._adapter

        self.connect_hw()

        if not self._adapter:
            raise SystemError("Device not found")

        self.update_thread = threading.Thread(target=self._update_process)
        self.update_thread.start()

    def connect_hw(self, wait: bool = True) -> None:
        self._adapter = None
        while not self._adapter:
            try:
                if self._midi:
                    self._adapter = MidiAdapter(self._midi)
                else:
                    self._adapter = Raw1394Adapter()
                self.init_data()
            except SystemError:
                print("Device not found, trying again in 5 secs...")
                time.sleep(5)
            except RuntimeError:
                print("Device not responding, trying again in 5 secs...")
                time.sleep(5)
            except Exception:
                import sys
                print("Unexpected error:", sys.exc_info()[0])
                raise

            if not wait:
                break

        print("StudioLive: connected")

    def init_data(self) -> None:
        # Read state of all channels
        for ch in self.channels.values():
            assert isinstance(ch, RawChannel)
            self._update_channel(ch, self._read_channel(ch))
