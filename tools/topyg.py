#!/usr/bin/python
from touchoscgen import *

name = "StudioLive1602"
CHAN = ["ch%d" %(i + 1) for i in range(12)]
AUXS = ["aux%d" %(i + 1) for i in range(4)] + ["fxa", "fxb"]

SH    = 540
SW    = 1080

MAINW = 120

INS   = len(CHAN)
INW   = int((SW - MAINW - 30) / INS)
FW    = INW - 20

pages = {}
pages[0] = create_page("1", "Mixer")
pages[1] = create_page("2", "Aux")
pages[2] = create_page("3", "Channel")

root = create_layout(SW, SH)
for p in pages:
    root.append(pages[p])

def create_led_bar(p, ctrl, x, y):
    for i in range(16):
        color = "green"
        if (i > 10):
            color = "yellow"
        if (i == 15):
            color = "red"
        p.append(create_led(None, color, ctrl, x, y + i*28, 25, 25, i / 16.0, (i+1) / 16.0))

MAINX = SW-MAINW-10
SW2= int(SW/2)
X0 = 10
X1 = int(SW/10*3)
X2 = int(SW/5*3)

# ########################################
# Page 0
p = pages[0]
for i in range(INS):
    create_led_bar(p, "/%s/level" % CHAN[i], i*INW+10, 30)

create_led_bar(p, "/main/level", SW-MAINW-20, 30)

LY = int((SH - 80)*0.75) + 20

color = "red"
for i in range(INS):
    if (i >= 8):
        color = "yellow"
    p.append(create_fader(None, color, "/%s/gain"              % CHAN[i], i*INW+20, 30    , FW   , SH-80))
    p.append(create_label(None, color, "/%s/label"             % CHAN[i], i*INW+20,  0    , FW   ,    30, "%s" % CHAN[i]))
    p.append(create_label(None, color, "/%s/gain_db"           % CHAN[i], i*INW+20, LY    , FW   ,    20, ""))

color = "gray"
p.append(create_fader(None, color, "/main/gain"                         , MAINX   , 30    , MAINW, SH-80))
p.append(create_label(None, color, "/main/label"                        , MAINX   ,  0    , MAINW,    30, "Main"))
p.append(create_label(None, color, "/main/gain_db"                      , MAINX   , LY    , MAINW,    20, ""))

# ########################################
# Page 1
p = pages[1]

LY = int((SH - 160) * 0.75) + 20

color = "red"
for i in range(INS):
    if (i >= 8):
        color = "yellow"
    p.append(create_fader(None, color, "/aux/%s"               % CHAN[i], i*INW+20, 30    , FW   , SH-160))
    p.append(create_label(None, color, "/aux/%s_label"         % CHAN[i], i*INW+20,  0    , FW   ,     30, "%s" % CHAN[i]))
    p.append(create_label(None, color, "/aux/%s_gain_db"       % CHAN[i], i*INW+20, LY    , FW   ,     20, ""))

color = "gray"
for i in range(len(AUXS)):
    p.append(create_push (None, color, "/aux/sel/%s"           % AUXS[i], i*INW+20, SH-120, FW   ,     50))
    p.append(create_label(None, color, "/aux/sel/%s_label"     % AUXS[i], i*INW+20, SH-120, FW   ,     50, "%s" % AUXS[i]))

p.append(create_fader(None, color, "/aux/gain"                          , MAINX   , 30    , MAINW, SH-160))
p.append(create_label(None, color, "/aux/label"                         , MAINX   ,  0    , MAINW,     30, "Main"))
p.append(create_label(None, color, "/aux/gain_db"                       , MAINX   , LY    , MAINW,     20, ""))

# ########################################
# Page 2
p = pages[2]

color = "green"
p.append(create_push  (None, color, "/channel/panreset"                 ,  X0     , SH-140,      60,   60))
p.append(create_toggle(None, color, "/channel/hpf"                      ,  X0     , SH-220,      60,   60))
p.append(create_toggle(None, color, "/channel/gate"                     ,  X0     , SH-300,      60,   60))
p.append(create_label (None, color, None                                ,  X0     , SH-140,      60,   60, "Pan"))
p.append(create_label (None, color, None                                ,  X0     , SH-220,      60,   60, "HPF"))
p.append(create_label (None, color, None                                ,  X0     , SH-300,      60,   60, "Gate"))
p.append(create_fader (None, color, "/channel/pan"                      , 100     , SH-140, SW2-120,   60, 'v'))
p.append(create_fader (None, color, "/channel/hpffreq"                  , 100     , SH-220, SW2-120,   60, 'v'))
p.append(create_fader (None, color, "/channel/gatethresh"               , 100     , SH-300, SW2-120,   60, 'v'))

color = "yellow"
p.append(create_toggle(None, color, "/channel/comp"                     , SW2     , SH-140,      60,   60))
p.append(create_toggle(None, color, "/channel/compauto"                 , SW2     , SH-220,      60,   60))
p.append(create_toggle(None, color, "/channel/limit"                    , SW2     , SH-300,      60,   60))
p.append(create_label (None, color, None                                , SW2     , SH-140,      60,   60, "Comp"))
p.append(create_label (None, color, None                                , SW2     , SH-220,      60,   60, "Auto"))
p.append(create_label (None, color, None                                , SW2     , SH-300,      60,   60, "Limit"))

p.append(create_fader (None, color, "/channel/compthresh"               , SW2+ 80 , SH-300,      60,  220))
p.append(create_fader (None, color, "/channel/compratio"                , SW2+160 , SH-300,      60,  220))
p.append(create_fader (None, color, "/channel/compresponse"             , SW2+240 , SH-300,      60,  220))
p.append(create_fader (None, color, "/channel/compgain"                 , SW2+320 , SH-300,      60,  220))
p.append(create_label (None, color, None                                , SW2+ 80 , SH-220,      60,   60, "Thresh"))
p.append(create_label (None, color, None                                , SW2+160 , SH-220,      60,   60, "Ratio"))
p.append(create_label (None, color, None                                , SW2+240 , SH-220,      60,   60, "Response"))
p.append(create_label (None, color, None                                , SW2+320 , SH-220,      60,   60, "Gain"))

color = "blue"
p.append(create_toggle(None, color, "/channel/eqlow"                    , X0      , SH-400,      60,   60))
p.append(create_toggle(None, color, "/channel/eqlowshelf"               , X0      , SH-480,      60,   60))
p.append(create_toggle(None, color, "/channel/eqmid"                    , X1      , SH-400,      60,   60))
p.append(create_toggle(None, color, "/channel/eqmidhiq"                 , X1      , SH-480,      60,   60))
p.append(create_toggle(None, color, "/channel/eqhigh"                   , X2      , SH-400,      60,   60))
p.append(create_toggle(None, color, "/channel/eqhighshelf"              , X2      , SH-480,      60,   60))
p.append(create_label (None, color, None                                , X0      , SH-400,      60,   60, "Low"))
p.append(create_label (None, color, None                                , X0      , SH-480,      60,   60, "Shelf"))
p.append(create_label (None, color, None                                , X1      , SH-400,      60,   60, "Mid"))
p.append(create_label (None, color, None                                , X1      , SH-480,      60,   60, "HiQ"))
p.append(create_label (None, color, None                                , X2      , SH-400,      60,   60, "High"))
p.append(create_label (None, color, None                                , X2      , SH-480,      60,   60, "Shelf"))
p.append(create_fader (None, color, "/channel/eqlowgain"                , X0+220  , SH-480,      60,  140))
p.append(create_fader (None, color, "/channel/eqmidgain"                , X1+220  , SH-480,      60,  140))
p.append(create_fader (None, color, "/channel/eqhighgain"               , X2+220  , SH-480,      60,  140))
p.append(create_rotary(None, color, "/channel/eqlowfreq"                , X0+ 80  , SH-480,     120,  120))
p.append(create_rotary(None, color, "/channel/eqmidfreq"                , X1+ 80  , SH-480,     120,  120))
p.append(create_rotary(None, color, "/channel/eqhighfreq"               , X2+ 80  , SH-480,     120,  120))

create_led_bar(p, "/channel/level", MAINX-10, 30)

LY = int((SH - 80)*0.75) + 20
color = "gray"
p.append(create_fader(None, color, "/channel/gain"                      , MAINX   ,  30   ,   MAINW, SH-80))
p.append(create_label(None, color, "/channel/label"                     , MAINX   ,   0   ,   MAINW,   30, "Main"))
p.append(create_label(None, color, "/channel/gain_db"                   , MAINX   ,  LY   ,   MAINW,   20, ""))

for i in range(len(CHAN)):
    p.append(create_push (None, color, "/channel/sel/%s"       % CHAN[i], i*INW+20,  10   ,   FW   ,   40))
    p.append(create_label(None, color, "/channel/sel/%s_label" % CHAN[i], i*INW+20,  10   ,   FW   ,   40, "%s" %  CHAN[i]))

# ########################################
# Finish

write_layout(root, name)
