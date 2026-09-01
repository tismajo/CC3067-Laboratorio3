"""
Fase 3 (Infraestructura de red)

Proceso/hilo de forwarding: decide qué hacer con cada paquete que entra o sale.

Entrantes:
- type == "message": si soy el destino -> print; si no -> reenviar según la
  tabla de ruteo (consultar node/routing/routing_table.py)
- type == "info": pasar el contenido al proceso de routing (dijkstra/flooding/lsr)
- type == "hello": responder / usar para medir delay y descubrir vecinos

Salientes:
- Forward de mensajes de usuario
- Forward de flooding
- Forward de paquetes DV/LSP/INFO
- Envío de HELLO/PING
- Confirmaciones de recepción (si se implementan)

TODO:
- [ ] handle_incoming_packet(packet: dict) -> despacha según packet["type"]
- [ ] forward_data_packet(packet: dict) -> usa routing_table para decidir el siguiente salto
- [ ] forward_info_packet(packet: dict) -> entrega el payload al algoritmo activo
- [ ] handle_hello_packet(packet: dict) -> responde y/o mide delay
- [ ] Decrementar y validar TTL antes de reenviar
"""

def handle_incoming_packet(packet: dict):
    raise NotImplementedError


def forward_data_packet(packet: dict):
    raise NotImplementedError


def forward_info_packet(packet: dict):
    raise NotImplementedError


def handle_hello_packet(packet: dict):
    raise NotImplementedError
