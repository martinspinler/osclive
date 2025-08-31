import threading

from dataclasses import dataclass, KW_ONLY
from typing import Optional, Callable

type SLValue = float

type SLUpdateCallback = Callable[[str, str, SLValue], None]
type SLLevelCallback = Callable[[], None]


@dataclass
class SLBaseChannel:
    pass


@dataclass
class SLChannel:
    name: str
    #info: SLBaseChannel
    ctrls: dict[str, SLValue]
    _: KW_ONLY
    level: int | tuple[int, int] = 0


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


class SLListener():
    update_callbacks: list[SLUpdateCallback] # Ch name, control, value
    level_callbacks: list[SLLevelCallback]


class SLBackend:
    def __init__(self) -> None:
        self.debug = False
        self.update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.channels: dict[str, SLChannel]

    def set_listener(self, listener: SLListener) -> None:
        self.listener = listener

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        self._stop_event.set()
        if self.update_thread:
            self.update_thread.join()

    def _update_levels(self) -> None:
        for callback in self.listener.level_callbacks:
            callback()

    def set_control(self, ch: SLChannel, control: str, value: SLValue) -> None:
        pass

    def _update_control(self, ch: SLChannel, control: str, value: SLValue) -> bool:
        if ch.ctrls[control] != value:
            ch.ctrls[control] = value
            if self.debug:
                print("StudioLive: Upd %-8s %-14s = %.3f" % (ch.name + ":", control, value))
            for callback in self.listener.update_callbacks:
                callback(ch.name, control, value)
            return True
        else:
            return False


class StudioLiveDevice:
    pass
