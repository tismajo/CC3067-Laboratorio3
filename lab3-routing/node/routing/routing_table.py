"""
DUEÑO: EA (Ernesto Ascencio) - Fase 3 (Infraestructura de red)

Cache thread-safe de next-hops, para no llamar algorithm.get_next_hop()
en el hilo caliente de forwarding en cada paquete.

TODO (EA):
- [ ] Clase RoutingTable con lock
- [ ] Método update(new_table: dict)
- [ ] Método get_next_hop(destination: str) -> str | None
- [ ] Método snapshot() -> dict (para imprimir/depurar)
"""

class RoutingTable:
    def __init__(self):
        raise NotImplementedError

    def update(self, new_table: dict):
        raise NotImplementedError

    def get_next_hop(self, destination: str):
        raise NotImplementedError

    def snapshot(self) -> dict:
        raise NotImplementedError
