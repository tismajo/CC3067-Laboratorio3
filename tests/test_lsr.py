"""Fase 4: pruebas unitarias de node/algorithms/lsr/*"""

import pytest

from node.algorithms.lsr.lsp import build_lsp, is_newer, parse_lsp


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
