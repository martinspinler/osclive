import threading

from dataclasses import dataclass
from typing import Union

@dataclass
class SLBaseChannel:
    index: Union[int, str]
    ctrls: dict

@dataclass
class SLInputChannel(SLBaseChannel):
    stereo: bool = False

@dataclass
class SLGeq(SLBaseChannel):
    pass

@dataclass
class SLFx(SLBaseChannel):
    pass

@dataclass
class SLMasters(SLBaseChannel):
    pass

@dataclass
class SLChannel:
    name: str
    info: Union[SLInputChannel, SLGeq, SLFx, SLMasters]


@dataclass
class SLType:
    pass

@dataclass
class SLTypeFloat(SLType):
    pass

@dataclass
class SLTypeGain(SLType):
    pass

@dataclass
class SLTypeInt(SLType):
    pass

# raw1394
@dataclass
class SLNibblePair:
    byte: int
    dataType: SLType = SLTypeFloat

@dataclass
class SLBit:
    byte: int
    bit: int


class SLBackend:
    def __init__(self, device):
        self.debug = False
        self.device = device
        self.update_thread = None
        self._stop_event = threading.Event()
        self.channels = {n: SLChannel(n, i) for n,i in self.device.channels.items()}

        for ch in self.channels.values():
            ch.ctrls = {n:None for n in ch.info.ctrls.keys()}
            ch.level = None
            ch.level = 0

    def set_listener(self, listener):
        self.listener = listener

    def connect(self):
        pass

    def disconnect(self):
        self._stop_event.set()
        if self.update_thread:
            self.update_thread.join()

    def _update_levels(self):
        for callback in self.listener.level_callbacks:
            callback()

    def set_control(self, ch, control, value):
        pass

    def _update_control(self, ch, control, value):
        if ch.ctrls[control] != value:
            ch.ctrls[control] = value
            if self.debug:
                print("StudioLive: Upd %-8s %-14s = %.3f" % (ch.name + ":", control, value))
            for callback in self.listener.update_callbacks:
                callback(ch.name, control, value)
            return True
        else:
            return False
