"""
DUEÑO: EA (Ernesto Ascencio) - Fase 0

Este es el contrato que permite que MJ (Dijkstra), LDM (Flooding) y HDB (LSR)
trabajen en paralelo sin esperarse entre sí ni esperar a que EA termine
node/network/*.

node/main.py y node/network/forwarding.py (de EA) SOLO conocen esta interfaz,
nunca una clase concreta. Así:
  - EA puede construir forwarding/sockets/health-check usando un
    RoutingAlgorithm "falso" (un mock/dummy) desde el día 1, sin esperar a
    que Dijkstra/Flooding/LSR existan.
  - MJ, LDM y HDB implementan cada quien su propia clase concreta, la
    prueban con pytest de forma aislada, y el día que se conecte todo con
    node/main.py debería simplemente encajar.

Cada uno de los 3 algoritmos debe tener, en su propio archivo, una clase que
herede de RoutingAlgorithm:
  - node/algorithms/dijkstra/dijkstra.py   -> class DijkstraRoutingAlgorithm
  - node/algorithms/flooding/flooding.py   -> class FloodingRoutingAlgorithm
  - node/algorithms/lsr/link_state.py      -> class LinkStateRouter
"""

from abc import ABC, abstractmethod


class RoutingAlgorithm(ABC):

    @abstractmethod
    def initialize(self, node_id: str, neighbors: list) -> None:
        """Se llama una sola vez al arrancar el nodo, con sus vecinos directos
        (lista de dicts: node_id, ip, port, weight)."""
        raise NotImplementedError

    @abstractmethod
    def handle_info_packet(self, packet: dict) -> None:
        """Se llama cuando llega un paquete type=info (LSP, vector de
        distancias, etc. según el algoritmo). Actualiza el estado interno."""
        raise NotImplementedError

    @abstractmethod
    def handle_neighbor_up(self, node_id: str) -> None:
        """Se llama cuando health_check.py detecta que un vecino volvió."""
        raise NotImplementedError

    @abstractmethod
    def handle_neighbor_down(self, node_id: str) -> None:
        """Se llama cuando health_check.py detecta que un vecino se cayó."""
        raise NotImplementedError

    @abstractmethod
    def get_next_hop(self, destination: str):
        """Regresa el node_id/ip del siguiente salto para llegar a
        'destination', o None si no hay ruta conocida. Esto es lo que
        forwarding.py consulta para reenviar un paquete de datos."""
        raise NotImplementedError

    @abstractmethod
    def get_outgoing_packets(self) -> list:
        """Regresa una lista de paquetes (dicts, ya armados con
        shared.protocol.build_packet) que el nodo necesita enviar/reenviar
        en este momento (ej. su propio LSP, un flood, un vector de
        distancias). node/network/forwarding.py los toma y los envía."""
        raise NotImplementedError
