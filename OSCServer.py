import asyncio
import socket
import socketserver
import time

from pythonosc import osc_bundle
from pythonosc import osc_message

# Client handler for UDP server
class ClientHandler(socketserver.BaseRequestHandler):
    def __init__(self, client, clientparam, defaultport = 8080):
        self.defaultport = defaultport
        self.clientparam = clientparam
        self.clienttype  = client
        self.client_addr = {}
        self.client_inst = {}

    def remove_client(self, name):
        if name not in self.client_addr.keys():
            print("Removing client %s: Error: not present" % name)
            return
        client = self.client_addr[name]
        print("Removing client %s" % name, client)
        del self.client_inst[client]
        del self.client_addr[name]

    def add_client(self, name, address, port):
        if name in self.client_addr.keys():
            print("Adding client %s: Error: already present" % name)
            return
        print("Adding client %s" % name, address, port)
        self.client_addr[name] = address
        self.client_inst[address] = self.clienttype(address, port, self.clientparam)

    def handle_requst(self, sender, request):
        address, port = sender
        client = address

        # Prevent handling unknown clients
        if client not in self.client_inst:
            return
        self.client_inst[client].handle_request(request)

# Client scanner for Zeroconf
class ClientScanner(object):
    def __init__(self, handler, localname):
        self.handler = handler
        self.localname = localname
    def remove_service(self, zeroconf, type, name):
        self.handler.remove_client(name)
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if name == self.localname:
            return
        self.handler.add_client(name, socket.inet_ntoa(info.address), info.port)

# Simple UDP handler
class _UDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.dispatcher.handle_requst(self.client_address, self.request)

# UDP server
class ClientBasedOSCUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, server_address, dispatcher):
        super().__init__(server_address, _UDPHandler)
        self._dispatcher = dispatcher

    def verify_request(self, request, client_address):
        data = request[0]
        return (osc_bundle.OscBundle.dgram_is_bundle(data) or osc_message.OscMessage.dgram_is_message(data))

    @property
    def dispatcher(self):
        return self._dispatcher
