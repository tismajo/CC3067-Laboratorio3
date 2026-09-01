"""
DUEÑO: MJ (María José Girón) - Fase 1 (Dijkstra)

Modelo de la topología completa (nodos y aristas con peso) que Dijkstra
necesita para funcionar. A diferencia de Flooding, Dijkstra sí requiere
conocer la topología completa, no solo los vecinos directos.

TODO (MJ):
- [ ] Clase Topology con nodos y aristas (peso)
- [ ] Método from_json(data: dict) -> Topology (carga desde config o desde
      la info recibida, si se usa dentro de LSR)
- [ ] Método add_edge(node_a, node_b, weight)
- [ ] Método get_neighbors(node) -> lista de (vecino, peso)
- [ ] Método remove_node / mark_down(node) (para pruebas de caída de nodos)
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
