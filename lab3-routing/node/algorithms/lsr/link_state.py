"""
DUEÑO: HDB (Hugo Daniel Barillas) - Fase 4 (Link State Routing)
DEPENDE DE: Dijkstra (MJ) y Flooding (LDM) ya terminados, y de shared.interfaces

Usa las funciones puras de MJ (node.algorithms.dijkstra.dijkstra) y de LDM
(node.algorithms.flooding.flooding) SIN modificarlas. LinkStateRouter es la
clase que implementa shared.interfaces.RoutingAlgorithm para --mode lsr.

TODO (HDB):
- [ ] on_lsp_received(lsp) -> si lsp.is_newer(...), reconstruir Topology (de MJ)
      y volver a llamar dijkstra.build_routing_table (de MJ)
- [ ] broadcast_own_lsp() -> arma su propio LSP (lsp.build_lsp) y lo agrega a
      la cola de get_outgoing_packets() para que Flooding (de LDM) lo reparta
- [ ] Completar los métodos de LinkStateRouter
"""

from shared.interfaces import RoutingAlgorithm
from shared import constants as c
from shared import protocol
from node.algorithms.dijkstra.topology import Topology
from node.algorithms.dijkstra import dijkstra
from node.algorithms.flooding import flooding
from node.algorithms.lsr import lsp


class LinkStateRouter(RoutingAlgorithm):

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
