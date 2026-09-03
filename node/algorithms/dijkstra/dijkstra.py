import heapq
import math

from node.algorithms.dijkstra.topology import Topology
from shared.interfaces import RoutingAlgorithm


def shortest_paths(topology: Topology, source: str) -> dict:
    if source not in topology.nodes:
        raise ValueError(f"El nodo de origen no existe: {source}")

    distances = {node: math.inf for node in topology.nodes}
    next_hops = {node: None for node in topology.nodes}
    distances[source] = 0
    pending = [(0, source)]

    while pending:
        current_distance, current = heapq.heappop(pending)
        if current_distance > distances[current]:
            continue

        for neighbor, weight in topology.get_neighbors(current):
            candidate = current_distance + weight
            if candidate >= distances[neighbor]:
                continue

            distances[neighbor] = candidate
            next_hops[neighbor] = (
                neighbor if current == source else next_hops[current]
            )
            heapq.heappush(pending, (candidate, neighbor))

    return {
        node: (distances[node], next_hops[node])
        for node in topology.nodes
    }


def build_routing_table(topology: Topology, source: str) -> dict:
    paths = shortest_paths(topology, source)
    return {
        destination: next_hop
        for destination, (cost, next_hop) in paths.items()
        if destination != source and cost < math.inf
    }


def _edges_of(topology: Topology) -> list:
    """Lista de aristas ``(a, b, peso)`` sin duplicar el sentido inverso."""

    seen = set()
    edges = []
    for node in topology.nodes:
        for neighbor, weight in topology.get_neighbors(node):
            key = frozenset((node, neighbor))
            if key not in seen:
                seen.add(key)
                edges.append((node, neighbor, weight))
    return edges


class DijkstraRoutingAlgorithm(RoutingAlgorithm):
    def __init__(self, topology: Topology = None):
        self.topology = topology
        self.node_id = None
        self.paths = {}
        self.routing_table = {}
        self._base_edges = None
        self._down_nodes = set()

    def initialize(self, node_id: str, neighbors: list) -> None:
        self.node_id = node_id
        if self.topology is not None:
            self._base_edges = _edges_of(self.topology)
        else:
            self._base_edges = [
                (node_id, neighbor["node_id"], neighbor["weight"])
                for neighbor in neighbors
            ]
        self._down_nodes = set()
        self._rebuild()

    def handle_info_packet(self, packet: dict) -> None:
        pass

    def handle_neighbor_up(self, node_id: str) -> None:
        if node_id in self._down_nodes:
            self._down_nodes.discard(node_id)
            self._rebuild()

    def handle_neighbor_down(self, node_id: str) -> None:
        self._down_nodes.add(node_id)
        self._rebuild()

    def get_next_hop(self, destination: str):
        return self.routing_table.get(destination)

    def get_outgoing_packets(self) -> list:
        return []

    def _rebuild(self) -> None:
        """Reconstruye la topología desde las aristas base, sin los nodos caídos.

        No se muta destructivamente: así un vecino que vuelve
        (``handle_neighbor_up``) reaparece con todos sus enlaces.
        """

        topology = Topology()
        for node_a, node_b, weight in self._base_edges:
            if node_a in self._down_nodes or node_b in self._down_nodes:
                continue
            topology.add_edge(node_a, node_b, weight)
        self.topology = topology
        self._recompute()

    def _recompute(self) -> None:
        if self.node_id not in self.topology.nodes:
            self.paths = {}
            self.routing_table = {}
            return
        self.paths = shortest_paths(self.topology, self.node_id)
        self.routing_table = build_routing_table(
            self.topology,
            self.node_id,
        )
