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


class DijkstraRoutingAlgorithm(RoutingAlgorithm):
    def __init__(self, topology: Topology = None):
        self.topology = topology
        self.node_id = None
        self.paths = {}
        self.routing_table = {}

    def initialize(self, node_id: str, neighbors: list) -> None:
        self.node_id = node_id
        if self.topology is None:
            self.topology = Topology()
            for neighbor in neighbors:
                self.topology.add_edge(
                    node_id,
                    neighbor["node_id"],
                    neighbor["weight"],
                )
        self._recompute()

    def handle_info_packet(self, packet: dict) -> None:
        pass

    def handle_neighbor_up(self, node_id: str) -> None:
        pass

    def handle_neighbor_down(self, node_id: str) -> None:
        self.topology.mark_down(node_id)
        self._recompute()

    def get_next_hop(self, destination: str):
        return self.routing_table.get(destination)

    def get_outgoing_packets(self) -> list:
        return []

    def _recompute(self) -> None:
        self.paths = shortest_paths(self.topology, self.node_id)
        self.routing_table = build_routing_table(
            self.topology,
            self.node_id,
        )
