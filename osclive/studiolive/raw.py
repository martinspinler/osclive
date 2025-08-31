from dataclasses import dataclass, field
from typing import Union

from .backend import SLChannel, SLTypeFloat, SLType


@dataclass
class SLNibblePair:
    byte: int
    dataType: type[SLType] = SLTypeFloat


@dataclass
class SLBit:
    byte: int
    bit: int


@dataclass
class RawBaseChannel:
    index: int
    ctrls: dict[str, Union[SLNibblePair, SLBit]]
    stereo: bool = False


@dataclass
class RawInputChannel(RawBaseChannel):
    pass


@dataclass
class RawGeq(RawBaseChannel):
    pass


@dataclass
class RawFx(RawBaseChannel):
    pass


@dataclass
class RawMasters(RawBaseChannel):
    pass


@dataclass
class RawChannel(SLChannel):
    info: RawBaseChannel
    raw: list[int] = field(default_factory=list)


@dataclass
class RawStudioLiveDevice:
    channels: dict[str, RawBaseChannel]
    sbo: dict[type[RawBaseChannel], int]
