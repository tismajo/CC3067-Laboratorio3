"""Algoritmo Flooding modular, sin dependencias de sockets."""

from __future__ import annotations

import hashlib
import json
import threading

from node.algorithms.flooding.neighbor_discovery import NeighborTable
from shared import constants as c
from shared.interfaces import RoutingAlgorithm
from shared.protocol import MSG_ID_HEADER, get_header


def get_packet_id(packet: dict) -> str:
    """ID lógico del paquete para deduplicar en flooding.

    Se usa ``msg_id`` (se conserva al reenviar). Si falta, un hash de
    ``(from, to, type, payload)``. El TTL NUNCA entra: cambia en cada salto y
    haría que cada copia pareciera nueva (PROTOCOLO.md §message).
    """

    msg_id = get_header(packet, MSG_ID_HEADER)
    if msg_id is not None:
        return str(msg_id)

    identity = {
        c.FIELD_FROM: packet.get(c.FIELD_FROM),
        c.FIELD_TO: packet.get(c.FIELD_TO),
        c.FIELD_TYPE: packet.get(c.FIELD_TYPE),
        c.FIELD_PAYLOAD: packet.get(c.FIELD_PAYLOAD),
    }
    encoded = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def should_forward(packet: dict, seen_packet_ids: set[str]) -> bool:
    """Decide si un paquete puede avanzar y registra su ID como visto."""

    ttl = packet.get(c.FIELD_TTL)
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 1:
        return False

    packet_id = get_packet_id(packet)
    if packet_id in seen_packet_ids:
        return False

    seen_packet_ids.add(packet_id)
    return True


def get_forward_targets(
    packet: dict,
    neighbor_table: NeighborTable,
    received_from: str | dict | None,
) -> list[dict]:
    """Devuelve vecinos activos excepto el salto que entregó el paquete."""

    del packet
    sender_id = (
        received_from.get("node_id")
        if isinstance(received_from, dict)
        else received_from
    )
    return [
        neighbor
        for neighbor in neighbor_table.get_active_neighbors()
        if neighbor["node_id"] != sender_id
    ]


def decrement_ttl(packet: dict) -> dict:
    """Devuelve una copia con TTL-1, sin modificar el original."""

    ttl = packet.get(c.FIELD_TTL)
    if not isinstance(ttl, int) or isinstance(ttl, bool):
        raise ValueError("El TTL debe ser un entero")
    if ttl <= 0:
        raise ValueError("El TTL no puede decrementarse por debajo de cero")

    forwarded = dict(packet)
    forwarded[c.FIELD_TTL] = ttl - 1
    return forwarded


class FloodingRoutingAlgorithm(RoutingAlgorithm):
    """Adaptador de Flooding para el contrato común de enrutamiento."""

    def __init__(
        self,
        neighbor_timeout: float = 15.0,
        self_info: dict | None = None,
    ):
        self.node_id: str | None = None
        self.self_info: dict = dict(self_info or {})
        self.neighbor_table = NeighborTable(timeout=neighbor_timeout)
        self.seen_packet_ids: set[str] = set()
        self._outgoing_packets: list[dict] = []
        self._lock = threading.RLock()

    def initialize(self, node_id: str, neighbors: list) -> None:
        self.node_id = node_id
        self.self_info["node_id"] = node_id
        self.self_info.setdefault("proto", c.PROTO_FLOODING)
        self.neighbor_table = NeighborTable(
            neighbors,
            timeout=self.neighbor_table.timeout,
        )
        with self._lock:
            self.seen_packet_ids.clear()
            self._outgoing_packets = self.neighbor_table.build_hello_packets(
                self.self_info
            )

    def handle_hello_packet(self, packet: dict) -> dict:
        return self.neighbor_table.on_hello_received(packet)

    def handle_echo_packet(self, packet: dict) -> dict:
        return self.neighbor_table.on_echo_received(packet)

    def flood(
        self,
        packet: dict,
        received_from: str | dict | None = None,
    ) -> list[tuple[dict, dict]]:
        """Prepara pares ``(vecino, paquete)`` para que Forwarding los envíe."""

        with self._lock:
            if not should_forward(packet, self.seen_packet_ids):
                return []
            targets = get_forward_targets(
                packet,
                self.neighbor_table,
                received_from,
            )
            forwarded = decrement_ttl(packet)
            return [(target, dict(forwarded)) for target in targets]

    def handle_info_packet(self, packet: dict) -> None:
        transmissions = self.flood(packet, packet.get(c.FIELD_FROM))
        if not transmissions:
            return
        with self._lock:
            for neighbor, copy in transmissions:
                routed = dict(copy)
                routed[c.FIELD_TO] = neighbor["node_id"]
                self._outgoing_packets.append(routed)

    def handle_neighbor_up(self, node_id: str) -> None:
        self.neighbor_table.mark_up(node_id)

    def handle_neighbor_down(self, node_id: str) -> None:
        self.neighbor_table.mark_down(node_id)

    def get_next_hop(self, destination: str):
        neighbor = self.neighbor_table.get_neighbor(destination)
        if neighbor and neighbor.get("active"):
            return destination
        return None

    def get_outgoing_packets(self) -> list[dict]:
        with self._lock:
            packets = list(self._outgoing_packets)
            self._outgoing_packets.clear()
            return packets
