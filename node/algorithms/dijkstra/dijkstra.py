"""
Fase 1 (Dijkstra)

Implementación del algoritmo de caminos más cortos. Debe poder usarse:
1. De forma standalone (modo "dijkstra" del nodo, topología estática)
2. Desde LSR (HDB la llamará una vez tenga la topología derivada de los LSPs)

Por eso NO debe depender de sockets ni de nada de node/network: recibe una
Topology y un nodo origen, y regresa la tabla de ruteo. Debe ser un módulo
puro y fácil de testear con pytest.

TODO:
- [ ] shortest_paths(topology: Topology, source: str) -> dict[nodo, (costo, siguiente_salto)]
- [ ] build_routing_table(topology: Topology, source: str) -> dict listo para
      que node/routing/routing_table.py lo use directamente
- [ ] Manejo de nodos inalcanzables (costo infinito)
- [ ] Recalcular cuando la topología cambia (recibe una nueva Topology)
"""

from node.algorithms.dijkstra.topology import Topology


def shortest_paths(topology: Topology, source: str) -> dict:
    """Regresa {nodo_destino: (costo_total, siguiente_salto)} desde 'source'."""
    raise NotImplementedError


def build_routing_table(topology: Topology, source: str) -> dict:
    raise NotImplementedError
