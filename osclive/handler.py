import math
import re

from .studiolive.StudioLive1602 import SL1602CtrlsIn_raw1394

from .osc.server import DispatchedOSCRequestHandler

class SLClientHandler(DispatchedOSCRequestHandler):
    # Must be set!
    sl = None

    input_names = {}
    aux_names = {}

    def setup(self):
        super().setup()

        channels = self.sl.channels
        self.channel_ctrls = channels["ch1"].ctrls

        self.inputs = [n for n in channels if re.match("^ch", n)]
        self.auxs = [n for n in channels if re.match("^aux", n)]
        self.fxs = [n for n in channels if re.match("^fx[a-z]", n)]
        self.all_channels = self.inputs + self.auxs + self.fxs + ["main"]

        self.peaks = {ch: 0 for ch in self.all_channels}

        self.connection_ping = 0

        self.sl.add_update_callback(self.sl_control_handler)
        self.sl.level_callbacks.append(self.sl_level_handler)

        self.init_dispatcher()
        self.init()

    def _get_freqs(self, ch):
        return [n for n in self.sl.channels[ch].ctrls if re.match(".*Hz$", n)]

    def init_dispatcher(self):
        for channel in self.all_channels:
            for control in self.channel_ctrls:
                self.map(f"/channel/{channel}/{control}", self.channel_control_handler, channel, control)

            for control in ["panreset", "peak_reset"]:
                self.map(f"/channel/{channel}/{control}", self.channel_control_extra_handler, channel, control)

        ch = "geq0"
        if ch in self.sl.channels:
            freqs = self._get_freqs(ch)
            for i in range(len(freqs)):
                self.map("/channel/%s/%d" % (ch, i + 1), self.channel_control_handler, ch, freqs[i])
            for ctrl in ["enable"]:
                self.map("/channel/%s/%s" % (ch, ctrl), self.channel_control_handler, ch, ctrl)
            for ctrl in ["reset"]:
                self.map("/channel/%s/%s" % (ch, ctrl), self.channel_control_extra_handler, ch, ctrl)
        # TODO
        #for i in ["fx0"]:
        #    for ctrl in ["param%d"%i for i in range(6)]:
        #        self.map("/fx/%s"%(ctrl), self.common_channel_handler, i, ctrl)

        self.map("/init", lambda addr: self.init())

    def init(self):
        all_channels = self.inputs + self.auxs + self.fxs + ["main"]
        for ch in all_channels:
            for ctrl in self.channel_ctrls:
                value = self.sl.get_control(ch, ctrl)
                if value == None:
                    self.send_message("/channel/%s/%s" % (ch, ctrl), 0)
                else:
                    self.send_message("/channel/%s/%s" % (ch, ctrl), value)

        # Update labels
        for i, (ch, name) in enumerate(self.input_names.items(), 1):
            self.send_message("/channel/%s/label" % ch, name)

        for i, (ch, name) in enumerate(self.aux_names.items(), 1):
            self.send_message("/channel/%s/label" % ch , name)
        self.send_message("/channel/main/label", 'Main')

        ch = "geq0"
        if ch in self.sl.channels:
            l = list(self.sl.channels[ch].ctrls.keys())
            index = l.index("20Hz")
            for i in range(index, index + 31):
                value = self.sl.get_control(ch, l[i])
                self.send_message("/channel/%s/%d" % (ch, i - index + 1), value)
            for ctrl in ["enable"]:
                value = self.sl.get_control(ch, ctrl)
                self.send_message("/channel/%s/%s" % (ch, ctrl), value)

    def sl_level_handler(self):
        with self.bundle():
            self.connection_ping += 1
            if self.connection_ping >= 16:
                self.connection_ping = 0

            if self.connection_ping % 8 == 0:
                self.send_message("/connection_ping", self.connection_ping >= 8)

            for ch in self.inputs:
                value = self.sl.get_level(ch)
                if value == None:
                    value = 0
                value /= 32.0

                if value > self.peaks[ch]:
                    self.peaks[ch] = value
                    self.send_message("/channel/%s/peak" % ch, value)

    def sl_control_handler(self, channel, ctrl, value):
        #print("SL Control handler, channel %s, ctrl %s" %( channel, ctrl))
        all_channels = self.inputs + self.auxs + self.fxs + ["main"]
        if channel in all_channels:
            self.send_message("/channel/%s/%s" % (channel, ctrl), value)

#        # PAGE "Equalizer"
        if channel == "geq0":
            l = list(self.sl.channels["geq0"].ctrls.keys())
            index = l.index(ctrl) - l.index("20Hz")

            if index <= 31:
                self.send_message("/channel/%s/%d" % (channel, index + 1), value)
            if ctrl in ["enable"]:
                self.send_message("/channel/%s/%s" % (channel, ctrl), value)
#
#        if channel == "fx0":
#            self.send_message("/fx/%s" % ctrl, value)

    def channel_control_handler(self, addr, args, value):
        ch, ctrl = args[:2]
        self.sl.set_control(ch, ctrl, value)

    def channel_control_extra_handler(self, addr, args, value):
        ch, ctrl = args[:2]
        if ctrl == "panreset":
            self.sl.set_control(ch, "pan", 0.5)

        if ctrl == "peak_reset":
            self.peaks[ch] = -1
            self.sl_level_handler()

        if ch == "geq0" and ctrl == "reset":
            for i, ctrl in enumerate(self._get_freqs(ch)):
                self.sl.set_control(ch, ctrl, 0.5)
