"""
Fase 2

TODO: pruebas unitarias de node/algorithms/flooding/*
- [ ] test_should_forward_respects_ttl
- [ ] test_no_duplicate_forward
- [ ] test_get_forward_targets_excludes_sender
- [ ] test_neighbor_marked_down_after_no_hello
"""
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
from shared.protocol import build_packet


ROOT = Path(__file__).parents[1]


class Clock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def make_packet(ttl=4, packet_id="packet-1", payload="hola"):
    return build_packet(
        proto=c.PROTO_FLOODING,
        type_=c.TYPE_MESSAGE,
        from_="A",
        to="D",
        ttl=ttl,
        headers=[{"packet_id": packet_id}],
        payload=payload,
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


def test_generated_packet_id_is_stable_when_ttl_changes():
    packet = make_packet()
    packet[c.FIELD_HEADERS] = []
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
    table = NeighborTable(
        [
            {"node_id": "B"},
            {"node_id": "C"},
            {"node_id": "D"},
        ]
    )
    table.mark_up("B")
    table.mark_up("C")

    targets = get_forward_targets(make_packet(), table, "B")
    assert [target["node_id"] for target in targets] == ["C"]


def test_hello_packet_and_received_neighbor_delay():
    clock = Clock(10.0)
    table = NeighborTable([{"node_id": "B"}], clock=clock)
    hello = table.build_hello_packet(
        {"node_id": "A", "ip": "10.0.0.1", "port": 5000},
        "B",
    )

    assert hello[c.FIELD_PROTO] == c.PROTO_FLOODING
    assert hello[c.FIELD_TYPE] == c.TYPE_HELLO
    assert hello[c.FIELD_TTL] == 1
    assert hello[c.FIELD_PAYLOAD]["sent_at"] == 10.0

    clock.now = 10.25
    receiver = NeighborTable(clock=clock)
    neighbor = receiver.on_hello_received(hello)

    assert neighbor["node_id"] == "A"
    assert neighbor["active"] is True
    assert neighbor["delay"] == pytest.approx(0.25)
    assert neighbor["ip"] == "10.0.0.1"
    assert neighbor["port"] == 5000


def test_neighbor_marked_down_after_no_hello():
    clock = Clock(100.0)
    table = NeighborTable([{"node_id": "B"}], timeout=5, clock=clock)
    table.mark_up("B")

    clock.now = 104.9
    assert table.expire_stale() == []
    assert table.get_neighbor("B")["active"] is True

    clock.now = 105.0
    assert table.expire_stale() == ["B"]
    assert table.get_active_neighbors() == []


def test_flood_prepares_one_copy_per_target_and_tracks_duplicate():
    algorithm = FloodingRoutingAlgorithm()
    algorithm.initialize(
        "B",
        [
            {"node_id": "A"},
            {"node_id": "C"},
            {"node_id": "D"},
        ],
    )
    algorithm.get_outgoing_packets()
    for node_id in ("A", "C", "D"):
        algorithm.handle_neighbor_up(node_id)

    packet = make_packet(ttl=3)
    transmissions = algorithm.flood(packet, received_from="A")

    assert [neighbor["node_id"] for neighbor, _ in transmissions] == ["C", "D"]
    assert all(copy[c.FIELD_TTL] == 2 for _, copy in transmissions)
    assert packet[c.FIELD_TTL] == 3
    assert algorithm.flood(packet, received_from="A") == []


def test_handle_info_packet_queues_one_copy_per_neighbor():
    algorithm = FloodingRoutingAlgorithm()
    algorithm.initialize("B", [{"node_id": "A"}, {"node_id": "C"}, {"node_id": "D"}])
    algorithm.get_outgoing_packets()
    for node_id in ("A", "C", "D"):
        algorithm.handle_neighbor_up(node_id)

    algorithm.handle_info_packet(make_packet(ttl=4, packet_id="lsp-1"))

    queued = algorithm.get_outgoing_packets()
    assert sorted(packet[c.FIELD_TO] for packet in queued) == ["C", "D"]
    assert all(packet[c.FIELD_TTL] == 3 for packet in queued)


def test_routing_algorithm_neighbor_events_and_initial_hello_queue():
    algorithm = FloodingRoutingAlgorithm()
    algorithm.initialize("A", [{"node_id": "B"}, {"node_id": "C"}])

    hellos = algorithm.get_outgoing_packets()
    assert [packet[c.FIELD_TO] for packet in hellos] == ["B", "C"]
    assert algorithm.get_outgoing_packets() == []
    assert algorithm.get_next_hop("B") is None

    algorithm.handle_neighbor_up("B")
    assert algorithm.get_next_hop("B") == "B"
    algorithm.handle_neighbor_down("B")
    assert algorithm.get_next_hop("B") is None


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
        [
            sys.executable,
            "-m",
            "node.main",
            "--config",
            str(config_path),
            "--mode",
            "flooding",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Flooding desde A" in result.stdout
    assert "vecinos configurados: B, C" in result.stdout
    assert "HELLO pendientes: 2" in result.stdout
