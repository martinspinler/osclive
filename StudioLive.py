from SLRemote import SLRemote

class StudioLive1602(SLRemote):
    DEFAULT_PORT = 6969
    CHANNEL_CTRL = {
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
        "phase":          61,
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
        "limit":        3076,
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
    GEQ_CTRL = {
        "enable":          0,
        "20Hz":            1,
        "25Hz":            2,
        "32Hz":            3,
        "40Hz":            4,
        "50Hz":            5,
        "63Hz":            6,
        "80Hz":            7,
        "100Hz":           8,
        "125Hz":           9,
        "160Hz":          10,
        "200Hz":          11,
        "250Hz":          12,
        "320Hz":          13,
        "400Hz":          14,
        "500Hz":          15,
        "640Hz":          16,
        "800Hz":          17,
        "1.0kHz":         18,
        "1.3kHz":         19,
        "1.6kHz":         20,
        "2.0kHz":         21,
        "2.5kHz":         22,
        "3.2kHz":         23,
        "4.0kHz":         24,
        "5.0kHz":         25,
        "6.4kHz":         26,
        "8.0kHz":         27,
        "10kHz":          28,
        "13kHz":          29,
        "16kHz":          30,
        "20kHz":          31,
    }
    MASTERS_CTRL = {
        "monLevelMain":   12,
        "monLevelPhones": 13,
        "fxagain":        15,
        "fxbgain":        16,
        "monLevelSolo":   17,
        "monMain":        29,
        "monSolo":        30,
        "monFirewire":    31,
        "FxA->Aux1":      72,
        "FxA->Aux2":      73,
        "FxA->Aux3":      74,
        "FxA->Aux4":      75,
        "FxB->Aux1":      78,
        "FxB->Aux2":      79,
        "FxB->Aux3":      80,
        "FxB->Aux4":      81,
    }
    FX_CTRL = {
        "parm0":           0,
        "parm1":           1,
        "parm2":           2,
        "parm3":           3,
        "parm4":           4,
        "parm5":           5,
        "parm6":           6,
        "parm7":           7,
        "parm8":           8,
    }
    SLMIXER_CTRL = {
        "meters":           15019,
    }


    def __init__(self, debug = False):
        # Some magic numbers
        SLRemote.__init__(self, [0x04ffffff, 0x000a9204, 8], debug)

        # Input channel mappings
        self.mapchannel.update({k:v for k,v in (("ch%d"  %(d+1),"in%d,0"%(d+ 0)) for d in range(12))})
        self.mapchannel.update({k:v for k,v in (("aux%d" %(d+1),"in%d,0"%(d+12)) for d in range(4))})
        self.mapchannel.update({k:v for k,v in (("main"        ,"in%d,0"%(d+16)) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("fxa"         ,"in%d,0"%(d+17)) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("fxb"         ,"in%d,0"%(d+18)) for d in range(1))})

        self.mapchannel.update({k:v for k,v in (("masters"     ,"masters"      ) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("fx a"        ,"fx a"         ) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("fx b"        ,"fx b"         ) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("geq0"        ,"geq0"         ) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("slmixer"     ,"slmixer"      ) for d in range(1))})
        self.mapchannel.update({k:v for k,v in (("smaartwiz"   ,"smaartwiz"    ) for d in range(1))})

        # Controls in each input channel
        for channel in self.mapchannel:
            self.channels[channel] = {}

            if (channel == "fx a" or channel == "fx b"):
                self.mapcontrol[channel] = self.FX_CTRL
            elif (channel == "geq0"):
                self.mapcontrol[channel] = self.GEQ_CTRL
            elif (channel == "masters"):
                self.mapcontrol[channel] = self.MASTERS_CTRL
            else:
                self.mapcontrol[channel] = self.CHANNEL_CTRL

            for ctrl in self.mapcontrol[channel]:
                self.channels[channel][ctrl] = 0
        
        # Fill reverse keys
        self.revchannel.update({v:k for k,v in self.mapchannel.items()})
        for channel in self.mapchannel:
            self.revcontrol[channel] = {v:k for k,v in self.mapcontrol[channel].items()}

    def connect(self, host, port = DEFAULT_PORT):
        SLRemote.connect(self, host, port)
