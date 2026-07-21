"""
Mock backend for osclive — no hardware required.

Simulates a StudioLive 16.0.2 mixer with random level meter activity.
All channel controls are stored in memory; set_control just records
the value and triggers update callbacks as usual.

Usage:
    osclive --mock
"""

import time
import random
import threading

from .backend import SLBackend, SLChannel, SLValue
from .studiolive1602 import SL1602EqFreqs


# Channel controls (keys from SL1602CtrlsIn_raw1394)
_INPUT_CTRLS = [
    "gain", "pan", "linkedpan",
    "aux1", "aux2", "aux3", "aux4", "fxa", "fxb",
    "hpf", "hpffreq", "gate", "gatethresh",
    "phantom", "firewire", "phase", "post", "mute", "solo",
    "comp", "compauto", "complimit",
    "compthresh", "compratio", "compresponse", "compgain",
    "eqlow", "eqmid", "eqhigh",
    "eqlowshelf", "eqmidhiq", "eqhighshelf",
    "eqlowfreq", "eqmidfreq", "eqhighfreq",
    "eqlowgain", "eqmidgain", "eqhighgain",
    "toMain",
]

_DEFAULTS = {
    "gain": 0.5,
    "pan": 0.5,
    "linkedpan": 0.5,
    "aux1": 0.0, "aux2": 0.0, "aux3": 0.0, "aux4": 0.0,
    "fxa": 0.0, "fxb": 0.0,
    "hpf": 0, "hpffreq": 0.0, "gate": 0, "gatethresh": 0.0,
    "phantom": 0, "firewire": 0, "phase": 0, "post": 0,
    "mute": 0, "solo": 0,
    "comp": 0, "compauto": 0, "complimit": 0,
    "compthresh": 0.3, "compratio": 0.3, "compresponse": 0.3, "compgain": 0.5,
    "eqlow": 0, "eqmid": 0, "eqhigh": 0,
    "eqlowshelf": 0, "eqmidhiq": 0, "eqhighshelf": 0,
    "eqlowfreq": 0.2, "eqmidfreq": 0.5, "eqhighfreq": 0.8,
    "eqlowgain": 0.5, "eqmidgain": 0.5, "eqhighgain": 0.5,
    "toMain": 1,
}


def _make_ctrls(extra: dict[str, SLValue] | None = None) -> dict[str, SLValue]:
    ctrls = {c: _DEFAULTS.get(c, 0) for c in _INPUT_CTRLS}
    if extra:
        ctrls.update(extra)
    return ctrls


class SLMockBackend(SLBackend):
    """In-memory mock backend that simulates meter activity."""

    def __init__(self) -> None:
        super().__init__()

        # Build channels matching StudioLive 16.0.2 layout
        self.channels: dict[str, SLChannel] = {
            **{f"ch{i + 1}": SLChannel(f"ch{i + 1}", _make_ctrls()) for i in range(12)},
            **{f"aux{i + 1}": SLChannel(f"aux{i + 1}", _make_ctrls()) for i in range(4)},
            "fxa": SLChannel("fxa", _make_ctrls()),
            "fxb": SLChannel("fxb", _make_ctrls()),
            "main": SLChannel("main", _make_ctrls()),
            # Graphic EQ channel
            "geq0": SLChannel("geq0", {
                "enable": 0,
                **{f: 0.5 for f in SL1602EqFreqs},
            }),
            # Hidden status channel (needed by some code paths)
            "_status": SLChannel("_status", {"meters": 0}),
        }

        # Randomize some initial levels so meters show activity
        for ch in self.channels.values():
            if not ch.name.startswith("_"):
                ch.level = 0

    def connect(self) -> None:
        SLBackend.connect(self)
        self.update_thread = threading.Thread(target=self._update_process, daemon=True)
        self.update_thread.start()

    def set_control(self, ch: SLChannel, control: str, value: SLValue) -> None:
        # Values are already stored by SLRemote; nothing extra to do
        pass

    def _update_process(self) -> None:
        """Simulate random meter activity on input channels."""
        rng = random.Random()
        while not self._stop_event.is_set():
            for name, ch in self.channels.items():
                if name.startswith("_") or name == "geq0":
                    continue
                if name.startswith("ch") or name == "main":
                    # Simulate input/output levels (0-32 range)
                    gain = ch.ctrls.get("gain", 0.5)
                    base = int(gain * 24 + rng.randint(-4, 4))
                    ch.level = max(0, min(32, base))
                else:
                    ch.level = rng.randint(0, 8)

            self._update_levels()
            time.sleep(0.1)
