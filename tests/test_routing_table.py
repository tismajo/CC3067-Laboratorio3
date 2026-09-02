from node.routing.routing_table import RoutingTable


def test_empty_table_has_no_routes():
    table = RoutingTable()
    assert table.get_next_hop("B") is None
    assert table.snapshot() == {}


def test_update_replaces_table():
    table = RoutingTable()
    table.update({"B": "B", "C": "B"})
    assert table.get_next_hop("B") == "B"
    assert table.get_next_hop("C") == "B"

    table.update({"B": "C"})
    assert table.get_next_hop("B") == "C"
    assert table.get_next_hop("C") is None


def test_snapshot_is_a_copy():
    table = RoutingTable()
    table.update({"B": "B"})

    snapshot = table.snapshot()
    snapshot["B"] = "tampered"

    assert table.get_next_hop("B") == "B"
