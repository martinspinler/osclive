from .backend import SLBackend, SLListener, SLUpdateCallback, SLLevelCallback, SLValue


class SLRemote(SLListener):
    def __init__(self, backend: SLBackend, debug: bool = False):
        self.backend = backend
        self.debug = debug

        self.update_callbacks: list[SLUpdateCallback] = []
        self.level_callbacks: list[SLLevelCallback] = []
        self.channels = backend.channels

        backend.set_listener(self)

    # Main functions
    def connect(self) -> None:
        self.backend.connect()

    def disconnect(self) -> None:
        self.backend.disconnect()

    def add_update_callback(self, callback: SLUpdateCallback) -> None:
        self.update_callbacks.append(callback)

    def remove_update_callback(self, callback: SLUpdateCallback) -> None:
        self.update_callbacks.remove(callback)

    def get_level(self, channel: str, stereo: bool = False) -> int | tuple[int, int]:
        assert channel in self.channels
        level = self.channels[channel].level
        return level[0] if not stereo and isinstance(level, tuple) else level

    def get_control(self, channel: str, control: str) -> SLValue:
        assert channel in self.channels
        ch = self.channels[channel]
        assert control in ch.ctrls, "Control %s is not in channel %s" % (control, ch.name)

        if control not in ch.ctrls:
            ch.ctrls[control] = 0

        value = ch.ctrls[control]

        if self.debug:
            print("StudioLive: Get %-8s %-14s = %.3f" % (ch.name + ":", control, value if value else 0))
        return value

    def set_control(self, channel: str, control: str, value: SLValue) -> None:
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
