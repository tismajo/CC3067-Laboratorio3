class Topology:
    def __init__(self):
        self._adjacency = {}

    @property
    def nodes(self) -> set:
        return set(self._adjacency)

    @classmethod
    def from_json(cls, data: dict):
        topology_data = data.get("topology", data)
        topology = cls()

        for node in topology_data["nodes"]:
            topology._adjacency[node] = {}

        for edge in topology_data["edges"]:
            topology.add_edge(
                edge["node_a"],
                edge["node_b"],
                edge["weight"],
            )

        return topology

    def add_edge(self, node_a: str, node_b: str, weight: float):
        if weight < 0:
            raise ValueError("Dijkstra no admite pesos negativos")

        self._adjacency.setdefault(node_a, {})[node_b] = weight
        self._adjacency.setdefault(node_b, {})[node_a] = weight

    def get_neighbors(self, node: str):
        return list(self._adjacency.get(node, {}).items())

    def mark_down(self, node: str):
        self._adjacency.pop(node, None)
        for neighbors in self._adjacency.values():
            neighbors.pop(node, None)
