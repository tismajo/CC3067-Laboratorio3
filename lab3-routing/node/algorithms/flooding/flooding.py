"""
DUEÑO: LDM (Leonardo Dufrey Mejía) - Fase 2 (Flooding)

should_forward / get_forward_targets / decrement_ttl deben ser funciones
puras (reciben/regresan dicts) para que HDB las reutilice dentro de LSR sin
tocarlas, y para poder testearlas con pytest sin sockets reales.

FloodingRoutingAlgorithm es la clase que implementa shared.interfaces.
RoutingAlgorithm para cuando --mode flooding.

TODO (LDM):
- [ ] Trackear IDs de paquetes ya vistos (usar headers -> msg_id, ver protocol_schema.json)
- [ ] should_forward(packet: dict, seen_packet_ids: set) -> bool (TTL + duplicados)
- [ ] get_forward_targets(packet, neighbor_table, received_from) -> lista de vecinos
- [ ] Completar los métodos de FloodingRoutingAlgorithm
"""

from shared.interfaces import RoutingAlgorithm
from shared import protocol
from node.algorithms.flooding.neighbor_discovery import NeighborTable


def should_forward(packet: dict, seen_packet_ids: set) -> bool:
    raise NotImplementedError


def get_forward_targets(packet: dict, neighbor_table: NeighborTable, received_from):
    raise NotImplementedError


class FloodingRoutingAlgorithm(RoutingAlgorithm):
    """Adaptador de Flooding al contrato RoutingAlgorithm (modo standalone)."""

    def initialize(self, node_id: str, neighbors: list) -> None:
        raise NotImplementedError

    def handle_info_packet(self, packet: dict) -> None:
        raise NotImplementedError

    def handle_neighbor_up(self, node_id: str) -> None:
        raise NotImplementedError

    def handle_neighbor_down(self, node_id: str) -> None:
        raise NotImplementedError

    def get_next_hop(self, destination: str):
        raise NotImplementedError

    def get_outgoing_packets(self) -> list:
        raise NotImplementedError
