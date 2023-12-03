import socket
import socketserver
import threading

import netifaces

from typing import List, Tuple, Union, Any, Iterable

from pythonosc import osc_packet
from pythonosc.osc_message_builder import OscMessageBuilder

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf


class ThreadedTCPOSCRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        print("OSC TCP client connected", self.client_address)
        self.server.clients.append(self)

    def _recv(self, size):
        data = b''
        while len(data) != size: # and self.alive.is_set():
            try:
                data += self.request.recv(size - len(data))
            except socket.timeout:
                pass
            except OSError:
                return None

        return data if len(data) == size else None

    def handle(self):
        while True:
            sz = self._recv(4)
            if sz is None:
                break

            data = self._recv(int.from_bytes(sz, byteorder='little'))
            if data is None:
                break

            for m in osc_packet.OscPacket(data).messages:
                self.handle_message(m.message.address, m.message.params)

    def finish(self):
        self.server.clients.remove(self)
        print("OSC TCP client disconnected", self.client_address)

    def handle_message(self, address, params):
        pass

    def send_message(self, address: str, value: Union[int, float, bytes, str, bool, tuple, list]) -> None:
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            values = [value]
        else:
            values = value
        for val in values:
            builder.add_arg(val)
        msg = builder.build()
        try:
            self.request.sendall(msg.size.to_bytes(length=4, byteorder='little') + msg._dgram)
        except:
            pass


class DispatchedOSCRequestHandler(ThreadedTCPOSCRequestHandler):
    def map(self, path, callback, *args):
        self._dispatcher_maps[path] = (callback, args)

    def setup(self):
        super().setup()
        self._dispatcher_maps = {}

    def handle_message(self, address: str, value: Union[int, float, bytes, str, bool, tuple, list]) -> None:
        mapping = self._dispatcher_maps.get(address)
        if mapping:
            callback, args = mapping
            if args:
                callback(address, args, *value)
            else:
                callback(address, *value)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class SharedTCPServer():
    def __init__(self, RequestHandler, port=4301, addr="0.0.0.0"):
        self.clients = []

        self.server = ThreadedTCPServer((addr, port), RequestHandler)
        self.server.clients = self.clients
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def shutdown(self):
        for c in self.server.clients:
            c.request.shutdown(socket.SHUT_RDWR)
            c.request.close()
        self.server.shutdown()
        self.server_thread.join()


def getIPv4Addresses():
    ret = {}
    for i in netifaces.interfaces():
        if i == 'lo':
            continue
        try:
            ret[i] = netifaces.ifaddresses(i)[netifaces.AF_INET][0]['addr']
        except KeyError:
            pass
    return ret


def zc_register_osc_tcp(port=4301, oscname="OSCLive"):
    zc_service = "_osc._tcp.local."
    zc_name = oscname + "." + zc_service
    zc_svcs = []
    # Workaround to publish all IP addresses
    for ifname, ip in getIPv4Addresses().items():
        zc_name = f"{oscname}_{ifname}.{zc_service}"
        si = ServiceInfo(zc_service, zc_name, port, addresses = [ip])
        zc = Zeroconf([ip])
        zc.register_service(si)
        print("Zeroconf register %s on IP %s" % (zc_name, ip))
        zc_svcs.append((zc, si))
    return zc_svcs
