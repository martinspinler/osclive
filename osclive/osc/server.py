import socket
import socketserver
import threading

import netifaces

from typing import Union, Any, Optional, Iterable, Callable

from pythonosc import osc_packet
#from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_bundle_builder import OscBundleBuilder, IMMEDIATELY

from zeroconf import ServiceInfo, Zeroconf

type BaseOscValue = Union[int, float, bytes, str, bool]
type OscValue = Union[int, float, bytes, str, bool, list[BaseOscValue]]
type DORHCallback = Union[Callable[[str, Any, Any], None], Callable[[str, Any], None], Callable[[str], None]]


class ThreadedTCPOSCRequestHandler(socketserver.BaseRequestHandler):
    _bundle: Optional[list[Any]]
    server: "ThreadedTCPServer"

    class BundleManager:
        def __init__(self, request_handler: "ThreadedTCPOSCRequestHandler") -> None:
            self._rh = request_handler

        def __enter__(self) -> None:
            if self._rh._bundle_inner == 0:
                self._rh._bundle = []
            self._rh._bundle_inner += 1

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            self._rh._bundle_inner -= 1
            if self._rh._bundle_inner == 0:
                if self._rh._bundle:
                    bundle = self._rh._bundle
                    self._rh._bundle = None
                    self._rh.send_bundle(bundle)

    def setup(self) -> None:
        super().setup()
        print("OSC TCP client connected", self.client_address)

        self._bundle = None
        self._bundle_inner = 0

        self.server.clients.append(self)

    def _recv(self, size: int) -> Optional[bytes]:
        data = b''
        while len(data) != size:
            recv = self.request.recv(size - len(data))
            if not recv:
                return None
            data += recv
        return data

    def handle(self) -> None:
        while True:
            sz = self._recv(4)
            if sz is None:
                break

            data = self._recv(int.from_bytes(sz, byteorder='big'))
            if data is None:
                break

            for m in osc_packet.OscPacket(data).messages:
                self.handle_message(m.message.address, m.message.params)

    def finish(self) -> None:
        print("OSC TCP client disconnected", self.client_address)
        self.server.clients.remove(self)
        super().finish()

    def handle_message(self, address: str, value: OscValue) -> None:
        pass

    def bundle(self) -> BundleManager:
        return self.BundleManager(self)

    def send_bundle(self, msg_list: list[OscBundle]) -> None:
        bb = OscBundleBuilder(IMMEDIATELY)
        for msg in msg_list:
            bb.add_content(msg)
        bundle = bb.build()
        self.request.sendall(bundle.size.to_bytes(length=4, byteorder='big') + bundle.dgram)

    def send_message(self, address: str, value: OscValue) -> None:
        builder = OscMessageBuilder(address=address)
        values: list[BaseOscValue]
        if value is None:
            values = []
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            values = [value]
        else:
            values = value

        for val in values:
            builder.add_arg(val)
        msg = builder.build()

        if self._bundle is None:
            try:
                self.request.sendall(msg.size.to_bytes(length=4, byteorder='big') + msg._dgram)
            except Exception:
                pass
        else:
            self._bundle.append(msg)


class DispatchedOSCRequestHandler(ThreadedTCPOSCRequestHandler):
    def map(self, path: str, callback: DORHCallback, *args: Any) -> None:
        self._dispatcher_maps[path] = (callback, args)

    def setup(self) -> None:
        super().setup()
        self._dispatcher_maps: dict[str, tuple[DORHCallback, Any]] = {}

    def handle_message(self, address: str, value: OscValue) -> None:
        mapping = self._dispatcher_maps.get(address)
        if mapping:
            callback: Any  # DORHCallback
            callback, args = mapping
            if args:
                callback(address, args, *value)
            else:
                callback(address, *value)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    clients: list[socketserver.BaseRequestHandler]


class SharedTCPServer():
    clients: list[socketserver.BaseRequestHandler]

    def __init__(self, RequestHandler: type[socketserver.BaseRequestHandler], port: int = 4301, addr: str = "0.0.0.0"):
        self.clients = []

        self.server = ThreadedTCPServer((addr, port), RequestHandler)
        self.server.clients = self.clients
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def shutdown(self) -> None:
        for c in self.server.clients:
            try:
                c.request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                c.request.close()
        self.server.shutdown()
        self.server_thread.join()


def getIPv4Addresses() -> dict[str, Any]:
    ret = {}
    for i in netifaces.interfaces():
        if i == 'lo':
            continue
        try:
            ret[i] = netifaces.ifaddresses(i)[netifaces.AF_INET][0]['addr']
        except KeyError:
            pass
    return ret


def zc_register_osc_tcp(port: int = 4301, oscname: str = "OSCLive") -> list[tuple[Zeroconf, ServiceInfo]]:
    zc_service = "_osc._tcp.local."
    zc_name = oscname + "." + zc_service
    zc_svcs = []
    # Workaround to publish all IP addresses
    for ifname, ip in getIPv4Addresses().items():
        zc_name = f"{oscname}_{ifname}.{zc_service}"
        si = ServiceInfo(zc_service, zc_name, port, addresses=[ip])
        zc = Zeroconf([ip])
        zc.register_service(si)
        print("Zeroconf register %s on IP %s" % (zc_name, ip))
        zc_svcs.append((zc, si))
    return zc_svcs
