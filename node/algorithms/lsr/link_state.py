"""
DUEÑO: HDB (Hugo Daniel Barillas) - Fase 4 (Link State Routing)
DEPENDE DE: Dijkstra (MJ) y Flooding (LDM), ya terminados antes de empezar esta fase

Orquesta el algoritmo completo de LSR:
1. Cada nodo genera su propio LSP (lsp.py) con sus vecinos directos.
2. Distribuye su LSP a toda la red usando el módulo de Flooding de LDM
   (node/algorithms/flooding/flooding.py) SIN modificar ese archivo.
3. Recolecta los LSPs de los demás nodos y arma la topología completa
   (usa node/algorithms/dijkstra/topology.py de MJ para representarla,
   SIN modificar ese archivo).
4. Corre Dijkstra (node/algorithms/dijkstra/dijkstra.py de MJ) sobre esa
   topología derivada para obtener la tabla de ruteo del nodo.
5. Si llega un LSP más nuevo (nodo caído, nuevo enlace, cambio de peso),
   reconstruye la topología y vuelve a correr Dijkstra.

TODO (HDB):
- [ ] Clase LinkStateRouter(node_id, neighbors)
- [ ] Método on_lsp_received(lsp: dict) -> actualiza la topología derivada
      y dispara recomputo si el LSP es más nuevo (lsp.is_newer)
- [ ] Método build_topology_from_lsps() -> Topology (de MJ)
- [ ] Método recompute_routing_table() -> usa dijkstra.build_routing_table
- [ ] Método broadcast_own_lsp() -> arma su LSP y lo envía por flooding
"""

class LinkStateRouter:
    def __init__(self, node_id: str, neighbors: list):
        raise NotImplementedError

    def on_lsp_received(self, lsp: dict):
        raise NotImplementedError

    def build_topology_from_lsps(self):
        raise NotImplementedError

    def recompute_routing_table(self):
        raise NotImplementedError

    def broadcast_own_lsp(self):
        raise NotImplementedError
