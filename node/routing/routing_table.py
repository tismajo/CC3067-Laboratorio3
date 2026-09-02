"""
Fase 3 (Infraestructura de red)

Estructura compartida y thread-safe que guarda la tabla de ruteo actual del
nodo: {destino: siguiente_salto}. La llenan los algoritmos (dijkstra.py,
flooding.py o link_state.py, según el modo) y la consulta forwarding.py
para decidir a quién reenviar un paquete de datos.
"""

import threading


class RoutingTable:
    def __init__(self):
        self._lock = threading.RLock()
        self._table: dict = {}

    def update(self, new_table: dict) -> None:
        with self._lock:
            self._table = dict(new_table)

    def get_next_hop(self, destination: str):
        with self._lock:
            return self._table.get(destination)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._table)
