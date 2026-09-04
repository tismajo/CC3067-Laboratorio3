"""Protocolo Unificado: checksum, validación y reenvío (ver PROTOCOLO.md)."""

import pytest

from shared.protocol import (
    build_message,
    compute_checksum,
    decrement_ttl,
    get_header,
    normalize_addr,
    parse_message,
    prepare_forward,
    serialize,
)


def test_checksum_test_vectors():
    assert compute_checksum("hola G") == "0bded535"
    assert compute_checksum(
        {"origin": "10.0.0.1:5000", "seq": 7,
         "neighbors": [{"id": "10.0.0.2:5000", "weight": 4.8}]}
    ) == "cbd08356"


def test_normalize_addr_completes_default_port():
    assert normalize_addr("10.0.0.7", 5000) == "10.0.0.7:5000"
    assert normalize_addr("10.0.0.7:5001", 5000) == "10.0.0.7:5001"
    assert normalize_addr("*", 5000) == "*"


def test_build_and_parse_roundtrip():
    msg = build_message("lsr", "message", "10.0.0.1:5000", "10.0.0.2:5000", "hola")
    assert parse_message(serialize(msg)) == msg


def test_parse_rejects_structural_errors():
    assert parse_message(b"no json") is None
    assert parse_message(b'{"proto":"lsr"}') is None  # faltan campos
    bad = build_message("lsr", "message", "a:1", "b:2", "x")
    bad["ttl"] = 0
    assert parse_message(serialize(bad)) is None


def test_bad_checksum_and_version_are_logged_not_discarded(caplog):
    msg = build_message("lsr", "message", "a:1", "b:2", "hola")
    msg["headers"] = [
        h if "checksum" not in h else {"checksum": "deadbeef"} for h in msg["headers"]
    ]
    msg["version"] = 9
    with caplog.at_level("WARNING"):
        parsed = parse_message(serialize(msg))
    assert parsed is not None
    assert "checksum" in caplog.text and "version" in caplog.text


def test_decrement_ttl_discards_at_zero():
    assert decrement_ttl({"ttl": 1, "from": "a", "to": "b"}) is None
    assert decrement_ttl({"ttl": 2})["ttl"] == 1


def test_prepare_forward_sets_via_and_trace_for_messages():
    msg = build_message("lsr", "message", "a:1", "d:1", "x", ttl=5)
    fwd = prepare_forward(msg, "b:1")
    assert fwd["ttl"] == 4
    assert fwd["from"] == "a:1"  # el originador no cambia
    assert get_header(fwd, "via") == "b:1"
    assert get_header(fwd, "trace") == ["b:1"]
