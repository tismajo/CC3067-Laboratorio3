"""
DUEÑO: MJ (María José Girón) - Fase 1 (Dijkstra)

TODO (MJ):
- [ ] Clase Topology con nodos y aristas (peso)
- [ ] Método from_json(data: dict) -> Topology
- [ ] Método add_edge(node_a, node_b, weight)
- [ ] Método get_neighbors(node) -> lista de (vecino, peso)
- [ ] Método mark_down(node) (para pruebas de caída de nodos)
"""

class Topology:
    def __init__(self):
        raise NotImplementedError

    @classmethod
    def from_json(cls, data: dict):
        raise NotImplementedError

    def add_edge(self, node_a: str, node_b: str, weight: float):
        raise NotImplementedError

    def get_neighbors(self, node: str):
        raise NotImplementedError

    def mark_down(self, node: str):
        raise NotImplementedError
