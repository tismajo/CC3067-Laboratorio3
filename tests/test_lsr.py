"""Fase 4: pruebas unitarias de node/algorithms/lsr/*"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]

from node.algorithms.lsr.link_state import LinkStateRouter
from node.algorithms.lsr.lsp import build_lsp, is_newer, parse_lsp
from shared import constants as c
from shared.protocol import build_packet


def make_router(node_id="A", neighbors=None):
    neighbors = neighbors or [
        {"node_id": "B", "ip": "127.0.0.1", "port": 5001, "weight": 7},
        {"node_id": "I", "ip": "127.0.0.1", "port": 5002, "weight": 1},
    ]
    router = LinkStateRouter(self_info={"node_id": node_id, "ip": "127.0.0.1", "port": 5000})
    router.initialize(node_id, neighbors)
    router.get_outgoing_packets()
    return router


def lsp_packet(origin, sequence, links, from_=None):
    payload = build_lsp(origin, sequence, links)
    return build_packet(
        proto=c.PROTO_LSR,
        type_=c.TYPE_INFO,
        from_=from_ or origin,
        to="A",
        headers=[{"packet_id": f"{origin}-{sequence}"}],
        payload=payload,
    )


def test_build_and_parse_lsp():
    lsp = build_lsp(
        "A",
        2,
        [
            {"node_id": "B", "ip": "127.0.0.1", "port": 5001, "weight": 7},
            {"node_id": "I", "weight": 1},
        ],
    )

    assert lsp == {
        "node_id": "A",
        "sequence": 2,
        "neighbors": [
            {"node_id": "B", "weight": 7},
            {"node_id": "I", "weight": 1},
        ],
    }
    assert parse_lsp(lsp) == lsp


def test_parse_lsp_rejects_malformed_payload():
    with pytest.raises(ValueError):
        parse_lsp({"node_id": "A", "sequence": 1})
    with pytest.raises(ValueError):
        parse_lsp("no soy un dict")


def test_is_newer_by_sequence():
    old = {"node_id": "A", "sequence": 1, "neighbors": []}
    new = {"node_id": "A", "sequence": 2, "neighbors": []}

    assert is_newer(None, old) is True
    assert is_newer(old, new) is True
    assert is_newer(new, old) is False
    assert is_newer(new, new) is False


def test_initial_routing_table_covers_direct_neighbors():
    router = make_router()

    assert router.routing_table == {"B": "B", "I": "I"}
    assert router.get_next_hop("B") == "B"


def test_topology_rebuilt_on_new_lsp():
    router = make_router()

    router.handle_info_packet(
        lsp_packet("B", 1, [{"node_id": "A", "weight": 7}, {"node_id": "C", "weight": 2}])
    )

    topology = router.build_topology_from_lsps()
    assert topology.nodes == {"A", "B", "C", "I"}
    assert ("C", 2) in topology.get_neighbors("B")


def test_routing_table_recomputed_after_topology_change():
    router = make_router()
    assert "C" not in router.routing_table

    router.handle_info_packet(
        lsp_packet("B", 1, [{"node_id": "A", "weight": 7}, {"node_id": "C", "weight": 2}])
    )

    assert router.routing_table["C"] == "B"


def test_stale_lsp_is_ignored():
    router = make_router()
    router.handle_info_packet(lsp_packet("B", 5, [{"node_id": "C", "weight": 2}]))
    router.handle_info_packet(lsp_packet("B", 2, [{"node_id": "C", "weight": 99}]))

    assert router.lsp_db["B"]["sequence"] == 5


def test_reflood_excludes_sender_and_skips_duplicates():
    router = make_router()
    packet = lsp_packet(
        "B", 1, [{"node_id": "C", "weight": 2}], from_="B"
    )

    router.handle_info_packet(packet)
    targets = [p[c.FIELD_TO] for p in router.get_outgoing_packets()]
    assert targets == ["I"]

    router.handle_info_packet(packet)
    assert router.get_outgoing_packets() == []


def test_neighbor_down_readvertises_and_reroutes():
    router = make_router()
    router.handle_info_packet(
        lsp_packet("I", 1, [{"node_id": "A", "weight": 1}, {"node_id": "C", "weight": 1}])
    )
    router.handle_info_packet(
        lsp_packet("B", 1, [{"node_id": "A", "weight": 7}, {"node_id": "C", "weight": 1}])
    )
    assert router.routing_table["C"] == "I"

    router.get_outgoing_packets()
    router.handle_neighbor_down("I")

    own_lsp = router.lsp_db["A"]
    assert [link["node_id"] for link in own_lsp["neighbors"]] == ["B"]
    assert router.routing_table["C"] == "B"
    assert any(p[c.FIELD_TYPE] == c.TYPE_INFO for p in router.get_outgoing_packets())


def test_standalone_lsr_mode(tmp_path):
    config_path = tmp_path / "topology.json"
    config_path.write_text(
        json.dumps(
            {
                "node_id": "A",
                "ip": "127.0.0.1",
                "port": 5000,
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
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "LSP de A (seq 1)" in result.stdout
    assert "Rutas desde A" in result.stdout
    assert "B\tB" in result.stdout
    assert "I\tI" in result.stdout
