from shared import constants as c
from shared.interfaces import RoutingAlgorithm
from shared.protocol import build_packet, serialize

from node.network.forwarding import Forwarder
from node.network.socket_manager import NeighborUnreachableError
from node.routing.routing_table import RoutingTable


class FakeSocketManager:
    def __init__(self, unreachable=False):
        self.sent = []
        self._unreachable = unreachable

    def send(self, to_ip, to_port, packet):
        if self._unreachable:
            raise NeighborUnreachableError(to_ip, to_port, OSError("connection refused"))
        self.sent.append((to_ip, to_port, packet))


class DummyAlgorithm(RoutingAlgorithm):
    """Implementa la interfaz sin depender de Dijkstra/Flooding reales."""

    def __init__(self, next_hops=None, routing_table=None):
        self._next_hops = dict(next_hops or {})
        if routing_table is not None:
            self.routing_table = dict(routing_table)
        self.outgoing = []
        self.handled_info = []
        self.neighbors_up = []
        self.neighbors_down = []

    def initialize(self, node_id, neighbors):
        pass

    def handle_info_packet(self, packet):
        self.handled_info.append(packet)

    def handle_neighbor_up(self, node_id):
        self.neighbors_up.append(node_id)

    def handle_neighbor_down(self, node_id):
        self.neighbors_down.append(node_id)

    def get_next_hop(self, destination):
        return self._next_hops.get(destination)

    def get_outgoing_packets(self):
        pending = self.outgoing
        self.outgoing = []
        return pending


NEIGHBOR_ADDRESSES = {
    "B": {"ip": "127.0.0.1", "port": 5001},
    "C": {"ip": "127.0.0.1", "port": 5003},
}


def make_forwarder(algorithm, routing_table=None, socket_manager=None):
    return Forwarder(
        node_id="A",
        proto="dijkstra",
        algorithm=algorithm,
        routing_table=routing_table or RoutingTable(),
        socket_manager=socket_manager or FakeSocketManager(),
        neighbor_addresses=NEIGHBOR_ADDRESSES,
    )


def test_message_addressed_to_self_is_not_forwarded(capsys):
    socket_manager = FakeSocketManager()
    forwarder = make_forwarder(DummyAlgorithm(), socket_manager=socket_manager)

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_MESSAGE, from_="B", to="A", payload="hola"
    )
    forwarder.forward_data_packet(packet)

    assert socket_manager.sent == []
    assert "hola" in capsys.readouterr().out


def test_message_dropped_when_ttl_exhausted():
    socket_manager = FakeSocketManager()
    routing_table = RoutingTable()
    routing_table.update({"C": "B"})
    forwarder = make_forwarder(
        DummyAlgorithm(), routing_table=routing_table, socket_manager=socket_manager
    )

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_MESSAGE, from_="B", to="C", ttl=1, payload="x"
    )
    forwarder.forward_data_packet(packet)

    assert socket_manager.sent == []


def test_message_dropped_when_no_route_known():
    socket_manager = FakeSocketManager()
    forwarder = make_forwarder(DummyAlgorithm(), socket_manager=socket_manager)

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_MESSAGE, from_="B", to="Z", payload="x"
    )
    forwarder.forward_data_packet(packet)

    assert socket_manager.sent == []


def test_message_forwarded_to_next_hop_with_decremented_ttl():
    socket_manager = FakeSocketManager()
    routing_table = RoutingTable()
    routing_table.update({"C": "B"})
    forwarder = make_forwarder(
        DummyAlgorithm(), routing_table=routing_table, socket_manager=socket_manager
    )

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_MESSAGE, from_="A", to="C", ttl=5, payload="x"
    )
    forwarder.forward_data_packet(packet)

    assert len(socket_manager.sent) == 1
    to_ip, to_port, forwarded = socket_manager.sent[0]
    assert (to_ip, to_port) == ("127.0.0.1", 5001)
    assert forwarded[c.FIELD_TTL] == 4
    assert forwarded[c.FIELD_TO] == "C"


def test_data_packet_is_flooded_when_algorithm_exposes_flood():
    socket_manager = FakeSocketManager()
    algorithm = DummyAlgorithm()
    algorithm.flood = lambda packet, received_from: [
        ({"node_id": "B"}, dict(packet, ttl=packet[c.FIELD_TTL] - 1)),
        ({"node_id": "C"}, dict(packet, ttl=packet[c.FIELD_TTL] - 1)),
    ]
    forwarder = make_forwarder(algorithm, socket_manager=socket_manager)

    packet = build_packet(
        proto="flooding", type_=c.TYPE_MESSAGE, from_="X", to="Z", ttl=5, payload="x"
    )
    forwarder.forward_data_packet(packet)

    assert [entry[0] for entry in socket_manager.sent] == ["127.0.0.1", "127.0.0.1"]
    assert all(sent[2][c.FIELD_TTL] == 4 for sent in socket_manager.sent)
    assert {sent[1] for sent in socket_manager.sent} == {5001, 5003}


def test_send_to_unreachable_neighbor_does_not_raise():
    routing_table = RoutingTable()
    routing_table.update({"C": "B"})
    forwarder = make_forwarder(
        DummyAlgorithm(),
        routing_table=routing_table,
        socket_manager=FakeSocketManager(unreachable=True),
    )

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_MESSAGE, from_="A", to="C", ttl=5, payload="x"
    )
    forwarder.forward_data_packet(packet)  # no debe propagar NeighborUnreachableError


def test_send_message_originates_packet_from_self():
    socket_manager = FakeSocketManager()
    routing_table = RoutingTable()
    routing_table.update({"B": "B"})
    forwarder = make_forwarder(
        DummyAlgorithm(),
        routing_table=routing_table,
        socket_manager=socket_manager,
    )

    forwarder.send_message("B", "hola vecino")

    assert len(socket_manager.sent) == 1
    _, _, packet = socket_manager.sent[0]
    assert packet[c.FIELD_FROM] == "A"
    assert packet[c.FIELD_TO] == "B"
    assert packet[c.FIELD_PAYLOAD] == "hola vecino"


def test_info_packet_delegates_to_algorithm_and_flushes_outgoing():
    socket_manager = FakeSocketManager()
    algorithm = DummyAlgorithm()
    forwarder = make_forwarder(algorithm, socket_manager=socket_manager)

    reply = build_packet(
        proto="lsr", type_=c.TYPE_INFO, from_="A", to="B", payload={"seq": 1}
    )
    algorithm.outgoing = [reply]

    incoming = build_packet(
        proto="lsr", type_=c.TYPE_INFO, from_="C", to="A", payload={"seq": 1}
    )
    forwarder.forward_info_packet(incoming)

    assert algorithm.handled_info == [incoming]
    assert socket_manager.sent == [("127.0.0.1", 5001, reply)]


def test_hello_packet_uses_algorithm_hook_when_no_dedicated_handler():
    socket_manager = FakeSocketManager()
    algorithm = DummyAlgorithm()
    forwarder = make_forwarder(algorithm, socket_manager=socket_manager)

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_HELLO, from_="B", to="A", payload=None
    )
    forwarder.handle_hello_packet(packet)

    assert algorithm.neighbors_up == ["B"]


def test_handle_incoming_packet_dispatches_by_type():
    socket_manager = FakeSocketManager()
    algorithm = DummyAlgorithm(next_hops={"B": "B"})
    forwarder = make_forwarder(algorithm, socket_manager=socket_manager)

    packet = build_packet(
        proto="dijkstra", type_=c.TYPE_HELLO, from_="B", to="A", payload=None
    )
    forwarder.handle_incoming_packet(serialize(packet))

    assert algorithm.neighbors_up == ["B"]


def test_sync_routing_table_uses_algorithm_attribute_when_available():
    algorithm = DummyAlgorithm(
        next_hops={"B": "B", "D": "B"},
        routing_table={"B": "B", "D": "B"},
    )
    routing_table = RoutingTable()
    forwarder = make_forwarder(algorithm, routing_table=routing_table)

    incoming = build_packet(
        proto="dijkstra", type_=c.TYPE_HELLO, from_="B", to="A", payload=None
    )
    forwarder.handle_hello_packet(incoming)

    assert routing_table.snapshot() == {"B": "B", "D": "B"}


def test_sync_routing_table_falls_back_to_neighbor_addresses():
    algorithm = DummyAlgorithm(next_hops={"B": "B", "C": "C"})
    routing_table = RoutingTable()
    forwarder = make_forwarder(algorithm, routing_table=routing_table)

    incoming = build_packet(
        proto="dijkstra", type_=c.TYPE_HELLO, from_="B", to="A", payload=None
    )
    forwarder.handle_hello_packet(incoming)

    assert routing_table.snapshot() == {"B": "B", "C": "C"}
