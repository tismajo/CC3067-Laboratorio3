"""
DUEÑO: LDM (Leonardo Dufrey Mejía) - Fase 2 (Flooding)

TODO (LDM):
- [ ] Clase NeighborTable: guarda vecinos conocidos (node_id, ip, port, delay, estado)
- [ ] Método on_hello_received(packet) -> actualiza delay/estado del vecino
- [ ] Método build_hello_packet(self_info) -> usa shared.protocol.build_packet + shared.constants.TYPE_HELLO
- [ ] Método get_active_neighbors() -> excluye a los marcados como caídos
"""

from shared import constants as c
from shared import protocol


class NeighborTable:
    def __init__(self, initial_neighbors=None):
        raise NotImplementedError

    def on_hello_received(self, packet: dict):
        raise NotImplementedError

    def get_active_neighbors(self):
        raise NotImplementedError
