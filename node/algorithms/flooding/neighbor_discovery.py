"""
Fase 2 (Flooding)

Flooding solo necesita conocer a sus vecinos directos (no la topología
completa). Este módulo maneja el descubrimiento y el estado de esos vecinos
usando paquetes tipo HELLO/PING (coordinar formato con EA en shared/protocol.py).

TODO:
- [ ] Clase NeighborTable: guarda vecinos conocidos (node_id, ip, port, delay, estado)
- [ ] Método on_hello_received(packet) -> actualiza delay/estado del vecino
- [ ] Método build_hello_packet(self_info) -> usa shared/protocol.build_packet
- [ ] Método get_active_neighbors() -> excluye a los marcados como caídos
"""

class NeighborTable:
    def __init__(self, initial_neighbors=None):
        raise NotImplementedError

    def on_hello_received(self, packet: dict):
        raise NotImplementedError

    def get_active_neighbors(self):
        raise NotImplementedError
