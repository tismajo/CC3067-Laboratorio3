"""
Fase 4 (Link State Routing)
DEPENDE DE: Fase Dijkstra y Flooding, ya terminados antes de empezar esta fase

Orquesta el algoritmo completo de LSR:
1. Cada nodo genera su propio LSP (lsp.py) con sus vecinos directos.
2. Distribuye su LSP a toda la red usando el módulo de Flooding
   (node/algorithms/flooding/flooding.py) SIN modificar ese archivo.
3. Recolecta los LSPs de los demás nodos y arma la topología completa
   (usa node/algorithms/dijkstra/topology.py para representarla,
   SIN modificar ese archivo).
4. Corre Dijkstra (node/algorithms/dijkstra/dijkstra.py) sobre esa
   topología derivada para obtener la tabla de ruteo del nodo.
5. Si llega un LSP más nuevo (nodo caído, nuevo enlace, cambio de peso),
   reconstruye la topología y vuelve a correr Dijkstra.
"""

from __future__ import annotations

import threading

from node.algorithms.flooding.flooding import (
    decrement_ttl,
    get_forward_targets,
    should_forward,
)
from node.algorithms.flooding.neighbor_discovery import NeighborTable
from node.algorithms.dijkstra.dijkstra import build_routing_table
from node.algorithms.dijkstra.topology import Topology
from node.algorithms.lsr.lsp import build_lsp, is_newer, parse_lsp
from shared import constants as c
from shared.interfaces import RoutingAlgorithm
from shared.protocol import build_packet


class LinkStateRouter(RoutingAlgorithm):
    """Adaptador de Link State Routing para el contrato común de enrutamiento."""

    def __init__(
        self,
        neighbor_timeout: float = 15.0,
        self_info: dict | None = None,
    ):
        self.node_id: str | None = None
        self.self_info: dict = dict(self_info or {})
        self.neighbor_table = NeighborTable(timeout=neighbor_timeout)
        self.sequence = 0
        self.lsp_db: dict[str, dict] = {}
        self.seen_packet_ids: set[str] = set()
        self.routing_table: dict[str, str] = {}
        self._outgoing: list[dict] = []
        self._lock = threading.RLock()

    # -- ciclo de vida -------------------------------------------------------

    def initialize(self, node_id: str, neighbors: list) -> None:
        self.node_id = node_id
        self.self_info["node_id"] = node_id
        self.neighbor_table = NeighborTable(
            neighbors,
            timeout=self.neighbor_table.timeout,
        )
        # ponytail: al arrancar se anuncian todos los enlaces configurados como
        # activos; la realidad la corrige el primer HELLO / health check.
        for neighbor in neighbors:
            self.neighbor_table.mark_up(neighbor["node_id"])

        with self._lock:
            self.seen_packet_ids.clear()
            self._outgoing = self.neighbor_table.build_hello_packets(self.self_info)
        self.broadcast_own_lsp()

    # -- generación y difusión de LSPs ------------------------------------------

    def broadcast_own_lsp(self) -> None:
        """Arma el LSP propio con los vecinos activos y lo encola por flooding."""

        with self._lock:
            self.sequence += 1
            lsp = build_lsp(
                self.node_id,
                self.sequence,
                self.neighbor_table.get_active_neighbors(),
            )
            self.lsp_db[self.node_id] = lsp
            self.recompute_routing_table()

            packet_id = f"{self.node_id}-{self.sequence}"
            self.seen_packet_ids.add(packet_id)
            for neighbor in self.neighbor_table.get_active_neighbors():
                self._outgoing.append(
                    build_packet(
                        proto=c.PROTO_LSR,
                        type_=c.TYPE_INFO,
                        from_=self.node_id,
                        to=neighbor["node_id"],
                        headers=[{"packet_id": packet_id}],
                        payload=lsp,
                    )
                )

    def handle_info_packet(self, packet: dict) -> None:
        """Procesa un LSP recibido y lo reenvía al resto de la red."""

        lsp = parse_lsp(packet.get(c.FIELD_PAYLOAD))
        self.on_lsp_received(lsp)

        with self._lock:
            if not should_forward(packet, self.seen_packet_ids):
                return
            targets = get_forward_targets(
                packet,
                self.neighbor_table,
                packet.get(c.FIELD_FROM),
            )
            forwarded = decrement_ttl(packet)
            for target in targets:
                copy = dict(forwarded)
                copy[c.FIELD_FROM] = self.node_id
                copy[c.FIELD_TO] = target["node_id"]
                self._outgoing.append(copy)

    def on_lsp_received(self, lsp: dict) -> bool:
        """Guarda el LSP si es más nuevo y recalcula. Devuelve si hubo cambio."""

        with self._lock:
            if not is_newer(self.lsp_db.get(lsp["node_id"]), lsp):
                return False
            self.lsp_db[lsp["node_id"]] = lsp
            self.recompute_routing_table()
            return True

    # -- topología derivada y tabla de ruteo ---------------------------------

    def build_topology_from_lsps(self) -> Topology:
        """Arma una Topology con todos los enlaces conocidos por los LSPs."""

        topology = Topology()
        for lsp in self.lsp_db.values():
            for link in lsp["neighbors"]:
                topology.add_edge(lsp["node_id"], link["node_id"], link["weight"])
        return topology

    def recompute_routing_table(self) -> None:
        """Corre Dijkstra sobre la topología derivada de los LSPs."""

        topology = self.build_topology_from_lsps()
        if self.node_id in topology.nodes:
            self.routing_table = build_routing_table(topology, self.node_id)
        else:
            self.routing_table = {}

    # -- eventos de vecinos -------------------------------------------------

    def handle_hello_packet(self, packet: dict) -> dict:
        return self.neighbor_table.on_hello_received(packet)

    def handle_neighbor_up(self, node_id: str) -> None:
        self.neighbor_table.mark_up(node_id)

    def handle_neighbor_down(self, node_id: str) -> None:
        self.neighbor_table.mark_down(node_id)

    # -- consultas de forwarding ------------------------------------------

    def get_next_hop(self, destination: str):
        with self._lock:
            return self.routing_table.get(destination)

    def get_outgoing_packets(self) -> list[dict]:
        with self._lock:
            packets = list(self._outgoing)
            self._outgoing.clear()
            return packets
