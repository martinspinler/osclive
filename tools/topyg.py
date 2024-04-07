#!/usr/bin/python

import argparse
from pathlib import Path
from dataclasses import dataclass

import tosclib as tosc
from tosclib import controls
from tosclib.elements import LOCAL, Trigger, Value
from tosclib.tosc import ControlType as CT
from tosclib.controls import PropertyFactory as pf

name = "StudioLive1602"
CHAN = ["ch%d" % (i + 1) for i in range(12)]
AUXS = ["aux%d" % (i + 1) for i in range(4)]
FXS = ["fx%s" % (chr(ord('a') + i)) for i in range(2)]

dim = lambda x:x

dim.SH    = 540
dim.SW    = 1080

dim.MAINW = 100
dim.MAINX = dim.SW - dim.MAINW - 10

dim._INW  = int((dim.SW - dim.MAINW - 30) / len(CHAN))
dim.FW    = dim._INW - 20

padding = 20
margin = 20


@dataclass
class Frame:
    x: int
    y: int
    w: int
    h: int


def pad(frame):
    return resizeFrame(frame, x=padding, y=padding, w=-2*padding, h=-2*padding)

def resizeFrame(frame, x = 0, y = 0, w = 0, h = 0):
    return (frame[0] + x, frame[1] + y, frame[2] + w, frame[3] + h)

def setFrame(frame, x = None, y = None, w = None, h = None):
    return tuple(item if item != None else frame[i] for i,item in enumerate((x, y, w, h)))


def md(**kwargs):
    return kwargs

colors = lambda x: x
colors.ltblue = (0.0, 0xc4/255, 0xa8/255, 1.0)
colors.white  = (1.0, 1.0, 1.0, 1.0)
colors.yellow = (1.0, 1.0, 0.0, 1.0)
colors.gray   = (0.5, 0.5, 0.5, 1.0)
colors.green  = (0.1, 0.5, 0.1, 1.0)
colors.dkgreen= (0.1, 0.25, 0.1, 1.0)
colors.gr     = (0x75/255, 0xCC/255, 0x26/255, 1.0)
colors.dkgray = (0.25, 0.25, 0.25, 1.0)
colors.redsh  = (1.0, 0.15, 0.1, 1.0)
colors.red    = (1.0, 0.0, 0.0, 1.0)
colors.blue   = (0.0, 0.15, 0.75, 1.0)
colors.orange = (1,165/255,0, 1)

geq_freqs = [
        "20", "25", "32", "40", "50", "63", "80", "100", "125", "160",
        "200", "250", "320", "400", "500", "640", "800", "1k", "1k3", "1k6",
        "2k", "2k5", "3k2", "4k", "5k", "6k4", "8k", "10k", "13k", "16k", "20k"]


class ElementTOSC(tosc.ElementTOSC):
    script_float2db = f"""
function float2db(val)
    local ret = (36.1 * math.log(val * 100 + 0.1) - 156.25)
    if (ret < -100) then
        return "-oo dB"
    end
    return string.format("%.1f dB", ret)
end

function onReceiveOSC(msg, connections)
    local path = msg[1]
    local args = msg[2]
    local i
    self.values["text"] = float2db(args[1].value)
    return true
end"""
    script_float2db15 = f"""
function float2db(val)
    local ret = (val - 0.5) * 30
    return string.format("%.1f dB", ret)
end

function onReceiveOSC(msg, connections)
    local path = msg[1]
    local args = msg[2]
    local i
    self.values["text"] = float2db(args[1].value)
    return true
end"""

    script_float2eq = """
function onReceiveOSC(msg, connections)
    local val = msg[2][1].value
    local a = math.log({a})
    local b = math.log({b}) - a
    self.values["text"] = string.format("%.0f Hz", math.exp(b*val+a))
    return true
end"""

    script_float2eqlow = script_float2eq.format(a=36, b=465)
    script_float2eqmid = script_float2eq.format(a=260, b=3500)
    script_float2eqhigh= script_float2eq.format(a=1400, b=18000)

    def __init__(self, parent):
        tosc.ElementTOSC.__init__(self, parent)
        self.color = None
        self.path = ""
        self.descend = True

    def getInnerFrame(self):
        return (0, 0, self.getW(), self.getH())

    def createOSCDP(self, path=None, arguments=[tosc.Partial(type="VALUE", conversion="FLOAT", value="x")], osc={}):
        if path == None:
            path = [tosc.Partial(value=self.path)]
        if type(path) == str:
            path = [tosc.Partial(value=path)]
        self.createOSC(tosc.OSC(path=path, arguments=arguments, **osc))

    def createTabProperties(self, text, color):
        tabColorProps = ['tabColorOff', 'tabColorOn', 'textColorOff', 'textColorOn']
        self.createProperty(pf.build("tabLabel", text))
        dkcolor = [x * 0.5 for x in color[:3]] + [color[3]]
        tab_colors = [dkcolor, color, colors.white, colors.white]
        [self.createProperty(pf.buildColor(name, value)) for name, value in zip(tabColorProps, tab_colors)]

    def createElement(self, el_type, name, frame, props = {}, **kwargs):
        e = ElementTOSC(self.createChild(el_type))
        if 'path' in kwargs:
            e.path = self.path + kwargs['path']
        else:
            e.path = self.path + (("/" if self.descend else "") + name if name else "")

        e.setName(name)
        if frame:
            e.setFrame(frame)

        color = props['color'] if 'color' in props else self.color
        if color:
            e.setColor(color)

        if 'outline' not in props:
            props['outline'] = 0
        if 'color' in props:
            del props['color']
        [e.createProperty(pf.build(name, value)) for name, value in props.items()]
        return e

    def createGainFader(self, frame, name, props = {}, **kwargs):
        p = self
        if name:
            p = self.createElement(CT.GROUP, name, frame, md(color=None))
            frame = setFrame(frame, x=0, y=0)

        e = p.createElement(CT.FADER, 'gain', resizeFrame(frame, h=-60), props)

        y = int((frame[3] - 80) * 0.25) + 20
        color = colors.white
        l = p.createElement(CT.LABEL, 'label', setFrame(frame, y=frame[3]-20, h=20), md(color=color, background=0))
        if 'label_path' in kwargs:
            path=[tosc.Partial(type="CONSTANT", value=kwargs['label_path'])]
        else:
            path=[tosc.Partial(type="CONSTANT", value=l.path)]
        l.createOSC(tosc.OSC(path=path, triggers=[tosc.Trigger(var="text")], arguments=[tosc.Partial(type="VALUE", value="text")]))

        g = p.createElement(CT.LABEL, 'gain', setFrame(frame, y=y, h=20), md(color=color, background=0))
        g.createOSCDP(kwargs['path'] if 'path' in kwargs else None)
        g.createProperty(pf.build("script", ElementTOSC.script_float2db))

        return e

    def createLabeledFader(self, frame, name, text, props = {}):
        f = self.createElement(CT.FADER, name, frame, props)
        l = self.createElement(CT.LABEL, name + '_label', frame, md(background=0))
        l.createValue(Value(key="text", default=text))
        return f

    def createLabeledButton(self, frame, name, text, props = {}):
        if len(frame) == 2:
            frame += (60, 60)

        b = self.createElement(CT.BUTTON, name, frame, props)
        l = self.createElement(CT.LABEL, name + '_label', frame, md(background=0))
        l.createValue(Value(key="text", default=text))
        return b

    def createLabeledChildrenScript(self, names, path = None):
        if not path:
            path = self.path

        script= "\n".join(
                ["function onReceiveOSC(msg, connections)"] +
                [f'    if string.match(msg[1], "{path}/{m}/label") then self.children[{i+1}].tabLabel = msg[2][1].value return end' for i, m in enumerate(names)] +
                ["end"])

        self.createProperty(pf.build("script", script))

        for ch in names:
            self.createOSC(tosc.OSC(path=[tosc.Partial(type="CONSTANT", value=f"/channel/{ch}/label")]))


def createPageChannel(page, frame):
    p = pager_inputs = page.createElement(CT.PAGER, '', frame, md(tabbarSize=40, orientation=0))
    frame_input = resizeFrame(frame, h=-40)
    for label, chnls in [("Inputs", CHAN), ("Auxs", AUXS), ("Fx", FXS), ("Main", ['main'])]:
        p = page_input = pager_inputs.createElement(CT.GROUP, None, frame_input)
        p.createTabProperties(label, colors.blue)

        frame_channel = resizeFrame(frame_input, h=-40)
        p = pager_channels = page_input.createElement(CT.PAGER, '', frame_input, md(tabbarSize=40, orientation=2))
        p.path = '/channel'
        p.createLabeledChildrenScript(chnls)
        for ch in chnls:
            p = page_channel = pager_channels.createElement(CT.GROUP, ch, frame_channel)
            p.createTabProperties(ch, colors.gray)

            p.createGainFader((dim.MAINX, 20, dim.MAINW, frame_channel[3]-20), None, md(color=colors.white)).createOSCDP()
            frame_config = resizeFrame(frame_channel, w=-dim.MAINW)

            p = pager_config = p.createElement(CT.PAGER, '', frame_config, md(tabbarSize=40, orientation=3))
            p.createValue(Value(key="page", default="2"))

            ctrl_pages = []
            for cfg in reversed(["General", "Comp", "Eq"]):
                p = page_cfggrp = pager_config.createElement(CT.GROUP, None, frame_config)
                p.createTabProperties(cfg, colors.green)

                ctrl_pages.append(p)
            ctrl_pages.reverse()

            frame = resizeFrame(frame_config, x=0, w=-40)

            y = [int(Frame(*frame).h * i // 3) + padding for i in range(3)]

            # General controls
            p = ctrl_pages[0]
            p = p.createElement(CT.GROUP, None, pad(frame))

            f = resizeFrame(frame_config, x=0, w=-40)

            # Common
            p.color = colors.gr

            p.createLabeledButton((0, y[0]), 'panreset', 'Pan').createOSCDP()
            p.createLabeledButton((0, y[1]), 'hpf', 'HPF', {'buttonType': 1}).createOSCDP()
            p.createLabeledButton((0, y[2]), 'gate', 'Gate', {'buttonType': 1}).createOSCDP()

            p.createLabeledButton((f[2]//2 + 160, y[0]), 'phantom', 'Phantom', md(color=colors.blue, buttonType=1)).createOSCDP()
            p.createLabeledButton((f[2]//2 + 260, y[0]), 'phase', 'Phase', md(color=colors.blue, buttonType=1)).createOSCDP()
            p.createLabeledButton((f[2]//2 + 160, y[1]), 'firewire', 'FireWire', md(color=colors.orange, buttonType=1)).createOSCDP()
            p.createLabeledButton((f[2]//2 + 260, y[1]), 'post', 'Post', md(color=colors.blue, buttonType=1)).createOSCDP()
            p.createLabeledButton((f[2]//2 + 160, y[2]), 'mute', 'Mute', md(color=colors.redsh, buttonType=1)).createOSCDP()
            p.createLabeledButton((f[2]//2 + 260, y[2]), 'solo', 'Solo', md(color=colors.yellow, buttonType=1)).createOSCDP()

            SW2 = Frame(*f).w - 5 * (60 + 20)
            items = ["pan", "hpffreq", "gatethresh"]
            p.createElement(CT.FADER, items[0], (f[0] + 80, y[0], f[2] // 2, 60), md(orientation=1, centered=1)).createOSCDP()
            p.createElement(CT.FADER, items[1], (f[0] + 80, y[1], f[2] // 2, 60), md(orientation=1)).createOSCDP()
            p.createElement(CT.FADER, items[2], (f[0] + 80, y[2], f[2] // 2, 60), md(orientation=1)).createOSCDP()

            # Compressor
            p = ctrl_pages[1]
            comp = p.createElement(CT.GROUP, 'comp', pad(frame))
            comp.descend = False
            comp.color = colors.yellow
            comp.createLabeledButton((0, y[0]), '', 'Enable', md(buttonType=1)).createOSCDP()
            comp.createLabeledButton((0, y[1]), 'auto', 'Auto', md(buttonType=1)).createOSCDP()
            comp.createLabeledButton((0, y[2]), 'limit', 'Limit', md(buttonType=1)).createOSCDP()

            items = [
                ("thresh", "Thresh"),
                ("ratio", "Ratio"),
                ("response", "Resp."),
                ("gain", "Gain")
            ]
            for i, item in enumerate(items):
                name, label = item
                comp.createLabeledFader(((i+1)*80, 20, 60, pad(frame)[3]-2*padding), name, label).createOSCDP()

            p = ctrl_pages[2]

            # Equalizer
            eq = p.createElement(CT.GROUP, "eq", pad(frame))
            eq.color = colors.ltblue
            eq.descend = False

            itemw = (Frame(*eq.getInnerFrame()).w + margin) // 3
            item1w = 60
            item2w = itemw - (item1w + 2*margin)
            x1 = [itemw * i + 0 * margin for i in range(3)]
            x2 = [itemw * i + 1 * margin + item1w for i in range(3)]

            items = [("low", "Low"), ("mid", "Mid"), ("high", "High")]
            for i, (name, label) in enumerate(items):
                eq.createElement(CT.FADER, name + 'freq', (x1[i], 0, 60, eq.getH()), {'centered': 1}).createOSCDP()
                eq.createElement(CT.RADIAL, name + 'gain', (x2[i], 0, item2w, item2w), {'shape': 2, 'centered': 1}).createOSCDP()

                l = eq.createElement(CT.LABEL, name + 'freq', (x1[i], 0, 60, eq.getH()), md(background=0))
                l.createOSCDP()
                l.createProperty(pf.build("script", getattr(ElementTOSC, f"script_float2eq{name}")))

                l = eq.createElement(CT.LABEL, name + 'gain', (x2[i], 0, item2w, item2w), md(background=0))
                l.createOSCDP()
                # TODO: fix compute function
                l.createProperty(pf.build("script", ElementTOSC.script_float2db15))


            items = [
                ("low", "Low"),
                ("lowshelf", "Shelf"),
                ("mid", "Mid"),
                ("midhiq", "HiQ"),
                ("high", "High"),
                ("highshelf", "Shelf")
            ]
            for i, item in enumerate(items):
                name, label = item
                fr=(x2[i//2] + (item2w-3*margin) // 2 + ((i % 2) * 2 - 1) * (30 + margin//2) , eq.getH() - 60 - margin)
                eq.createLabeledButton(fr, name, label, {'buttonType': 1}).createOSCDP()


def createPageMixer(p, frame):
    p.path = "/channel"
    for i, name in enumerate(CHAN):
        p.createGainFader((i * dim._INW + 20, 20, dim.FW, frame[3]-20), name, md(color=colors.redsh if i < 8 else colors.yellow)).createOSCDP()

    p.createGainFader((dim.MAINX, 20, dim.MAINW, frame[3]-20), 'main', md(color=colors.white)).createOSCDP()

def createPageAux(p, frame):
    p.path = "/channel"

    p = pager_channels = p.createElement(CT.PAGER, '', frame, md(tabbarSize=40, orientation=2))
    p.createLabeledChildrenScript(AUXS + FXS)

    frame = resizeFrame(frame, h=-40)
    for j, target in enumerate(AUXS + FXS):
        p = page_channel = pager_channels.createElement(CT.GROUP, target, frame)
        path = f'/channel/{target}/gain'
        p.createTabProperties(target, colors.gray)
        e = p.createGainFader((dim.MAINX, 20, dim.MAINW, frame[3]-30), 'gain', md(color=colors.white), label_path=f'/channel/{target}/label', path=path)
        e.createOSCDP(path)

        for i, inp in enumerate(CHAN):
            path = f'/channel/{inp}/{target}'
            e = p.createGainFader((i * dim._INW + 20, 20, dim.FW, frame[3]-30), inp, md(color=colors.redsh if i < 8 else colors.yellow), label_path=f'/channel/{inp}/label', path=path)
            e.createOSCDP(path)


def createPageMisc(p, frame):
    p.path = "/channel"

    page = p
    for i, ch in enumerate(CHAN):
        p = page.createElement(CT.GROUP, ch, setFrame(frame, x=i*80 + padding, w=80))
        h = frame[3]

        p.createLabeledButton((0, h-320), 'peak_reset', 'R.Peak', md(color=colors.redsh)).createOSCDP()
        p.createLabeledButton((0, h-240), 'firewire', 'FireWire', md(buttonType=1, color=colors.orange)).createOSCDP()
        p.createLabeledButton((0, h-160), 'solo', 'Solo', md(buttonType=1, color=colors.yellow)).createOSCDP()
        p.createLabeledButton((0, h-80), 'mute', 'Mute', md(buttonType=1, color=colors.redsh)).createOSCDP()

        r = p.createElement(CT.RADIO, 'level', (10, 20, 40, h-360), md(interactive=0, color=colors.green, orientation=0, steps=16, radioType=1)).createOSCDP()

        yellow_alpha = colors.yellow[0:3] + (0.5,)
        e = p.createElement(CT.RADIO, 'peak',  (10, 20, 40, h-360), md(interactive=0, color=yellow_alpha, orientation=0, steps=16, background=0)).createOSCDP()

        args=[tosc.Partial(type="VALUE", conversion="STRING", value="text")]
        p.createElement(CT.LABEL, 'label', (0, h-20, 60, 20), md(background=0)).createOSCDP(arguments=args)


def createPageEqualizer(p, frame):
    p.path = "/channel"
    p = p.createElement(CT.GROUP, 'geq0', frame)
    for i, name in enumerate(geq_freqs):
        w = frame[2] // len(geq_freqs)
        fr = setFrame(resizeFrame(frame, h=-140), x=i*w, y=100, w=w-5)
        e = p.createElement(CT.FADER, str(i+1), fr, md(centered=1, color=colors.white))
        e.createOSCDP()

        l = p.createElement(CT.LABEL, str(i+1), setFrame(fr, h=30, y=70), md(background=0))
        l.createValue(Value(key="text", default=name))

    p.createLabeledButton((10, 10), 'enable', 'Enable', md(buttonType=1, color=colors.green)).createOSCDP()
    p.createLabeledButton((80, 10), 'reset', 'Reset', md(color=colors.redsh)).createOSCDP()

def createTabPlayer(p, oc):
    p.createTabProperties("Player", colors.yellow)
    p.createLabeledButton((10, 10), 'play', 'Play', md(buttonType=1, color=colors.green)).createOSCDP(osc=oc)
    f = p.createElement(CT.FADER, "seek", (80, 80, Frame(*p.getFrame()).w-20, 60), md(orientation=1, color=colors.red)).createOSCDP(osc=oc)

def createPageMidibox(p, frame):
    p.path = "/midibox"
    oc = {"connections": "00010"}

    layers = p.createElement(CT.PAGER, 'layers', frame, md(tabbarSize=40))

    page = layers.createElement(CT.GROUP, "player", resizeFrame(layers.getFrame(), h=-40))
    page.path = p.path
    page.createTabProperties("Global", colors.yellow)
    page.createLabeledButton((10, 10), 'enable', 'Enable', md(buttonType=1, color=colors.green)).createOSCDP(
            arguments=[tosc.Partial(type="VALUE", conversion="BOOLEAN", value="x")], osc=oc)

    page = layers.createElement(CT.GROUP, "player", resizeFrame(layers.getFrame(), h=-40))
    page.path = "/player"
    createTabPlayer(page, oc)

    for index in range(8):
        page = layers.createElement(CT.GROUP, f"{index}", None)
        page.createTabProperties(f"{index}", colors.gray)
        page.path = layers.path + f"/{index}"

        args_bool = md(arguments=[tosc.Partial(type="VALUE", conversion="BOOLEAN", value="x")], osc=oc)
        args_uint = md(arguments=[tosc.Partial(type="VALUE", conversion="INTEGER", value="x", scaleMin="0", scaleMax="127")], osc=oc)
        args_sint = md(arguments=[tosc.Partial(type="VALUE", conversion="INTEGER", value="x", scaleMin="-64", scaleMax="63")], osc=oc)

        page.createLabeledButton((10, 10), 'enabled', 'Enable', md(buttonType=1, color=colors.green)).createOSCDP(**args_bool)
        page.createLabeledButton((10, 80), 'active', 'Active', md(buttonType=1, color=colors.green)).createOSCDP(**args_bool)

        page.createLabeledFader(((1)*80, 80, 80, 300), "volume", "Volume", md(color=colors.red)).createOSCDP(**args_uint)
        page.createLabeledFader(((2)*80, 80, 80, 300), "transposition", "Transposition", md(color=colors.red)).createOSCDP(**args_sint)

def main():
    name = "StudioLive1602"
    filename = str(Path.home() / "Documents" / "TouchOSC" / (name + ".tosc"))

    argp = argparse.ArgumentParser()
    argp.add_argument("-o", "--output", help="Output file", default=filename)
    args = argp.parse_args()

    frame = (0, 0, dim.SW, dim.SH)
    root = tosc.createTemplate(frame=frame)
    template = ElementTOSC(root[0])
    template.createProperty(pf.build("script", "function init() sendOSC('/init') end"))

    pager = template.createElement(CT.PAGER, 'pager', frame, md(tabbarSize=40), path = "")

    pages_cfg = [
        ("channel",   "Channel", createPageChannel),
        ("mixer",     "Mixer", createPageMixer),
        ("aux",       "Sends", createPageAux),
        ("misc",      "Misc", createPageMisc),
        ("equalizer", "Equalizer", createPageEqualizer),
        ("midibox",   "Midibox", createPageMidibox),
    ]
    for name, text, initfn in pages_cfg:
        page = pager.createElement(CT.GROUP, name, None)
        page.createTabProperties(text, colors.gray)

        if initfn:
            initfn(page, resizeFrame(pager.getFrame(), h=-40))

    lb = template.createLabeledButton((dim.SW-40, 0, 40, 40), 'connection_ping', "live", md(interactive=0, color=colors.green)).createOSCDP()

    tosc.write(root, args.output)


if __name__ == "__main__":
    main()
