"""Fase 4: pruebas unitarias de node/algorithms/lsr/*"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]

from node.algorithms.lsr.link_state import LinkStateRouter
from node.algorithms.lsr.lsp import build_lsp, is_newer, parse_lsp
from shared import constants as c
from shared.protocol import build_message

A = "127.0.0.1:5000"
B = "127.0.0.1:5001"
I = "127.0.0.1:5002"
CN = "127.0.0.1:5003"


def make_router(node_id=A, neighbors=None):
    neighbors = neighbors or [
        {"node_id": B, "ip": "127.0.0.1", "port": 5001, "weight": 7},
        {"node_id": I, "ip": "127.0.0.1", "port": 5002, "weight": 1},
    ]
    router = LinkStateRouter(
        self_info={"node_id": node_id, "ip": "127.0.0.1", "port": 5000, "proto": "lsr"}
    )
    router.initialize(node_id, neighbors)
    router.get_outgoing_packets()
    return router


def lsp_packet(origin, seq, links, from_=None, via=None):
    payload = build_lsp(origin, seq, links)
    headers = [{c.HEADER_VIA: via}] if via else None
    return build_message(
        proto=c.PROTO_LSR, type_=c.TYPE_INFO,
        src=from_ or origin, dst=c.BROADCAST_TO, headers=headers, payload=payload,
    )


def test_build_and_parse_lsp():
    lsp = build_lsp(A, 2, [{"id": B, "weight": 7}, {"node_id": I, "weight": 1}])
    assert lsp == {
        "origin": A, "seq": 2, "age_s": 0,
        "neighbors": [{"id": B, "weight": 7}, {"id": I, "weight": 1}],
    }
    assert parse_lsp(lsp) == lsp


def test_parse_lsp_accepts_foreign_variants():
    got = parse_lsp({"node_id": A, "sequence": 3, "links": {B: 4, I: 1}})
    assert got["origin"] == A and got["seq"] == 3
    assert sorted(got["neighbors"], key=lambda n: n["id"]) == [
        {"id": B, "weight": 4}, {"id": I, "weight": 1},
    ]
    text = json.dumps({"origin": A, "seq": 1, "neighbors": [{"node": B, "cost": 2}]})
    assert parse_lsp(text)["neighbors"] == [{"id": B, "weight": 2}]


def test_parse_lsp_rejects_malformed_payload():
    with pytest.raises(ValueError):
        parse_lsp({"origin": A})
    with pytest.raises(ValueError):
        parse_lsp(42)


def test_is_newer_by_seq_and_reset_detection():
    old = {"origin": A, "seq": 1, "neighbors": []}
    new = {"origin": A, "seq": 2, "neighbors": []}
    assert is_newer(None, old) is True
    assert is_newer(old, new) is True
    assert is_newer(new, old) is False
    # contador reiniciado: seq muy por debajo se acepta
    assert is_newer({"origin": A, "seq": 100, "neighbors": []}, {"origin": A, "seq": 1, "neighbors": []}) is True


def test_initial_routing_table_covers_direct_neighbors():
    router = make_router()
    assert router.routing_table == {B: B, I: I}
    assert router.get_next_hop(B) == B


def test_own_lsp_sequence_starts_at_one():
    router = make_router()
    assert router.lsp_db[A]["lsp"]["seq"] == 1


def test_topology_rebuilt_on_new_lsp():
    router = make_router()
    router.handle_info_packet(lsp_packet(B, 1, [{"id": A, "weight": 7}, {"id": CN, "weight": 2}]))

    topology = router.build_topology_from_lsps()
    assert topology.nodes == {A, B, CN, I}
    assert (CN, 2) in topology.get_neighbors(B)


def test_routing_table_recomputed_after_topology_change():
    router = make_router()
    assert CN not in router.routing_table

    router.handle_info_packet(lsp_packet(B, 1, [{"id": A, "weight": 7}, {"id": CN, "weight": 2}]))
    assert router.routing_table[CN] == B


def test_stale_lsp_is_ignored():
    router = make_router()
    router.handle_info_packet(lsp_packet(B, 5, [{"id": CN, "weight": 2}]))
    router.handle_info_packet(lsp_packet(B, 2, [{"id": CN, "weight": 99}]))
    assert router.lsp_db[B]["lsp"]["seq"] == 5


def test_reflood_excludes_sender_and_skips_duplicates():
    router = make_router()
    packet = lsp_packet("10.0.0.9:5000", 1, [{"id": "10.0.0.8:5000", "weight": 2}], from_=B, via=B)

    router.handle_info_packet(packet)
    assert [p[c.FIELD_TO] for p in router.get_outgoing_packets()] == [I]

    router.handle_info_packet(packet)
    assert router.get_outgoing_packets() == []


def test_neighbor_down_readvertises_and_reroutes():
    router = make_router()
    router.handle_info_packet(lsp_packet(I, 1, [{"id": A, "weight": 1}, {"id": CN, "weight": 1}]))
    router.handle_info_packet(lsp_packet(B, 1, [{"id": A, "weight": 7}, {"id": CN, "weight": 1}]))
    assert router.routing_table[CN] == I

    router.get_outgoing_packets()
    router.handle_neighbor_down(I)

    own_lsp = router.lsp_db[A]["lsp"]
    assert [link["id"] for link in own_lsp["neighbors"]] == [B]
    assert router.routing_table[CN] == B
    assert any(p[c.FIELD_TYPE] == c.TYPE_INFO for p in router.get_outgoing_packets())


def test_lsp_expires_after_timeout():
    router = make_router()
    router.handle_info_packet(lsp_packet(B, 1, [{"id": A, "weight": 7}, {"id": CN, "weight": 2}]))
    assert router.routing_table[CN] == B

    router.expire_lsps(now=time.time() + 31)
    assert CN not in router.routing_table


def test_standalone_lsr_mode(tmp_path):
    config_path = tmp_path / "topology.json"
    config_path.write_text(
        json.dumps(
            {
                "node_id": "A", "ip": "127.0.0.1", "port": 5000,
                "neighbors": [
                    {"node_id": "B", "ip": "127.0.0.1", "port": 5001, "weight": 7},
                    {"node_id": "I", "ip": "127.0.0.1", "port": 5002, "weight": 1},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "node.main", "--config", str(config_path), "--mode", "lsr"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )

    assert "LSP de A (seq " in result.stdout
    assert "Rutas desde A" in result.stdout
    assert "B\tB" in result.stdout
    assert "I\tI" in result.stdout
