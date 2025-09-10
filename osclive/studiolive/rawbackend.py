import sys
import threading
import time
import raw1394
import mido

from typing import Optional

from .backend import SLBackend, SLChannel, SLType, SLTypeGain, SLTypeFloat, SLValue
from .raw import RawBaseChannel, RawInputChannel, RawFaders, RawStatus

from .raw import RawChannel, RawStudioLiveDevice, SLNibblePair, SLBit, SLShortInt


def h(data: list[int]) -> str:
    return " ".join([f"{x:02x}" for x in data])


def _decode_raw(data: list[int], n: int) -> int:
    a6 = data[n*3+0]
    b6 = data[n*3+1]
    ca = (data[n*3+2] >> 0) & 0x3
    cb = (data[n*3+2] >> 2) & 0x3
    return (a6 << 0) | (b6 << 8) | (ca << 6) | (cb << 6 + 8)


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
        self._passive = False

        api = None

        self._portout = mido.open_output(self._output_port_name, client_name=self._client_name, virtual=self._virtual, api=api)
        self._portin = mido.open_input(self._input_port_name, client_name=self._client_name, virtual=self._virtual, api=api)

        self._in_buffer: list[int] = []
        self._portin.callback = self._input_callback

        self.write([0xf0, 0x33, 0xf7])
        self._read(10)

    def write(self, data: list[int]) -> None:
        if not self._passive:
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
        self._allchannels = {n: RawChannel(n, {n: 0 for n in i.ctrls.keys()}, i) for n, i in self.device.channels.items()}
        self.channels = {k: v for k, v in self._allchannels.items() if not k.startswith("_")}

        self._midi = midi

        self.lock = threading.Lock()
        self._adapter: Optional[AbstractAdapter] = None

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

    def _read_data(self, cmd: list[int], length: int, status: list[int]) -> list[int]:
        cmd = [0xf0] + cmd + [0xf7]
        length += 2
        data = self._transceive_msg(cmd, (length + 2))
        assert data[1:len(status) + 1] == status, f"StudioLive: unexpected status for cmd {cmd} expected {status}, got {data[1:len(status) + 1]}"
        #assert data[length + 1] == 0xf7, "StudioLive: no EOF byte for cmd %x, %x" % (cmd[1], data[length+1])
        #assert len(data) == (length + len(status))
        return data[1+len(status):len(status) + length-1]

    def _write_data(self, cmd: list[int], status: Optional[int] = None) -> None:
        cmd = [0xf0] + cmd + [0xf7]
        data = self._transceive_msg(cmd, 1)
        if status:
            assert data[1] == status, "StudioLive: unexpected status for cmd %x: expected %x, got %x" % (cmd[0], status, data[1])
        assert data[2] == 0xf7, "StudioLive: no EOF byte for cmd %x" % (cmd[1])

    def _write_raw(self, cmd: list[int]) -> None:
        cmd = [0xf0] + cmd + [0xf7]
        self._transceive_msg(cmd, 0) # FIXME: Check for ACK?
        time.sleep(0.1)

    def route_source_1516(self, main_mix: bool = False) -> None:
        if main_mix:
            # Route main mix output to FireWire stream 15/16
            self._write_raw([0x52, 0x13, 0x0e, 0x02, 0x00, 0x00, 0x00])
        else:
            # Route analog input 15/16 to FireWire stream 15/16
            self._write_raw([0x52, 0x13, 0x0e, 0x00, 0x0e, 0x00, 0x00])

    def _rd_channel(self, ch: RawBaseChannel) -> list[int]:
        assert ch.read_id
        assert ch.resp_id
        return self._read_data(ch.read_id, ch.length, ch.resp_id)

    def _wr_channel(self, ch: RawChannel) -> None:
        assert isinstance(ch.info, RawBaseChannel)
        assert ch.info.write_id

        self._write_data(ch.info.write_id + ch.raw + [0], 0x10)

    def _update_levels_from_status(self, levels: list[int]) -> None:
        i = 0

        levels = levels[19:19 + 23]

        for ch in self.channels.values():
            assert isinstance(ch, RawChannel)
            if isinstance(ch.info, RawInputChannel) and ch.info.levels:
                # TODO: Max value?
                if ch.info.levels == 2:
                    if i + 1 < len(levels):
                        ch.level = (levels[i], levels[i + 1])
                    i += 2
                else:
                    if i < len(levels):
                        ch.level = levels[i]
                    i += 1
        super()._update_levels()

    def _update_faders(self, data: list[int]) -> None:
        for name, ch in self.channels.items():
            assert isinstance(ch, RawChannel)
            if isinstance(ch.info, RawInputChannel):
                control = "gain"
                b = ch.info.index
                value = _val_from_nibble_pair(data[b * 2: b * 2 + 2], SLTypeGain)
                self._update_control(ch, control, value)

    def _update_channel(self, ch: RawChannel, data: list[int]) -> None:
        handled = False

        if len(data) != ch.info.length:
            print("_update_channel data length mismatch:", type(ch.info), data, len(data), ch.info.length)
            return

        if isinstance(ch.info, RawFaders):
            return self._update_faders(data)
        elif isinstance(ch.info, RawStatus):
            self._update_levels_from_status(data)

        for control, pos in ch.info.ctrls.items():
            b = pos.byte - ch.info.offset
            if isinstance(pos, SLNibblePair):
                value = _val_from_nibble_pair(data[b:b + 2], pos.dataType)
            elif isinstance(pos, SLShortInt):
                value = data[b:b + 1][0]
            elif isinstance(pos, SLBit):
                value = _get_bit_val(data, b, pos.bit)
            else:
                print("StudioLive: Unknown control type")

            if self._update_control(ch, control, value):
                handled = True

        for i in range(len(data)):
            if self.debug and ch.raw and ch.raw[i] != data[i] and not handled:
                print("StudioLive: Channel %s change: byte %d, oldval = %x, newval = %x" % (ch.name, i, ch.raw[i], data[i]))
        ch.raw = data

    def _readonly_update(self) -> None:
        channels: dict[str, RawChannel] = {k: v for k, v in self._allchannels.items() if isinstance(v, RawChannel)}

        while not self._stop_event.is_set():
            assert isinstance(self._adapter, MidiAdapter)
            data = self._adapter._read(1e12)
            size = len(data)
            assert data[size - 1] == 0xf7, "StudioLive: no EOF byte"

            echo = True

            match = False
            for name, ch in channels.items():
                assert ch.info.resp_id, ch.info

                if ch.info.read_id and ch.info.read_id == data[1:1+len(ch.info.read_id)]:
                    match = True
                if ch.info.resp_id and ch.info.resp_id == data[1:1+len(ch.info.resp_id)]:
                    match = True
                if ch.info.write_id and ch.info.write_id == data[1:1+len(ch.info.write_id)]:
                    match = True

                if match:
                    raw = data[:-1][ch.info.offset:ch.info.offset + ch.info.length]

                    if isinstance(ch.info, RawStatus):
                        echo = False

                    if echo:
                        print(type(ch.info), f"{len(data)}/{len(raw)}:", h(data[:ch.info.offset]), ">", h(raw), "<", h(data[ch.info.offset + len(raw):]))

                    if len(raw):
                        self._update_channel(ch, raw)
                    break

            match |= self._check_for_raw(data)

    def _update_process(self) -> None:
        if isinstance(self._adapter, MidiAdapter) and self._adapter._passive:
            self._readonly_update()
            return

        ch_status = self._allchannels["_status"]
        while not self._stop_event.is_set():
            try:
                status = self._rd_channel(ch_status.info)
                self._update_channel(ch_status, status)

                for mod_ctrl, ch_name in self.device.status_modified.items():
                    if ch_status.ctrls[mod_ctrl]:
                        ch = self._allchannels[ch_name]
                        self._update_channel(ch, self._rd_channel(ch.info))

                time.sleep(0.1)

            except SystemError as e:
                self._adapter = None
                print("SystemError, trying connect_hw:", e)
                self.connect_hw()

    def _check_for_raw(self, data: list[int]) -> bool:
        if data[1:3] == [0x2e, 0x40] or data[1:3] == [0x2e, 0x20]:
            rawdump = []
            rd = [_decode_raw(data, n) for n in range((len(data)-4)//3)]
            for n in rd:
                rawdump.append((n >> 0) & 0xFF)
                rawdump.append((n >> 8) & 0xFF)
            print("RD", "".join([f"{x:02x}" for x in rawdump]))
            if True:
                print("RC", " ".join([chr(n) if (
                    n >= ord('a') and n <= ord('z') or
                    n >= ord('A') and n <= ord('Z') or
                    n >= ord('0') and n <= ord('9') or
                    False
                ) else "_" for n in rawdump]))
            return True
        return False

    def set_control(self, ch: SLChannel, control: str, value: SLValue) -> None:
        assert isinstance(ch, RawChannel)
        pos = ch.info.ctrls[control]
        b = pos.byte - ch.info.offset
        if isinstance(pos, SLNibblePair):
            ch.raw[b:b + 2] = _val_to_nibble_pair(value, pos.dataType)
        elif isinstance(pos, SLShortInt):
            ch.raw[b:b + 1] = [int(value)]
        elif isinstance(pos, SLBit):
            _set_bit_val(ch.raw, b, pos.bit, value >= 0.5)
        else:
            print("StudioLive: Unknown control type")

        try:
            self._wr_channel(ch)
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
                print("Unexpected error:", sys.exc_info()[0])
                raise

            if not wait:
                break

        print("StudioLive: connected")

    def init_data(self) -> None:
        if isinstance(self._adapter, MidiAdapter) and self._adapter._passive:
            return

        # Read state of all channels
        for ch in self.channels.values():
            assert isinstance(ch, RawChannel)
            self._update_channel(ch, self._rd_channel(ch.info))
