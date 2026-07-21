#!/usr/bin/python3
"""
Generate an Open Stage Control session JSON for osclive (StudioLive 16.0.2).

The layout mirrors the TouchOSC layout from topyg.py:
  - Mixer:     All channel gain faders in one row
  - Channel:   Per-channel detail (gain, general, comp, eq) via nested tabs
  - Sends:     Aux/FX send matrix
  - Meters:    Level/peak meters + mute/solo/firewire per channel
  - Equalizer: 31-band graphic EQ faders

Usage:
    python toosc.py [-o output.json]

The generated session sends /init on load and listens on the same OSC
addresses the osclive server uses (/channel/{ch}/{ctrl}).
"""

import json
import argparse
from pathlib import Path

# -- Channel definitions (same as topyg.py) ----------------------------------

CHAN = [f"ch{i + 1}" for i in range(12)]
AUXS = [f"aux{i + 1}" for i in range(4)]
FXS = [f"fx{chr(ord('a') + i)}" for i in range(2)]
ALL = CHAN + AUXS + FXS + ["main"]

GEQ_FREQS = [
    "20", "25", "32", "40", "50", "63", "80", "100", "125", "160",
    "200", "250", "320", "400", "500", "640", "800", "1k", "1k3", "1k6",
    "2k", "2k5", "3k2", "4k", "5k", "6k4", "8k", "10k", "13k", "16k", "20k",
]

LABELS = {
    **{f"ch{i + 1}": f"Ch {i + 1}" for i in range(12)},
    **{f"aux{i + 1}": f"Aux {i + 1}" for i in range(4)},
    "fxa": "FX A", "fxb": "FX B", "main": "Main",
}

# -- Colors (CSS hex) ---------------------------------------------------------

C_RED = "#e62618"
C_YELLOW = "#ffff00"
C_BLUE = "#0026bf"
C_GREEN = "#199919"
C_GRAY = "#7f7f7f"
C_ORANGE = "#ffa500"
C_WHITE = "#ffffff"
C_LTBLUE = "#00c4a8"


# -- Widget helpers -----------------------------------------------------------

def W(wtype, id, addr="auto", top=0.0, left=0.0, width=100.0, height=100.0, label="auto", **kw):
    """Create a widget dict with geometry expressed as percentages."""
    w = {
        "type": wtype, "id": id, "address": addr,
        "top": f"{top}%", "left": f"{left}%",
        "width": f"{width}%", "height": f"{height}%", "label": label,
    }
    w.update(kw)
    return w


def fader(id, ch, ctrl, **kw):
    return W("fader", id, f"/channel/{ch}/{ctrl}", **kw)


def knob(id, ch, ctrl, **kw):
    return W("knob", id, f"/channel/{ch}/{ctrl}", **kw)


def button(id, ch, ctrl, mode="toggle", **kw):
    return W("button", id, f"/channel/{ch}/{ctrl}", mode=mode, on=1, off=0, **kw)


def text_widget(id, addr, **kw):
    return W("text", id, addr, interaction=False, **kw)


def panel(id, widgets=None, tabs=None, **kw):
    w = W("panel", id, **kw)
    w["widgets"] = widgets or []
    w["tabs"] = tabs or []
    return w


def tab(id, label, widgets=None, tabs=None):
    return {
        "type": "tab", "id": id, "label": label,
        "widgets": widgets or [], "tabs": tabs or [],
    }


def container_tab(id, label, sub_tabs):
    """A tab containing a panel with nested sub-tabs.

    Open Stage Control requires nested tabs to live inside a panel,
    not directly in a tab's 'tabs' array.
    """
    return tab(id, label, widgets=[
        panel(f"{id}_panel", top=0, left=0, width=100, height=100,
              tabs=sub_tabs)
    ])


# -- Page builders ------------------------------------------------------------

def build_mixer_page():
    """All channel gain faders in one horizontal row + main."""
    widgets = []
    channels = CHAN + AUXS + FXS + ["main"]
    n = len(channels)
    fw = 100.0 / n  # fader width %

    for i, ch in enumerate(channels):
        x = i * fw
        w = fw
        color = (C_RED if i < 8 else
                 (C_YELLOW if i < 12 else
                  (C_ORANGE if ch.startswith("fx") else C_WHITE)))
        widgets.append(fader(
            f"mix_{ch}", ch, "gain",
            top=10, left=x, width=w, height=75,
            label=LABELS.get(ch, ch),
            colorWidget=color,
        ))
        widgets.append(text_widget(
            f"mix_{ch}_label", f"/channel/{ch}/label",
            top=86, left=x, width=w, height=8,
            align="center",
        ))

    return tab("mixer", "Mixer", widgets=widgets)


def build_channel_detail(ch):
    """Per-channel detail: gain fader (right) + config tabs (General/Comp/Eq)."""

    # --- Gain fader (right, tall) ---
    gain = fader(f"ch_{ch}_gain", ch, "gain",
                 top=2, left=90, width=10, height=96,
                 label="Gain", design="compact")

    label = text_widget(f"ch_{ch}_lbl", f"/channel/{ch}/label",
                        top=0, left=0, width=88, height=5,
                        align="left", colorText=C_WHITE)

    # --- General tab ---
    # 3 rows: [button | horizontal fader | 2 buttons]
    # Row layout mirrors topyg.py: panreset/hpf/gate buttons on left,
    # wide horizontal faders for pan/hpffreq/gatethresh, 2x3 button matrix on right
    bw, bh = 10, 9       # button width/height
    fw, fh = 35, 8       # fader width/height (horizontal)
    rx = 52              # right button column start x
    rxs = 12             # right button spacing
    rows = [5, 37, 69]   # y positions for 3 rows

    gen_widgets = [
        # Row 0: panreset | pan fader | phantom, phase
        button(f"ch_{ch}_panreset", ch, "panreset", top=rows[0], left=0, width=bw, height=bh,
               label="Pan Rst", mode="momentary", colorWidget=C_GREEN),
        fader(f"ch_{ch}_pan", ch, "pan", top=rows[0], left=bw + 2, width=fw, height=fh,
              label="Pan", horizontal=True, range={"min": 0, "max": 1}, design="compact"),
        button(f"ch_{ch}_phantom", ch, "phantom", top=rows[0], left=rx, width=bw, height=bh,
               label="Phantom", colorWidget=C_BLUE),
        button(f"ch_{ch}_phase", ch, "phase", top=rows[0], left=rx + rxs, width=bw, height=bh,
               label="Phase", colorWidget=C_BLUE),
        # Row 1: hpf | hpffreq fader | firewire, post
        button(f"ch_{ch}_hpf", ch, "hpf", top=rows[1], left=0, width=bw, height=bh,
               label="HPF", colorWidget=C_BLUE),
        fader(f"ch_{ch}_hpffreq", ch, "hpffreq", top=rows[1], left=bw + 2, width=fw, height=fh,
              label="HPF Hz", horizontal=True, range={"min": 0, "max": 1}, design="compact"),
        button(f"ch_{ch}_firewire", ch, "firewire", top=rows[1], left=rx, width=bw, height=bh,
               label="FireWire", colorWidget=C_ORANGE),
        button(f"ch_{ch}_post", ch, "post", top=rows[1], left=rx + rxs, width=bw, height=bh,
               label="Post", colorWidget=C_BLUE),
        # Row 2: gate | gatethresh fader | mute, solo
        button(f"ch_{ch}_gate", ch, "gate", top=rows[2], left=0, width=bw, height=bh,
               label="Gate", colorWidget=C_BLUE),
        fader(f"ch_{ch}_gatethresh", ch, "gatethresh", top=rows[2], left=bw + 2, width=fw, height=fh,
              label="Gate", horizontal=True, range={"min": 0, "max": 1}, design="compact"),
        button(f"ch_{ch}_mute", ch, "mute", top=rows[2], left=rx, width=bw, height=bh,
               label="Mute", colorWidget=C_RED),
        button(f"ch_{ch}_solo", ch, "solo", top=rows[2], left=rx + rxs, width=bw, height=bh,
               label="Solo", colorWidget=C_YELLOW),
    ]

    # --- Comp tab ---
    # 3 buttons on top, 4 vertical faders below
    comp_widgets = [
        button(f"ch_{ch}_comp", ch, "comp", top=2, left=5, width=25, height=10,
               label="Enable", colorWidget=C_YELLOW),
        button(f"ch_{ch}_compauto", ch, "compauto", top=2, left=37, width=25, height=10,
               label="Auto", colorWidget=C_YELLOW),
        button(f"ch_{ch}_complimit", ch, "complimit", top=2, left=69, width=25, height=10,
               label="Limit", colorWidget=C_YELLOW),
        fader(f"ch_{ch}_compthresh", ch, "compthresh", top=15, left=5, width=20, height=72,
              label="", range={"min": 0, "max": 1}, design="compact"),
        fader(f"ch_{ch}_compratio", ch, "compratio", top=15, left=28, width=20, height=72,
              label="", range={"min": 0, "max": 1}, design="compact"),
        fader(f"ch_{ch}_compresponse", ch, "compresponse", top=15, left=51, width=20, height=72,
              label="", range={"min": 0, "max": 1}, design="compact"),
        fader(f"ch_{ch}_compgain", ch, "compgain", top=15, left=74, width=20, height=72,
              label="", range={"min": 0, "max": 1}, design="compact"),
        text_widget(f"ch_{ch}_compthresh_lbl", "auto",
                    top=88, left=5, width=20, height=8,
                    label="", value="Thresh", align="center", colorText=C_WHITE),
        text_widget(f"ch_{ch}_compratio_lbl", "auto",
                    top=88, left=28, width=20, height=8,
                    label="", value="Ratio", align="center", colorText=C_WHITE),
        text_widget(f"ch_{ch}_compresponse_lbl", "auto",
                    top=88, left=51, width=20, height=8,
                    label="", value="Resp", align="center", colorText=C_WHITE),
        text_widget(f"ch_{ch}_compgain_lbl", "auto",
                    top=88, left=74, width=20, height=8,
                    label="", value="Gain", align="center", colorText=C_WHITE),
    ]

    # --- Eq tab ---
    # 3 columns (low/mid/high): freq fader + gain knob + enable/shelf buttons
    col_w = 33
    eq_widgets = [
        # Column 0: Low
        fader(f"ch_{ch}_eqlowfreq", ch, "eqlowfreq", top=2, left=0, width=col_w, height=55,
              label="Low Hz", range={"min": 0, "max": 1}, design="compact"),
        knob(f"ch_{ch}_eqlowgain", ch, "eqlowgain", top=58, left=0, width=col_w, height=20,
             label="L Gain", range={"min": 0, "max": 1}),
        button(f"ch_{ch}_eqlow", ch, "eqlow", top=80, left=0, width=15, height=8,
               label="Low", colorWidget=C_LTBLUE),
        button(f"ch_{ch}_eqlowshelf", ch, "eqlowshelf", top=80, left=17, width=15, height=8,
               label="Shelf", colorWidget=C_GRAY),
        # Column 1: Mid
        fader(f"ch_{ch}_eqmidfreq", ch, "eqmidfreq", top=2, left=col_w, width=col_w, height=55,
              label="Mid Hz", range={"min": 0, "max": 1}, design="compact"),
        knob(f"ch_{ch}_eqmidgain", ch, "eqmidgain", top=58, left=col_w, width=col_w, height=20,
             label="M Gain", range={"min": 0, "max": 1}),
        button(f"ch_{ch}_eqmid", ch, "eqmid", top=80, left=col_w, width=15, height=8,
               label="Mid", colorWidget=C_LTBLUE),
        button(f"ch_{ch}_eqmidhiq", ch, "eqmidhiq", top=80, left=col_w + 17, width=15, height=8,
               label="HiQ", colorWidget=C_GRAY),
        # Column 2: High
        fader(f"ch_{ch}_eqhighfreq", ch, "eqhighfreq", top=2, left=2 * col_w, width=col_w, height=55,
              label="High Hz", range={"min": 0, "max": 1}, design="compact"),
        knob(f"ch_{ch}_eqhighgain", ch, "eqhighgain", top=58, left=2 * col_w, width=col_w, height=20,
             label="H Gain", range={"min": 0, "max": 1}),
        button(f"ch_{ch}_eqhigh", ch, "eqhigh", top=80, left=2 * col_w, width=15, height=8,
               label="High", colorWidget=C_LTBLUE),
        button(f"ch_{ch}_eqhighshelf", ch, "eqhighshelf", top=80, left=2 * col_w + 17, width=15, height=8,
               label="Shelf", colorWidget=C_GRAY),
    ]

    # --- Config panel with 3 tabs ---
    config = panel(
        f"ch_{ch}_config",
        top=6, left=0, width=88, height=93,
        tabs=[
            tab(f"ch_{ch}_general", "General", widgets=gen_widgets),
            tab(f"ch_{ch}_comp", "Comp", widgets=comp_widgets),
            tab(f"ch_{ch}_eq", "Eq", widgets=eq_widgets),
        ])

    return panel(f"ch_{ch}_detail", top=0, left=0, width=100, height=100,
                 widgets=[gain, label, config])


def build_channel_page():
    """Channel detail page with group tabs (Inputs/Auxs/Fx/Main)."""
    def group_tab(label, channels):
        if len(channels) == 1:
            return tab(f"grp_{channels[0]}", label,
                       widgets=[build_channel_detail(channels[0])])
        return container_tab(label.lower(), label, [
            tab(f"ch_{ch}", LABELS.get(ch, ch),
                widgets=[build_channel_detail(ch)])
            for ch in channels
        ])

    return container_tab("channel", "Channel", [
        group_tab("Inputs", CHAN),
        group_tab("Auxs", AUXS),
        group_tab("Fx", FXS),
        group_tab("Main", ["main"]),
    ])


def build_sends_page():
    """Aux/FX send matrix: one tab per target, each with 12 input sends."""
    targets = AUXS + FXS
    return container_tab("sends", "Sends", [
        tab(f"send_{t}", LABELS.get(t, t), widgets=[
            # Main gain for this target
            fader(f"send_{t}_main", t, "gain",
                  top=5, left=88, width=10, height=85,
                  label="Main", colorWidget=C_WHITE),
            # 12 input sends
            *[
                fader(f"send_{t}_{ch}", ch, t,
                      top=15, left=i * 7, width=6, height=75,
                      label=LABELS.get(ch, ch), range={"min": 0, "max": 1},
                      design="compact",
                      colorWidget=C_RED if i < 8 else C_YELLOW)
                for i, ch in enumerate(CHAN)
            ],
            # Label for the target
            text_widget(f"send_{t}_label", f"/channel/{t}/label",
                        top=2, left=0, width=80, height=6,
                        align="left"),
        ])
        for t in targets
    ])


def build_meters_page():
    """Level/peak meters + mute/solo/firewire per channel."""
    widgets = []
    channels = CHAN + AUXS + FXS + ["main"]
    n = len(channels)
    cw = 100.0 / n  # column width %

    for i, ch in enumerate(channels):
        x = i * cw
        w = cw
        color = (C_RED if i < 8 else
                 (C_YELLOW if i < 12 else
                  (C_ORANGE if ch.startswith("fx") else C_WHITE)))

        # Level meter (read-only fader, 0-16 range)
        widgets.append(W("fader", f"meter_{ch}_level", f"/channel/{ch}/level",
                         top=5, left=x, width=w, height=60,
                         label="", interaction=False,
                         range={"min": 0, "max": 16},
                         colorWidget=color, design="compact"))
        # Peak indicator (read-only fader)
        widgets.append(W("fader", f"meter_{ch}_peak", f"/channel/{ch}/peak",
                         top=5, left=x, width=w, height=60,
                         label="", interaction=False,
                         range={"min": 0, "max": 16},
                         colorWidget=C_RED, alphaStroke=0.5, design="compact"))
        # Mute / Solo / FireWire buttons
        widgets.append(button(f"meter_{ch}_mute", ch, "mute",
                              top=67, left=x, width=w, height=8,
                              label="Mute", colorWidget=C_RED))
        widgets.append(button(f"meter_{ch}_solo", ch, "solo",
                              top=76, left=x, width=w, height=8,
                              label="Solo", colorWidget=C_YELLOW))
        if ch in CHAN:
            widgets.append(button(f"meter_{ch}_fw", ch, "firewire",
                                  top=85, left=x, width=w, height=6,
                                  label="FW", colorWidget=C_ORANGE))
        # Peak reset
        widgets.append(button(f"meter_{ch}_pkrst", ch, "peak_reset",
                              top=85 if ch not in CHAN else 92, left=x, width=w,
                              height=6 if ch not in CHAN else 5,
                              label="Rst", mode="momentary", colorWidget=C_GRAY))
        # Label
        widgets.append(text_widget(f"meter_{ch}_label", f"/channel/{ch}/label",
                                   top=92 if ch not in CHAN else 97,
                                   left=x, width=w, height=3,
                                   align="center"))

    return tab("meters", "Meters", widgets=widgets)


def build_equalizer_page():
    """31-band graphic EQ faders + enable/reset buttons."""
    widgets = []
    n = len(GEQ_FREQS)
    fw = 100.0 / n

    for i, freq in enumerate(GEQ_FREQS):
        x = i * fw
        widgets.append(fader(
            f"geq_{i + 1}", "geq0", str(i + 1),
            top=10, left=x, width=fw, height=75,
            label=freq, range={"min": 0, "max": 1},
            design="compact", colorWidget=C_WHITE,
        ))

    widgets.append(button("geq_enable", "geq0", "enable",
                          top=88, left=0, width=10, height=8,
                          label="Enable", colorWidget=C_GREEN))
    widgets.append(button("geq_reset", "geq0", "reset",
                          top=88, left=12, width=10, height=8,
                          label="Reset", mode="momentary", colorWidget=C_RED))

    return tab("equalizer", "Equalizer", widgets=widgets)


# -- Session assembly ---------------------------------------------------------

def connection_led(tab_id):
    """Connection ping LED for a top-level tab (unique id per tab)."""
    return W("led", f"ping_{tab_id}", "/connection_ping",
             top=1, left=95, width=4, height=4,
             label="", mode="intensity",
             range={"min": 0, "max": 1},
             colorWidget=C_GREEN)


def build_session(target="localhost:4299"):
    """Assemble the full Open Stage Control session.

    The target points to the UDP<->TCP bridge (default localhost:4299),
    NOT directly at osclive. Open Stage Control only speaks UDP OSC;
    the bridge forwards to osclive's TCP OSC port (default 4301).
    """
    tabs = [
        build_mixer_page(),
        build_channel_page(),
        build_sends_page(),
        build_meters_page(),
        build_equalizer_page(),
    ]
    # Add a connection ping LED to each top-level tab
    for t in tabs:
        t["widgets"].insert(0, connection_led(t["id"]))

    root = {
        "type": "root",
        "id": "root",
        "colorBg": "#1a1a1a",
        "scroll": True,
        "contain": True,
        "tabs": tabs,
        "widgets": [],
        # Send all widget OSC to the UDP<->TCP bridge (UDP, default :4299).
        # The bridge forwards to osclive's TCP OSC port.
        # Override with:  open-stage-control -s host:port
        "target": target,
        # Send /init when the session loads
        "onCreate": "send('/init')",
    }

    return {
        "createdWith": "Open Stage Control",
        "version": "1.15.6",
        "type": "session",
        "content": root,
    }


def main():
    default = str(Path.home() / "osclive.json")
    argp = argparse.ArgumentParser(
        description="Generate Open Stage Control session for osclive")
    argp.add_argument("-o", "--output", help="Output JSON file", default=default)
    argp.add_argument("-s", "--target", default="localhost:4299",
                      help="OSC target as ip:port (UDP, default: localhost:4299). "
                           "Points to the osc-bridge, not directly to osclive.")
    args = argp.parse_args()

    session = build_session(args.target)
    with open(args.output, "w") as f:
        json.dump(session, f, indent=2)
    print(f"Session written to {args.output}")


if __name__ == "__main__":
    main()
