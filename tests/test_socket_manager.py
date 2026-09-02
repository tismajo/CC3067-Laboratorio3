import socket
import threading

import pytest

from node.network.socket_manager import NeighborUnreachableError, SocketManager
from shared.protocol import build_packet, deserialize


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_send_delivers_packet_to_listener():
    port = _free_port()
    manager = SocketManager("127.0.0.1", port)

    received = {}
    got_packet = threading.Event()

    def on_packet_received(raw, addr):
        received["raw"] = raw
        received["addr"] = addr
        got_packet.set()

    manager.start_listening(on_packet_received)
    try:
        packet = build_packet(
            proto="flooding", type_="message", from_="A", to="B", payload="hola"
        )
        sender = SocketManager("127.0.0.1", _free_port())
        sender.send("127.0.0.1", port, packet)

        assert got_packet.wait(timeout=2)
        assert deserialize(received["raw"]) == packet
    finally:
        manager.stop()


def test_send_to_closed_port_raises_neighbor_unreachable():
    manager = SocketManager("127.0.0.1", _free_port())
    packet = build_packet(
        proto="flooding", type_="hello", from_="A", to="B", payload=None
    )

    with pytest.raises(NeighborUnreachableError):
        manager.send("127.0.0.1", _free_port(), packet)
