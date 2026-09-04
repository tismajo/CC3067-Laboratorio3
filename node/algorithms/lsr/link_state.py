"""
Link State Routing — ver PROTOCOLO.md §info (LSP).

1. Cada nodo genera su propio LSP con sus enlaces directos.
2. Lo inunda con ``to="*"`` (usa el flooding de LDM, sin modificarlo).
3. Recolecta los LSPs de los demás y arma la topología completa.
4. Corre Dijkstra (de MJ, sin modificarlo) desde sí mismo.
5. Recalcula al recibir un LSP más nuevo, al expirar uno (30 s) o al cambiar
   el estado de un vecino.

Direccionamiento por ``IP:puerto``: el ``origin`` del LSP y los ``id`` de sus
enlaces son direcciones.
"""

from __future__ import annotations

import threading
import time

from node.algorithms.dijkstra.dijkstra import build_routing_table
from node.algorithms.dijkstra.topology import Topology
from node.algorithms.flooding.neighbor_discovery import NeighborTable
from node.algorithms.lsr.lsp import build_lsp, is_newer, parse_lsp
from shared import constants as c
from shared.interfaces import RoutingAlgorithm
from shared.protocol import (
    VIA_HEADER,
    build_message,
    get_header,
    prepare_forward,
)

LSP_EXPIRY_SECONDS = 30.0
LSP_ORIGINATE_INTERVAL = 10.0


class LinkStateRouter(RoutingAlgorithm):
    def __init__(
        self,
        neighbor_timeout: float = 15.0,
        self_info: dict | None = None,
    ):
        self.node_id: str | None = None
        self.self_info: dict = dict(self_info or {})
        self._link_costs: dict[str, float] = {}
        self.neighbor_table = NeighborTable(timeout=neighbor_timeout)
        self.sequence = 0
        # origin -> {"lsp": dict, "received_at": float}
        self.lsp_db: dict[str, dict] = {}
        self.routing_table: dict[str, str] = {}
        self._outgoing: list[dict] = []
        self._last_originate = 0.0
        self._lock = threading.RLock()

    # -- ciclo de vida ----------------------------------------------------

    def initialize(self, node_id: str, neighbors: list) -> None:
        self.node_id = node_id
        self.self_info["node_id"] = node_id
        self.self_info.setdefault("proto", c.PROTO_LSR)
        self._link_costs = {n["node_id"]: n.get("weight", 1) for n in neighbors}
        self.sequence = 0
        self.neighbor_table = NeighborTable(
            neighbors, timeout=self.neighbor_table.timeout
        )
        # ponytail: arranca anunciando los enlaces configurados como activos;
        # la realidad la corrige el primer hello/echo o el health check.
        for neighbor in neighbors:
            self.neighbor_table.mark_up(neighbor["node_id"])

        with self._lock:
            self._outgoing = self.neighbor_table.build_hello_packets(self.self_info)
        self.broadcast_own_lsp()

    # -- generación y difusión ------------------------------------------

    def broadcast_own_lsp(self) -> None:
        with self._lock:
            self.sequence += 1
            self._last_originate = time.time()
            active = self.neighbor_table.get_active_neighbors()
            lsp = build_lsp(
                self.node_id,
                self.sequence,
                [
                    {
                        "id": nb["node_id"],
                        "weight": nb.get(
                            "weight", self._link_costs.get(nb["node_id"], 1)
                        ),
                    }
                    for nb in active
                ],
                age_s=0,
            )
            self.lsp_db[self.node_id] = {"lsp": lsp, "received_at": time.time()}
            self.recompute_routing_table()
            self._outgoing.append(
                build_message(
                    proto=c.PROTO_LSR,
                    type_=c.TYPE_INFO,
                    src=self.node_id,
                    dst=c.BROADCAST_TO,
                    payload=lsp,
                )
            )

    def handle_info_packet(self, packet: dict) -> None:
        lsp = parse_lsp(packet.get(c.FIELD_PAYLOAD))
        if not self.on_lsp_received(lsp):
            return

        with self._lock:
            came_from = {packet.get(c.FIELD_FROM), get_header(packet, VIA_HEADER)}
            forwarded = prepare_forward(packet, self.node_id)
            if forwarded is None:
                return
            for neighbor in self.neighbor_table.get_active_neighbors():
                target = neighbor["node_id"]
                if target in came_from:
                    continue
                copy = dict(forwarded)
                copy[c.FIELD_TO] = target
                self._outgoing.append(copy)

    def on_lsp_received(self, lsp: dict) -> bool:
        with self._lock:
            existing = self.lsp_db.get(lsp["origin"])
            existing_lsp = existing["lsp"] if existing else None
            if not is_newer(existing_lsp, lsp):
                return False
            self.lsp_db[lsp["origin"]] = {"lsp": lsp, "received_at": time.time()}
            self.recompute_routing_table()
            return True

    # -- expiración y re-origen ----------------------------------------

    def on_periodic_tick(self) -> None:
        now = time.time()
        self.expire_lsps(now)
        if now - self._last_originate >= LSP_ORIGINATE_INTERVAL:
            self.broadcast_own_lsp()

    def expire_lsps(self, now: float | None = None) -> list[str]:
        current = time.time() if now is None else now
        with self._lock:
            stale = [
                origin
                for origin, entry in self.lsp_db.items()
                if origin != self.node_id
                and current - entry["received_at"] >= LSP_EXPIRY_SECONDS
            ]
            for origin in stale:
                del self.lsp_db[origin]
            if stale:
                self.recompute_routing_table()
        return stale

    # -- topología derivada -------------------------------------------

    def build_topology_from_lsps(self) -> Topology:
        advertised = {
            entry["lsp"]["origin"]: {
                link["id"]: link["weight"] for link in entry["lsp"]["neighbors"]
            }
            for entry in self.lsp_db.values()
        }
        topology = Topology()
        for origin, links in advertised.items():
            for neighbor, weight in links.items():
                back = advertised.get(neighbor)
                if back is None or origin in back:
                    topology.add_edge(origin, neighbor, weight)
        return topology

    def recompute_routing_table(self) -> None:
        topology = self.build_topology_from_lsps()
        if self.node_id in topology.nodes:
            self.routing_table = build_routing_table(topology, self.node_id)
        else:
            self.routing_table = {}

    # -- eventos de vecinos ------------------------------------------

    def handle_hello_packet(self, packet: dict) -> dict:
        return self.neighbor_table.on_hello_received(packet)

    def handle_echo_packet(self, packet: dict) -> dict:
        return self.neighbor_table.on_echo_received(packet)

    def handle_neighbor_up(self, node_id: str) -> None:
        self.neighbor_table.mark_up(node_id)
        self.broadcast_own_lsp()

    def handle_neighbor_down(self, node_id: str) -> None:
        self.neighbor_table.mark_down(node_id)
        self.broadcast_own_lsp()

    # -- consultas de forwarding -----------------------------------

    def get_next_hop(self, destination: str):
        with self._lock:
            return self.routing_table.get(destination)

    def get_outgoing_packets(self) -> list[dict]:
        with self._lock:
            packets = list(self._outgoing)
            self._outgoing.clear()
            return packets
