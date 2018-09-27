#!/usr/bin/env python3
import threading
import argparse
import socket
import time

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf

from StudioLive import StudioLive1602

from pythonosc import osc_message_builder
from pythonosc import udp_client

from OSCServer import ClientHandler, ClientScanner, ClientBasedOSCUDPServer
from OSCClient import OSCClient
from transport import *

from misc import *

from config import *

# StudioLive object
sl = StudioLive1602(args.debug)
sl.connect(args.slip)

while(not sl.loaded):
	time.sleep(1)

tr = NullTransport() if not args.transport_device else Transport(args.transport_device, args.transport_samplerate, args.transport_channels)

# Client handler object
client_handler = ClientHandler(OSCClient, (sl, tr, args.active_channels, args.active_auxs), 8080)

# OSC UDP Server
server = ClientBasedOSCUDPServer((args.oscip, args.oscport), client_handler)
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()
print("Serving OSC server on {}".format(server.server_address))

# Zeroconf server & client
zc_service = "_osc._udp.local."
zc_name = args.oscname + "." + zc_service
zeroconf = Zeroconf()
ServiceBrowser(zeroconf, zc_service, ClientScanner(client_handler, args.oscname))

# Populate empty Zeroconf IP address list
if not args.zcip:
	args.zcip = getIPv4Addresses()

# Workaround to publish all IP addresses
for ip in args.zcip:
	zc = Zeroconf([ip])
	zc.register_service(ServiceInfo(zc_service, zc_name, socket.inet_aton(ip), args.oscport, 0, 0, {}))
	print("Zeroconf register %s on IP %s" % (zc_name, ip))
