"""
DUEÑO: MJ (María José Girón) - Fase 1 (Dijkstra)

shortest_paths / build_routing_table deben ser funciones puras (sin sockets,
sin threads) para poder testearlas con pytest y para que HDB las reutilice
dentro de LSR sin tocarlas.

DijkstraRoutingAlgorithm es la clase que implementa shared.interfaces.
RoutingAlgorithm: es el "adaptador" que node/main.py (de EA) instancia
cuando --mode dijkstra. Aquí sí puede depender de shared.protocol /
shared.constants para armar sus paquetes de "info" (la topología estática
que Dijkstra necesita).

TODO (MJ):
- [ ] shortest_paths(topology: Topology, source: str) -> dict[nodo, (costo, siguiente_salto)]
- [ ] build_routing_table(topology: Topology, source: str) -> dict
- [ ] Completar los métodos de DijkstraRoutingAlgorithm (usa las 2 funciones de arriba)
"""

from shared.interfaces import RoutingAlgorithm
from node.algorithms.dijkstra.topology import Topology


def shortest_paths(topology: Topology, source: str) -> dict:
    raise NotImplementedError


def build_routing_table(topology: Topology, source: str) -> dict:
    raise NotImplementedError


class DijkstraRoutingAlgorithm(RoutingAlgorithm):
    """Adaptador de Dijkstra al contrato RoutingAlgorithm (modo standalone)."""

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
