"""
Fase 2 (Flooding)

Implementación de flooding: reenvía cada paquete recibido a todos los
vecinos activos excepto por quien llegó, controlando TTL y evitando
reenviar paquetes duplicados (ciclos infinitos).

Debe poder usarse:
1. De forma standalone (modo "flooding" del nodo)
2. Desde LSR (HDB la usará para inundar los LSPs por toda la red)

Por eso NO debe depender directamente de sockets: expone funciones que
reciben/regresan paquetes (dict), y quien los envía de verdad es
node/network/socket_manager.py (a través de forwarding.py).

TODO:
- [ ] Clase o funciones para trackear IDs de paquetes ya vistos (evitar duplicados)
- [ ] should_forward(packet: dict) -> bool (chequea TTL y si ya se vio)
- [ ] get_forward_targets(packet: dict, neighbor_table: NeighborTable, received_from) -> lista de vecinos a los que reenviar
- [ ] decrement_ttl(packet: dict) -> dict
"""

def should_forward(packet: dict, seen_packet_ids: set) -> bool:
    raise NotImplementedError


def get_forward_targets(packet: dict, neighbor_table, received_from):
    raise NotImplementedError


def decrement_ttl(packet: dict) -> dict:
    raise NotImplementedError
