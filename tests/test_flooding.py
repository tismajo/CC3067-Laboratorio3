"""Fase 2: pruebas unitarias de node/algorithms/flooding/*"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from node.algorithms.flooding.flooding import (
    FloodingRoutingAlgorithm,
    decrement_ttl,
    get_forward_targets,
    get_packet_id,
    should_forward,
)
from node.algorithms.flooding.neighbor_discovery import NeighborTable
from shared import constants as c
from shared.protocol import build_message, get_header


ROOT = Path(__file__).parents[1]

A = "10.0.0.1:5000"
B = "10.0.0.2:5000"
CN = "10.0.0.3:5000"
D = "10.0.0.4:5000"


class Clock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def make_packet(ttl=4, msg_id="packet-1", payload="hola"):
    return build_message(
        proto=c.PROTO_FLOODING, type_=c.TYPE_MESSAGE,
        src=A, dst=D, ttl=ttl, msg_id=msg_id, payload=payload,
    )


@pytest.mark.parametrize("ttl", [1, 0, -1, None, "3", True])
def test_should_forward_rejects_exhausted_or_invalid_ttl(ttl):
    packet = make_packet()
    packet[c.FIELD_TTL] = ttl
    assert should_forward(packet, set()) is False


def test_should_forward_accepts_once_and_rejects_duplicate():
    packet = make_packet(ttl=3)
    seen = set()

    assert should_forward(packet, seen) is True
    assert should_forward(packet, seen) is False
    assert seen == {"packet-1"}


def test_packet_id_falls_back_to_from_to_type_payload_without_ttl():
    packet = make_packet()
    packet[c.FIELD_HEADERS] = []  # sin msg_id
    decremented = decrement_ttl(packet)
    assert get_packet_id(packet) == get_packet_id(decremented)


def test_decrement_ttl_returns_copy_without_mutating_original():
    packet = make_packet(ttl=4)
    forwarded = decrement_ttl(packet)

    assert packet[c.FIELD_TTL] == 4
    assert forwarded[c.FIELD_TTL] == 3
    assert forwarded is not packet


def test_decrement_ttl_rejects_zero_and_invalid_values():
    packet = make_packet()
    packet[c.FIELD_TTL] = 0
    with pytest.raises(ValueError):
        decrement_ttl(packet)

    packet[c.FIELD_TTL] = "4"
    with pytest.raises(ValueError):
        decrement_ttl(packet)


def test_get_forward_targets_uses_active_neighbors_and_excludes_sender():
    table = NeighborTable([{"node_id": B}, {"node_id": CN}, {"node_id": D}])
    table.mark_up(B)
    table.mark_up(CN)

    targets = get_forward_targets(make_packet(), table, B)
    assert [target["node_id"] for target in targets] == [CN]


def test_hello_marks_active_and_echo_measures_rtt():
    clock = Clock(10.0)
    table = NeighborTable([{"node_id": B}], clock=clock)
    hello = table.build_hello_packet(
        {"node_id": A, "ip": "10.0.0.1", "port": 5000, "proto": "flooding"}, B
    )

    assert hello[c.FIELD_TYPE] == c.TYPE_HELLO
    assert hello[c.FIELD_TTL] == 1
    assert get_header(hello, c.HEADER_T0) == 10.0
    assert hello[c.FIELD_PAYLOAD] == {"listen_port": 5000}

    # El vecino responde el echo (mismo t0). Nuestro reloj avanzó 0.25 s.
    clock.now = 10.25
    echo = dict(hello, **{c.FIELD_TYPE: c.TYPE_ECHO, c.FIELD_FROM: B, c.FIELD_TO: A})
    neighbor = table.on_echo_received(echo)

    assert neighbor["node_id"] == B
    assert neighbor["active"] is True
    assert neighbor["delay"] == pytest.approx(0.25)


def test_neighbor_marked_down_after_timeout():
    clock = Clock(100.0)
    table = NeighborTable([{"node_id": B}], timeout=5, clock=clock)
    table.mark_up(B)

    clock.now = 104.9
    assert table.expire_stale() == []
    clock.now = 105.0
    assert table.expire_stale() == [B]
    assert table.get_active_neighbors() == []


def test_flood_prepares_one_copy_per_target_and_tracks_duplicate():
    algorithm = FloodingRoutingAlgorithm()
    algorithm.initialize(B, [{"node_id": A}, {"node_id": CN}, {"node_id": D}])
    algorithm.get_outgoing_packets()
    for node_id in (A, CN, D):
        algorithm.handle_neighbor_up(node_id)

    packet = make_packet(ttl=3)
    transmissions = algorithm.flood(packet, received_from=A)

    assert sorted(n["node_id"] for n, _ in transmissions) == [CN, D]
    assert all(copy[c.FIELD_TTL] == 2 for _, copy in transmissions)
    assert algorithm.flood(packet, received_from=A) == []


def test_handle_info_packet_queues_one_copy_per_neighbor():
    algorithm = FloodingRoutingAlgorithm()
    algorithm.initialize(B, [{"node_id": A}, {"node_id": CN}, {"node_id": D}])
    algorithm.get_outgoing_packets()
    for node_id in (A, CN, D):
        algorithm.handle_neighbor_up(node_id)

    algorithm.handle_info_packet(make_packet(ttl=4, msg_id="lsp-1"))

    queued = algorithm.get_outgoing_packets()
    assert sorted(packet[c.FIELD_TO] for packet in queued) == [CN, D]
    assert all(packet[c.FIELD_TTL] == 3 for packet in queued)


def test_routing_algorithm_neighbor_events_and_initial_hello_queue():
    algorithm = FloodingRoutingAlgorithm()
    algorithm.initialize(A, [{"node_id": B}, {"node_id": CN}])

    hellos = algorithm.get_outgoing_packets()
    assert [packet[c.FIELD_TO] for packet in hellos] == [B, CN]
    assert algorithm.get_next_hop(B) is None

    algorithm.handle_neighbor_up(B)
    assert algorithm.get_next_hop(B) == B
    algorithm.handle_neighbor_down(B)
    assert algorithm.get_next_hop(B) is None


def test_standalone_flooding_mode(tmp_path):
    config_path = tmp_path / "topology.json"
    config_path.write_text(
        json.dumps(
            {
                "node_id": "A",
                "neighbors": [
                    {"node_id": "B", "ip": "127.0.0.1", "port": 5001},
                    {"node_id": "C", "ip": "127.0.0.1", "port": 5002},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "node.main", "--config", str(config_path), "--mode", "flooding"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )

    assert "Flooding desde A" in result.stdout
    assert "vecinos configurados: B, C" in result.stdout
    assert "HELLO pendientes: 2" in result.stdout
