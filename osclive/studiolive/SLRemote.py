import threading
import struct
import time

class SLRemote(object):
    def __init__(self, backend, debug = False):
        self.backend = backend
        self.debug = debug

        self.update_callbacks = []
        self.level_callbacks = []
        self.channels = backend.channels

        backend.set_listener(self)

    # Main functions
    def connect(self):
        self.backend.connect()

    def disconnect(self):
        self.backend.disconnect()

    def add_update_callback(self, callback):
        self.update_callbacks.append(callback)

    def remove_update_callback(self, callback):
        self.update_callbacks.remove(callback)

    def get_level(self, channel, stereo = False):
        assert channel in self.channels
        level = self.channels[channel].level
        return level[0] if not stereo and type(level) == tuple else level

    def get_control(self, channel, control):
        assert channel in self.channels
        ch = self.channels[channel]
        assert control in ch.ctrls, "Control %s is not in channel %s" % (control, ch.name)

        if control not in ch.ctrls:
            ch.ctrls[control] = 0

        value = ch.ctrls[control]

        if self.debug:
            print("StudioLive: Get %-8s %-14s = %.3f" % (ch.name + ":", control, value if value else 0))
        return value

    def set_control(self, channel, control, value):
        assert channel in self.channels, "Unknown channel %s" % channel
        ch = self.channels[channel]
        assert control in ch.ctrls, "Control %s not in channel %s" % (control, channel)

        if self.debug:
            print("StudioLive: Set %-8s %-14s = %.3f" % (ch.name + ":", control, value))

        value = max(min(value, 1), 0)

        ch.ctrls[control] = value

        for callback in self.update_callbacks:
            callback(ch.name, control, value)

        self.backend.set_control(ch, control, value)
