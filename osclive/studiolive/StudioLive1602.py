from dataclasses import dataclass

from .SLBackend import *

SL1602EqFreqs = [
    "20Hz",
    "25Hz",
    "32Hz",
    "40Hz",
    "50Hz",
    "63Hz",
    "80Hz",
    "100Hz",
    "125Hz",
    "160Hz",
    "200Hz",
    "250Hz",
    "320Hz",
    "400Hz",
    "500Hz",
    "640Hz",
    "800Hz",
    "1.0kHz",
    "1.3kHz",
    "1.6kHz",
    "2.0kHz",
    "2.5kHz",
    "3.2kHz",
    "4.0kHz",
    "5.0kHz",
    "6.4kHz",
    "8.0kHz",
    "10kHz",
    "13kHz",
    "16kHz",
    "20kHz",
]

SL1602CtrlsIn_raw1394 = {
    "gain":             SLNibblePair(3, SLTypeGain),
    "pan":              SLNibblePair(5),
    "linkedpan":        SLNibblePair(7),
    "aux1":             SLNibblePair(9),
    "aux2":             SLNibblePair(11),
    "aux3":             SLNibblePair(13),
    "aux4":             SLNibblePair(15),
    "fxa":              SLNibblePair(29),
    "fxb":              SLNibblePair(31),
    "hpf":              SLBit(107, 0),
    "hpffreq":          SLNibblePair(45),
    "gate":             SLBit(108, 3),
    "gatethresh":       SLNibblePair(85),
    "phantom":          SLBit(112, 0),
    "firewire":         SLBit(112, 1),
    "phase":            SLBit(112, 2),
    "post":             SLBit(112, 3),
    "mute":             SLBit(114, 0),
    "solo":             SLBit(114, 1),

    "comp":             SLBit(109, 1),
    "compauto":         SLBit(109, 2),
    "complimit":        SLBit(108, 0),
    "compthresh":       SLNibblePair(71),
    "compratio":        SLNibblePair(73),
    "compresponse":     SLNibblePair(75),
    "compgain":         SLNibblePair(79),

    "eqlow":            SLBit(110, 1),
    "eqmid":            SLBit(110, 3),
    "eqhigh":           SLBit(109, 0),
    "eqlowshelf":       SLBit(111, 0),
    "eqmidhiq":         SLBit(111, 2),
    "eqhighshelf":      SLBit(111, 3),
    "eqlowfreq":        SLNibblePair(47),
    "eqmidfreq":        SLNibblePair(51),
    "eqhighfreq":       SLNibblePair(53),
    "eqlowgain":        SLNibblePair(63),
    "eqmidgain":        SLNibblePair(67),
    "eqhighgain":       SLNibblePair(69),

    "toMain":           SLBit(113, 3)
}

SL1602CtrlsGeq_raw1394 = {
    "enable":          SLBit(4, 0),
    **{s: SLNibblePair(i*2 + 5) for s, i in zip(SL1602EqFreqs, range(len(SL1602EqFreqs)))},
}

SL1602CtrlsFx_raw1394 = {
    "fxtype":         SLNibblePair(5, SLTypeInt),
    **{"param%d" % i: SLNibblePair(i*2+7) for i in range(6)}
}

SL1602CtrlsMasters_raw1394 = {
    "monLevelMain":   SLNibblePair(26),
    "monLevelPhones": SLNibblePair(36),
    "fxagain":        SLNibblePair(32, SLTypeGain),
    "fxbgain":        SLNibblePair(34, SLTypeGain),
    "monLevelSolo":   SLNibblePair(28),
    "monMain":        SLBit(47, 1),
    "monSolo":        SLBit(47, 2),
    "monFirewire":    SLBit(47, 3),
    "soloPFL":        SLBit(46, 0),
    "talkback":       SLBit(46, 3),
    "talkback->aux12":SLBit(45, 0),
    "talkback->aux34":SLBit(45, 1),
    "fxa->aux1":      SLBit(52, 0),
    "fxa->aux2":      SLBit(52, 1),
    "fxa->aux3":      SLBit(52, 2),
    "fxa->aux4":      SLBit(52, 3),
    "fxb->aux1":      SLBit(50, 0),
    "fxb->aux2":      SLBit(50, 1),
    "fxb->aux3":      SLBit(51, 2),
    "fxb->aux4":      SLBit(51, 3),
}

SL1602CtrlsIn_uc = {
    "gain":            0,
    "pan":             1,
    "aux1":            3,
    "aux2":            4,
    "aux3":            5,
    "aux4":            6,
    "fxa":            13,
    "fxb":            14,
    #"fxagain":        15,
    #"fxbgain":        16,
    "linkstereo":     54,
    "phantom":        60,
    "firewire":       61,
    "phase":          62,
    "hpf":            80,
    "hpffreq":      3021,
    "gatethresh":   3041,
    "mute":         3052,
    "solo":         3053,
    "post":         3063,
    "gate":         3079,
    # Compressor
    "compthresh":   3034,
    "compratio":    3035,
    "compresponse": 3036,
    "compgain":     3038,
    "comp":         3073,
    "compauto":     3074,
    "complimit":    3076,
    # EQ
    "eqlowfreq":    3022,
    "eqmidfreq":    3024,
    "eqhighfreq":   3025,
    "eqlowgain":    3030,
    "eqmidgain":    3032,
    "eqhighgain":   3033,
    "eqlowshelf":   3064,
    "eqmidhiq":     3066,
    "eqhighshelf":  3067,
    "eqlow":        3069,
    "eqmid":        3071,
    "eqhigh":       3072,
    # Unknown parameters
    "Unknown1":     3002,
    "toMain":       3059,
    "Unknown3":     3070,
    "Unknown4":     3075,
    "Unknown5":     3077,
    "Unknown6":     3078,
}

SL1602CtrlsGeq_uc = {
    "enable":          0,
    **{s: i+1 for s, i in zip(SL1602EqFreqs, range(len(SL1602EqFreqs)))},
#   "unknown":        32,
}

SL1602CtrlsMasters_uc = {
    "monLevelMain":   12,
    "monLevelPhones": 13,
    "fxagain":        15,
    "fxbgain":        16,
    "monLevelSolo":   17,
    "monMain":        29,
    "monSolo":        30,
    "monFirewire":    31,
    "solo_pfl_afl":   32,
    "talkback":       35,
    "tb_to_aux12":    36,
    "tb_to_aux37":    37,
    "srec_assigns":   64,
    "srec_eqdyn":     65,
    "srec_auxmix":    66,
    "srec_faders":    67,
    "srec_mute":      68,
    "srec_fx":        69,
    "srec_geq":       70,
    "srec_pots":      70,
    "fxa->aux1":      72,
    "fxa->aux2":      73,
    "fxa->aux3":      74,
    "fxa->aux4":      75,
    "fxb->aux1":      78,
    "fxb->aux2":      79,
    "fxb->aux3":      80,
    "fxb->aux4":      81,
}

SL1602CtrlsFx_uc = {
    "param%d"%i: i for i in range(9)
}

SL1602CtrlsSlMixer_uc = {
    "meters":                   15019,  # inputs, outputs, GR, locate
    "link_channel_faders":      15031,
    "default_to_fader_locate":  15032,
}

SL1602Channels_uc = {
    # Main channels
    **{"ch%d"  % (i+1): SLInputChannel("in%d,0"%(i), SL1602CtrlsIn_uc)        for i in range(8)},
    **{"ch%d"  % (i+1): SLInputChannel("in%d,0"%(i), SL1602CtrlsIn_uc, True)  for i in range(8, 12)},
    **{"aux%d" % (i+1): SLInputChannel("in%d,0"%(i+12), SL1602CtrlsIn_uc)     for i in range(4)},
    "main": SLInputChannel("in16,0", SL1602CtrlsIn_uc),
    "fxa": SLInputChannel("in17,0", SL1602CtrlsIn_uc),
    "fxb": SLInputChannel("in18,0", SL1602CtrlsIn_uc),

    # Misc channels
    "masters":      SLInputChannel("masters", SL1602CtrlsMasters_uc),
    **{"fx %s" % s: SLInputChannel("fx %s" % s, SL1602CtrlsFx_uc) for s in ["a", "b"]},
    "geq0":         SLInputChannel("geq0", SL1602CtrlsGeq_uc),
    "slmixer":      SLInputChannel("slmixer", SL1602CtrlsSlMixer_uc),
    "smaartwiz":    SLInputChannel("smaartwiz", {}),
}

SL1602Channels_raw1394 = {
    **{"ch%d"  % (i+1): SLInputChannel(i, SL1602CtrlsIn_raw1394)        for i in range(8)},
    **{"ch%d"  % (i+1): SLInputChannel(i, SL1602CtrlsIn_raw1394, True)  for i in range(8, 12)},
    **{"aux%d" % (i+1): SLInputChannel(i+12, SL1602CtrlsIn_raw1394)     for i in range(4)},
    "main":     SLInputChannel(16, SL1602CtrlsIn_raw1394),
    "fxa":      SLInputChannel(17, SL1602CtrlsIn_raw1394),
    "fxb":      SLInputChannel(18, SL1602CtrlsIn_raw1394),
    "geq0":     SLGeq(0, SL1602CtrlsGeq_raw1394),
    "fx0":      SLFx(0, SL1602CtrlsFx_raw1394),
    "fx1":      SLFx(1, SL1602CtrlsFx_raw1394),
    "masters":  SLMasters(0, SL1602CtrlsMasters_raw1394),
}

@dataclass
class StudioLive1602Base:
    name = "StudioLive 16.0.2"

@dataclass
class SL1602Info_uc(StudioLive1602Base):
    port = 6969
    channels = SL1602Channels_uc
    magic = [0x04ffffff, 0x000a9204, 8]

@dataclass
class SL1602Info_raw1394(StudioLive1602Base):
    channels = SL1602Channels_raw1394
    # Status bit offsets for channel groups
    sbo = {SLInputChannel: 14, SLFx: 15, SLGeq: 17, SLMasters: 18}

@dataclass
class StudioLive1602:
    backends = {"uc": SL1602Info_uc, "raw1394" : SL1602Info_raw1394}
