"""
Fase 3 (Infraestructura de red)

Decide qué hacer con cada paquete que entra o sale del nodo.

Entrantes:
- type == "message": si soy el destino -> print; si no -> reenviar según la
  tabla de ruteo (node/routing/routing_table.py)
- type == "info": pasar el contenido al proceso de routing (dijkstra/flooding/lsr)
- type == "hello": responder / usar para medir delay y descubrir vecinos

Salientes:
- Forward de mensajes de usuario (propios o reenviados)
- Paquetes que el algoritmo activo tenga pendientes (get_outgoing_packets)

`forward_data_packet` consulta RoutingTable en vez del algoritmo directamente:
routing (que actualiza el algoritmo) y forwarding corren en hilos distintos,
y RoutingTable es el punto de sincronización thread-safe entre ambos.
"""

from __future__ import annotations

from node.routing.routing_table import RoutingTable
from shared import constants as c
from shared.protocol import build_packet, decrement_ttl, deserialize


class Forwarder:
    def __init__(
        self,
        node_id: str,
        proto: str,
        algorithm,
        routing_table: RoutingTable,
        socket_manager,
        neighbor_addresses: dict,
    ):
        self.node_id = node_id
        self.proto = proto
        self.algorithm = algorithm
        self.routing_table = routing_table
        self.socket_manager = socket_manager
        self.neighbor_addresses = dict(neighbor_addresses)

    def handle_incoming_packet(self, raw: str, addr=None) -> None:
        packet = deserialize(raw)
        packet_type = packet.get(c.FIELD_TYPE)
        if packet_type == c.TYPE_MESSAGE:
            self.forward_data_packet(packet)
        elif packet_type == c.TYPE_INFO:
            self.forward_info_packet(packet)
        elif packet_type == c.TYPE_HELLO:
            self.handle_hello_packet(packet)
        else:
            raise ValueError(f"Tipo de paquete desconocido: {packet_type!r}")

    def forward_data_packet(self, packet: dict) -> None:
        destination = packet.get(c.FIELD_TO)
        if destination == self.node_id:
            print(
                f"[{self.node_id}] mensaje de {packet.get(c.FIELD_FROM)}: "
                f"{packet.get(c.FIELD_PAYLOAD)}"
            )
            return

        if packet.get(c.FIELD_TTL, 0) <= 1:
            return

        next_hop = self.routing_table.get_next_hop(destination)
        if next_hop is None:
            return

        self._send_to_neighbor(next_hop, decrement_ttl(packet))

    def forward_info_packet(self, packet: dict) -> None:
        self.algorithm.handle_info_packet(packet)
        self._flush_outgoing()
        self.sync_routing_table()

    def handle_hello_packet(self, packet: dict) -> None:
        handler = getattr(self.algorithm, "handle_hello_packet", None)
        if handler is not None:
            handler(packet)
        else:
            self.algorithm.handle_neighbor_up(packet.get(c.FIELD_FROM))
        self._flush_outgoing()
        self.sync_routing_table()

    def send_message(self, destination: str, payload) -> None:
        packet = build_packet(
            proto=self.proto,
            type_=c.TYPE_MESSAGE,
            from_=self.node_id,
            to=destination,
            payload=payload,
        )
        self.forward_data_packet(packet)

    def send_outgoing(self) -> None:
        """Envía lo que el algoritmo tenga pendiente (p.ej. HELLOs iniciales)."""
        self._flush_outgoing()

    def sync_routing_table(self) -> None:
        """Refresca RoutingTable a partir del estado actual del algoritmo.

        Se llama tras cada evento que puede cambiar rutas (info, hello,
        vecino caído/recuperado desde health check).
        """
        destinations = set(self.neighbor_addresses)
        if hasattr(self.algorithm, "routing_table"):
            destinations |= set(self.algorithm.routing_table)

        table = {}
        for destination in destinations:
            next_hop = self.algorithm.get_next_hop(destination)
            if next_hop is not None:
                table[destination] = next_hop
        self.routing_table.update(table)

    def _flush_outgoing(self) -> None:
        for packet in self.algorithm.get_outgoing_packets():
            self._send_to_neighbor(packet.get(c.FIELD_TO), packet)

    def _send_to_neighbor(self, neighbor_id: str, packet: dict) -> None:
        address = self.neighbor_addresses.get(neighbor_id)
        if address is None:
            return
        self.socket_manager.send(address["ip"], address["port"], packet)
