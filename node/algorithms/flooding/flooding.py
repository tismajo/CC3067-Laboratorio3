"""Algoritmo Flooding modular, sin dependencias de sockets."""

from __future__ import annotations

import hashlib
import json
import threading

from node.algorithms.flooding.neighbor_discovery import NeighborTable
from shared import constants as c
from shared.interfaces import RoutingAlgorithm


PACKET_ID_HEADER = "packet_id"


def get_packet_id(packet: dict) -> str:
    """Obtiene el ID explícito o genera una huella estable del paquete.

    El TTL se excluye de la huella porque cambia en cada salto. Se recomienda
    incluir ``{"packet_id": "..."}`` en ``headers`` para distinguir envíos
    legítimos con el mismo contenido.
    """

    headers = packet.get(c.FIELD_HEADERS, [])
    header_items = headers if isinstance(headers, list) else [headers]
    for header in header_items:
        if isinstance(header, dict) and header.get(PACKET_ID_HEADER) is not None:
            return str(header[PACKET_ID_HEADER])

    identity = {
        c.FIELD_PROTO: packet.get(c.FIELD_PROTO),
        c.FIELD_TYPE: packet.get(c.FIELD_TYPE),
        c.FIELD_FROM: packet.get(c.FIELD_FROM),
        c.FIELD_TO: packet.get(c.FIELD_TO),
        c.FIELD_HEADERS: headers,
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
    """Devuelve una copia con TTL-1, sin modificar el paquete original."""

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
        """Actualiza descubrimiento con un HELLO recibido."""

        return self.neighbor_table.on_hello_received(packet)

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
        """Acepta INFO para cumplir la interfaz y agenda su reenvío."""

        transmissions = self.flood(packet, packet.get(c.FIELD_FROM))
        if transmissions:
            with self._lock:
                self._outgoing_packets.append(transmissions[0][1])

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
