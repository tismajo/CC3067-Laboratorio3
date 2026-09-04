"""
Fase 3 (Infraestructura de red)

`forward_data_packet` consulta RoutingTable en vez del algoritmo directamente:
routing y forwarding corren en hilos distintos y RoutingTable es el punto de
sincronización thread-safe.

Direccionamiento por ``IP:puerto`` (ver PROTOCOLO.md). ``node_id`` en esta clase
es la dirección propia del nodo.
"""

from __future__ import annotations

import logging

from node.network.socket_manager import NeighborUnreachableError
from node.routing.routing_table import RoutingTable
from shared import constants as c
from shared.protocol import (
    BROADCAST_TO,
    build_echo,
    build_message,
    get_header,
    normalize_addr,
    parse_message,
    prepare_forward,
)

logger = logging.getLogger("forwarding")


class Forwarder:
    def __init__(
        self,
        node_id: str,
        proto: str,
        algorithm,
        routing_table: RoutingTable,
        socket_manager,
        neighbor_addresses: dict,
        default_port: int = 5000,
    ):
        self.node_id = node_id
        self.proto = proto
        self.algorithm = algorithm
        self.routing_table = routing_table
        self.socket_manager = socket_manager
        self.neighbor_addresses = dict(neighbor_addresses)
        self.default_port = default_port

    def _norm(self, addr: str) -> str:
        return normalize_addr(addr, self.default_port)

    def _is_self(self, addr: str) -> bool:
        return self._norm(addr) == self._norm(self.node_id)

    def handle_incoming_packet(self, raw, addr=None) -> None:
        packet = parse_message(raw)
        if packet is None:
            return
        packet_type = packet.get(c.FIELD_TYPE)
        if packet_type == c.TYPE_MESSAGE:
            self.forward_data_packet(packet)
        elif packet_type == c.TYPE_INFO:
            self.forward_info_packet(packet)
        elif packet_type == c.TYPE_HELLO:
            self.handle_hello_packet(packet)
        elif packet_type == c.TYPE_ECHO:
            self.handle_echo_packet(packet)
        else:
            logger.warning("Tipo de paquete desconocido: %r", packet_type)

    def forward_data_packet(self, packet: dict) -> None:
        destination = packet.get(c.FIELD_TO)
        if self._is_self(destination):
            print(
                f"[{self.node_id}] mensaje de {packet.get(c.FIELD_FROM)}: "
                f"{packet.get(c.FIELD_PAYLOAD)}"
            )
            return

        flood = getattr(self.algorithm, "flood", None)
        if flood is not None:
            for neighbor, copy in flood(packet, packet.get(c.FIELD_FROM)):
                self._send_to_neighbor(neighbor["node_id"], copy)
            return

        next_hop = self.routing_table.get_next_hop(self._norm(destination))
        if next_hop is None:
            logger.info("NO_ROUTE: %s (descartado en %s)", destination, self.node_id)
            return

        forwarded = prepare_forward(packet, self.node_id)
        if forwarded is None:
            return
        self._send_to_neighbor(next_hop, forwarded)

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
        # Responder el echo por el mismo protocolo (PROTOCOLO.md §hello/echo).
        origin = packet.get(c.FIELD_FROM)
        if origin and not self._is_self(origin):
            self._send_to_neighbor(origin, build_echo(packet, self.node_id))
        self._flush_outgoing()
        self.sync_routing_table()

    def handle_echo_packet(self, packet: dict) -> None:
        handler = getattr(self.algorithm, "handle_echo_packet", None)
        if handler is not None:
            handler(packet)
        else:
            self.algorithm.handle_neighbor_up(packet.get(c.FIELD_FROM))
        self._flush_outgoing()
        self.sync_routing_table()

    def send_message(self, destination: str, payload) -> None:
        packet = build_message(
            proto=self.proto,
            type_=c.TYPE_MESSAGE,
            src=self.node_id,
            dst=self._norm(destination),
            payload=payload,
        )
        self.forward_data_packet(packet)

    def send_outgoing(self) -> None:
        self._flush_outgoing()

    def sync_routing_table(self) -> None:
        destinations = set(self.neighbor_addresses)
        if hasattr(self.algorithm, "routing_table"):
            destinations |= set(self.algorithm.routing_table)

        table = {}
        for destination in destinations:
            next_hop = self.algorithm.get_next_hop(destination)
            if next_hop is not None:
                table[self._norm(destination)] = next_hop
        self.routing_table.update(table)

    def _flush_outgoing(self) -> None:
        for packet in self.algorithm.get_outgoing_packets():
            self._send_to_neighbor(packet.get(c.FIELD_TO), packet)

    def _send_to_neighbor(self, neighbor_id: str, packet: dict) -> None:
        if neighbor_id == BROADCAST_TO:
            for address in list(self.neighbor_addresses):
                self._send_to_neighbor(address, packet)
            return
        address = self.neighbor_addresses.get(self._norm(neighbor_id))
        if address is None:
            return
        try:
            self.socket_manager.send(address["ip"], address["port"], packet)
        except NeighborUnreachableError:
            # Un vecino que aún no escucha o que se acaba de caer no debe tumbar
            # el nodo: el health check lo detecta y reintenta.
            pass
