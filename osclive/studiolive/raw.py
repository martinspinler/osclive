from dataclasses import dataclass, field, KW_ONLY
from typing import Union

from .backend import SLChannel, SLTypeFloat, SLType


def dfl(data: list[int]) -> list[int]:
    return field(default_factory=lambda : data.copy())


def dfi(data: int) -> int:
    return field(default=data)


@dataclass
class SLNibblePair:
    byte: int
    dataType: type[SLType] = SLTypeFloat


@dataclass
class SLShortInt:
    byte: int


@dataclass
class SLBit:
    byte: int
    bit: int


C_INDEX = 0xBEEF


@dataclass
class RawBaseChannel:
    index: int
    ctrls: dict[str, Union[SLNibblePair, SLBit, SLShortInt]]
    levels: int = 0
    _: KW_ONLY
    read_id: list[int] = field(default_factory=list)
    resp_id: list[int] = field(default_factory=list)
    write_id: list[int] = field(default_factory=list)
    length: int = 0          # raw data length
    offset: int = 0          # raw data offset in SysEx message (offset 0 = 0xF0)

    def __post_init__(self) -> None:
        self.read_id[:] = [i if i != C_INDEX else self.index for i in self.read_id]
        self.resp_id[:] = [i if i != C_INDEX else self.index for i in self.resp_id]
        self.write_id[:] = [i if i != C_INDEX else self.index for i in self.write_id]


@dataclass
class RawInputChannel(RawBaseChannel):
    read_id: list[int] = dfl([0x6b, C_INDEX])
    resp_id: list[int] = dfl([0x6b, C_INDEX])
    write_id: list[int] = dfl([0x6a, C_INDEX])
    length: int = dfi(120)
    offset: int = dfi(3)


@dataclass
class RawGeq(RawBaseChannel):
    read_id: list[int] = dfl([0x6d, 0x01, C_INDEX])
    resp_id: list[int] = dfl([0x6c, 0x01, C_INDEX])
    write_id: list[int] = dfl([0x6c, 0x01, C_INDEX])
    length: int = dfi(64)
    offset: int = dfi(4)


@dataclass
class RawFx(RawBaseChannel):
    read_id: list[int] = dfl([0x6d, 0x03, C_INDEX])
    resp_id: list[int] = dfl([0x6c, 0x03, C_INDEX])
    write_id: list[int] = dfl([0x6c, 0x03, C_INDEX])
    length: int = dfi(15)
    offset: int = dfi(4)


@dataclass
class RawMidiConfig(RawBaseChannel):
    read_id: list[int] = dfl([0x54])
    resp_id: list[int] = dfl([0x54])
    write_id: list[int] = dfl([0x53])
    length: int = dfi(25)
    offset: int = dfi(2)


@dataclass
class RawStatus(RawBaseChannel):
    read_id: list[int] = dfl([0x38, 0x03]) # RD REQ ID bytes
    resp_id: list[int] = dfl([0x39, 0x03]) # Expected response ID bytes
    length: int = dfi(41) # Expected response length, without F0,F7 and ID bytes
    offset: int = dfi(3)


@dataclass
class RawFaders(RawBaseChannel):
    read_id: list[int] = dfl([0x6e])
    resp_id: list[int] = dfl([0x6e])
    length: int = dfi(41)
    offset: int = dfi(2)


@dataclass
class RawMasters(RawBaseChannel):
    read_id: list[int] = dfl([0x60])
    resp_id: list[int] = dfl([0x60])
    write_id: list[int] = dfl([0x6f])
    length: int = dfi(57)
    offset: int = dfi(2)

# Notes:
# Meters purpose / Fader locate: f0 6c 02 04 f7 | 1=Inputs, 2=Outputs, 3=GR, 4=Locate
# MIDI control: f0 53 00 00 00 00 00 00 00 00 00 00 00 00 07 0f 07 0f 07 0f 07 0f 07 0f 00 01 f7
# Change ACK  : f0 10 f7


@dataclass
class RawChannel(SLChannel):
    info: RawBaseChannel
    raw: list[int] = field(default_factory=list)


@dataclass
class RawStudioLiveDevice:
    channels: dict[str, RawBaseChannel]
    status_modified: dict[str, str]
