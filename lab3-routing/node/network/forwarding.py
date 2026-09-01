"""
DUEÑO: EA (Ernesto Ascencio) - Fase 3 (Infraestructura de red)

Recibe un `algorithm: shared.interfaces.RoutingAlgorithm` ya inicializado y
lo usa para decidir next-hop / recibir paquetes de info, sin importar si por
debajo es Dijkstra, Flooding o LSR.

TODO (EA):
- [ ] handle_incoming_packet(packet, algorithm, routing_table) -> despacha
      según packet[c.FIELD_TYPE] (usar shared.constants, no strings literales)
- [ ] forward_data_packet(packet, routing_table) -> decrementa TTL
      (shared.protocol.decrement_ttl) y reenvía al next hop
- [ ] forward_info_packet(packet, algorithm) -> algorithm.handle_info_packet(packet)
- [ ] handle_hello_packet(packet, algorithm) -> algorithm.handle_neighbor_up(...)
"""

from shared import constants as c
from shared import protocol


def handle_incoming_packet(packet: dict, algorithm, routing_table):
    raise NotImplementedError


def forward_data_packet(packet: dict, routing_table):
    raise NotImplementedError


def forward_info_packet(packet: dict, algorithm):
    raise NotImplementedError


def handle_hello_packet(packet: dict, algorithm):
    raise NotImplementedError
