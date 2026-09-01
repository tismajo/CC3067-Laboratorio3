"""
Fase 3 (Infraestructura de red)

Estructura compartida y thread-safe que guarda la tabla de ruteo actual del
nodo: {destino: siguiente_salto}. La llenan los algoritmos (dijkstra.py,
flooding.py o link_state.py, según el modo) y la consulta forwarding.py
para decidir a quién reenviar un paquete de datos.

TODO:
- [ ] Clase RoutingTable con lock (thread-safe: routing y forwarding corren
      en hilos distintos)
- [ ] Método update(new_table: dict)
- [ ] Método get_next_hop(destination: str) -> str | None
- [ ] Método snapshot() -> dict (para imprimir/depurar la tabla actual)
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
