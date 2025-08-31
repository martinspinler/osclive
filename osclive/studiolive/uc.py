from dataclasses import dataclass, field
from typing import Optional

from .backend import SLBaseChannel, SLChannel


@dataclass
class UCBaseChannel(SLBaseChannel):
    name: str
    info: SLBaseChannel
    ctrls: dict[str, Optional[int]]
    level: int | tuple[int, int] = 0


@dataclass
class UCInputChannel:
    name: str
    ctrls: dict[str, int]
    stereo: bool = False
    _control_rev: dict[int, str] = field(init=False)

    def __post_init__(self) -> None:
        self._control_rev = {i: n for n, i in self.ctrls.items()}


@dataclass
class UCGeq(UCBaseChannel):
    pass


@dataclass
class UCFx(UCBaseChannel):
    pass


@dataclass
class UCMasters(UCBaseChannel):
    pass


@dataclass
class UCChannel(SLChannel):
    #name: str
    info: UCInputChannel
    #ctrls: dict[str, Optional[int]]
    #level: int | tuple[int, int] = 0


@dataclass
class UCStudioLiveDevice:
    port: int
    channels: dict[str, UCInputChannel]
    magic: tuple[int, int, int]
