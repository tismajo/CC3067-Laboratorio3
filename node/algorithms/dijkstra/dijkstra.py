import heapq
import math

from node.algorithms.dijkstra.topology import Topology


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
