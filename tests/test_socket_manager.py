import socket
import threading

import pytest

from node.network.socket_manager import NeighborUnreachableError, SocketManager
from shared.protocol import build_message, parse_message, serialize


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _collector():
    received = []
    event = threading.Event()

    def on_packet_received(raw, addr):
        received.append(parse_message(raw))
        event.set()

    return received, event, on_packet_received


def test_send_delivers_packet_to_listener():
    port = _free_port()
    manager = SocketManager("127.0.0.1", port)
    received, event, handler = _collector()

    manager.start_listening(handler)
    try:
        packet = build_message(
            proto="flooding", type_="message",
            src="127.0.0.1:6000", dst=f"127.0.0.1:{port}", payload="hola",
        )
        SocketManager("127.0.0.1", _free_port()).send("127.0.0.1", port, packet)

        assert event.wait(timeout=2)
        assert received[0] == packet
    finally:
        manager.stop()


def test_two_packets_on_one_connection_are_split():
    port = _free_port()
    manager = SocketManager("127.0.0.1", port)
    received = []
    got_two = threading.Event()

    def handler(raw, addr):
        received.append(parse_message(raw))
        if len(received) == 2:
            got_two.set()

    manager.start_listening(handler)
    try:
        a = build_message(proto="lsr", type_="message", src="127.0.0.1:1", dst="127.0.0.1:2", payload="a")
        b = build_message(proto="lsr", type_="message", src="127.0.0.1:1", dst="127.0.0.1:2", payload="b")
        with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
            conn.sendall(serialize(a) + b"\n" + serialize(b) + b"\n")
        assert got_two.wait(timeout=2)
        assert [m["payload"] for m in received] == ["a", "b"]
    finally:
        manager.stop()


def test_send_to_closed_port_raises_neighbor_unreachable():
    manager = SocketManager("127.0.0.1", _free_port())
    packet = build_message(
        proto="flooding", type_="hello",
        src="127.0.0.1:1", dst="127.0.0.1:2", payload={"listen_port": 5000},
    )

    with pytest.raises(NeighborUnreachableError):
        manager.send("127.0.0.1", _free_port(), packet)
