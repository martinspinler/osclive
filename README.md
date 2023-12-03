# osclive
Python OSC server for remote control of the PreSonus StudioLive mixer

# Motivation
Original tool from PreSonus provides remote control application only for iOS.
*osclive* is an alternative solution, which provides standard [OSC](https://en.wikipedia.org/wiki/Open_Sound_Control) interface.
The OSC interface can be adapted by various GUI clients.

# Supported hardware

Currently the *osclive* server is tested on [StudioLive 16.0.2](https://legacy.presonus.com/products/StudioLive-16.0.2) FireWire version,
but maybe it can be expanded to other models.

Osclive implements two backends for communication with mixer:

1. Universal Control client:

     Connects to the Universal Control application running on Windows or MacOS.

2. Direct access to the mixer over FireWire

     Connects to the mixer over raw1394 library and directly accesses mixer configuration registers.
     The pyraw1394 library is currently Linux only, but works also on ARM (tested on RPi4-CM with PCIe FireWire adapter).

Both backend methods are reverese-engineered, so not all features of the original control application can be used,
but the main functionality is supported and stable.

# Setup

Install this Python package as usual:

`pip install --user https://github.com/martinspinler/osclive`

For the raw1394 backend you need also to install [pyraw1394](https://github.com/martinspinler/pyraw1394) library.

Run `osclive` main script (your Python bin folder should be already in PATH env var).

For the UC backend use the `-u addr` parameter, where `addr` is the IP address of the server running Universal Control application.

# Client

The recommended client is [TouchOSC](https://hexler.net/touchosc).

You can generate layout for TouchOSC by script located in `tools/topyg.py`.
The scripts needs just the [tosclib](https://github.com/AlbertoV5/tosclib) Python library.

The *osclive* server broadcasts a Zeroconf service info, if your client doesn't support Zeroconf, use the TCP protocol with OSC 1.0 framing and port 4301.
