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

from config import *

# StudioLive object
sl = StudioLive1602(debug = True, local = False)
sl.connect(args.slip)
sl.start()
#while(not sl.loaded):
time.sleep(2)

# Client handler object
client_handler = ClientHandler(OSCClient, sl, 8080)

# OSC UDP Server
server = ClientBasedOSCUDPServer((args.oscip, args.oscport), client_handler)
server_thread = threading.Thread(target=server.serve_forever)
server_thread.start()
print("Serving OSC UDP server on {}".format(server.server_address))

# Zeroconf server & client
zeroconf_service = "_osc._udp.local."
zeroconf = Zeroconf([args.oscip])
print("OSCServer" + zeroconf_service)
zeroconf.register_service(ServiceInfo(zeroconf_service, "OSCServer"+"."+zeroconf_service, socket.inet_aton(args.oscip), args.oscport, 0, 0, {}))
browser = ServiceBrowser(zeroconf, zeroconf_service, ClientScanner(client_handler))
