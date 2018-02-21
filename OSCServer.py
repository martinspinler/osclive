import asyncio
import socket
import socketserver
import time

from pythonosc import osc_bundle
from pythonosc import osc_message

# Client handler for UDP server
class ClientHandler(socketserver.BaseRequestHandler):
    def __init__(self, client, clientparam, defaultport = 8080):
        self.clientparam = clientparam
        self.client = client
        self.clients = {}
        self.clientports = {}
        self.defaultport = defaultport

    def remove_client(self, address):
        assert address in self.clients
        self.clients.remove(address)
        self.clientports.remove(address)
        print("Client removed", address, port)

    def add_client(self, address, port):
        if(address in self.clients):
            self.clientports[address] = port
            print("Client already exists", address, port)
            return
        client = self.client(address, port, self.clientparam)
        self.clients[address] = client
        self.clientports[address] = port
        print("Client added", address, port)

    def handle_requst(self, client, request):
        address, port = client
        if(address not in self.clients):
            # Try add default port
            self.add_client(address, self.defaultport)
        self.clients[address].handle_request(request)

# Client scanner for Zeroconf
class ClientScanner(object):
    def __init__(self, handler):
        self.handler = handler
    def remove_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        print("Removed Zeroconf client: %s. TODO!!!" % name)
        #self.handler.remove_client(socket.inet_ntoa(info.address), info.port)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if(name == "OSCServer._osc._udp.local."):
            return
        print("New Zeroconf client: %s" % name)
        self.handler.add_client(socket.inet_ntoa(info.address), info.port)

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
