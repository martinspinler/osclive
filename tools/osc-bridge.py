#!/usr/bin/python3 -u
"""UDP <-> TCP OSC bridge: connects Open Stage Control (UDP) to osclive (TCP).

Open Stage Control sends UDP OSC; osclive listens on TCP OSC (port 4301).
This bridge connects to osclive via TCP and translates between the two.

Usage:
    python tools/osc-bridge.py [--udp-port 4299] [--tcp-host localhost] [--tcp-port 4301]

Then in Open Stage Control, set the target to: localhost:<udp-port> (default: 4299)
"""

import socket
import struct
import threading
import time
import argparse


def main() -> None:
    argp = argparse.ArgumentParser(description="UDP-TCP OSC bridge for osclive")
    argp.add_argument("--udp-port", type=int, default=4299,
                      help="UDP listen port (default: 4299)")
    argp.add_argument("--tcp-host", default="localhost",
                      help="osclive TCP host (default: localhost)")
    argp.add_argument("--tcp-port", type=int, default=4301,
                      help="osclive TCP port (default: 4301)")
    argp.add_argument("--debug", action="store_true",
                      help="Verbose per-packet logging")
    args = argp.parse_args()

    udp_clients: set[tuple[str, int]] = set()
    # [0] is the live TCP socket; reconnects replace it in place so the
    # reader thread picks up the new socket without coordination.
    tcp_sock: list[socket.socket | None] = [None]
    lock = threading.Lock()

    def log(msg: str) -> None:
        print(msg, flush=True)

    def dbg(msg: str) -> None:
        if args.debug:
            print(msg, flush=True)

    def connect_tcp() -> socket.socket:
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((args.tcp_host, args.tcp_port))
                with lock:
                    tcp_sock[0] = s
                log(f"Bridge: connected to osclive at "
                    f"{args.tcp_host}:{args.tcp_port}")
                return s
            except ConnectionRefusedError:
                log("Bridge: osclive not available, retrying in 2s...")
                time.sleep(2)

    def send_tcp(data: bytes) -> None:
        """Send a length-prefixed OSC packet to osclive, reconnecting on failure."""
        framed = struct.pack(">I", len(data)) + data
        with lock:
            s = tcp_sock[0]
        if s is None:
            s = connect_tcp()
        try:
            s.sendall(framed)
        except OSError:
            log("Bridge: TCP send error, reconnecting...")
            s = connect_tcp()
            s.sendall(framed)

    def tcp_to_udp(udp_sock: socket.socket) -> None:
        """Forward TCP (length-prefixed) -> UDP (raw OSC) to all clients."""
        buf = b""
        while True:
            with lock:
                s = tcp_sock[0]
            if s is None:
                connect_tcp()
                continue
            try:
                data = s.recv(4096)
                if not data:
                    raise ConnectionError("TCP closed")
            except OSError:
                log("Bridge: TCP connection lost, reconnecting...")
                connect_tcp()
                buf = b""
                continue

            buf += data
            while len(buf) >= 4:
                size = struct.unpack(">I", buf[:4])[0]
                if len(buf) < 4 + size:
                    break
                packet = buf[4:4 + size]
                buf = buf[4 + size:]
                with lock:
                    targets = list(udp_clients)
                for addr in targets:
                    try:
                        udp_sock.sendto(packet, addr)
                    except OSError:
                        with lock:
                            udp_clients.discard(addr)
                dbg(f"Bridge: TCP->{len(targets)} UDP clients ({size}B)")

    def request_init() -> None:
        """Ask osclive to push the full state to this TCP connection."""
        from pythonosc.osc_message_builder import OscMessageBuilder
        msg = OscMessageBuilder("/init").build()
        send_tcp(msg.dgram)
        dbg("Bridge: sent /init to osclive")

    # -- Startup -----------------------------------------------------------

    connect_tcp()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", args.udp_port))
    log(f"Bridge: listening on UDP :{args.udp_port}")

    threading.Thread(target=tcp_to_udp, args=(udp_sock,), daemon=True).start()

    # -- Main loop: UDP -> TCP + client registration -----------------------

    while True:
        data, addr = udp_sock.recvfrom(65536)

        is_new = addr not in udp_clients
        if is_new:
            with lock:
                udp_clients.add(addr)
            log(f"Bridge: new UDP client {addr[0]}:{addr[1]} "
                f"({len(udp_clients)} total)")
            # The new client missed the initial state push that osclive sent
            # when the TCP connection was established (before any UDP client
            # existed). Request a fresh state push so the new client catches up.
            request_init()

        dbg(f"Bridge: UDP->TCP ({len(data)}B from {addr[0]}:{addr[1]})")
        send_tcp(data)


if __name__ == "__main__":
    main()
