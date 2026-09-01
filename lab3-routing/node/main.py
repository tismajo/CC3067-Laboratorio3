"""
DUEÑO: EA (Ernesto Ascencio) - Fase 3 (Infraestructura de red)

Punto de entrada del nodo:
    python -m node.main --config shared/config/topology_example.json --mode dijkstra
    python -m node.main --config shared/config/topology_example.json --mode flooding
    python -m node.main --config shared/config/topology_example.json --mode lsr

Este archivo NO importa las clases concretas de dijkstra/flooding/lsr por
nombre en la lógica principal: las selecciona por --mode y las trata todas
como shared.interfaces.RoutingAlgorithm. Así se puede empezar a construir
esto sin esperar a que MJ/LDM/HDB terminen sus algoritmos.

TODO (EA):
- [ ] Parsear argumentos: --config, --mode
- [ ] Cargar configuración (node_id, ip, port, neighbors) desde el JSON
- [ ] Según --mode, instanciar la clase concreta correspondiente
      (DijkstraRoutingAlgorithm | FloodingRoutingAlgorithm | LinkStateRouter)
      y llamar a .initialize(node_id, neighbors)
- [ ] Instanciar SocketManager (node/network/socket_manager.py)
- [ ] Levantar los 2 hilos: forwarding (node/network/forwarding.py) y
      routing (consulta periódica a algorithm.get_outgoing_packets())
- [ ] Levantar el health check de vecinos (node/network/health_check.py),
      conectado a algorithm.handle_neighbor_up/down
- [ ] Loop principal / CLI para enviar mensajes de usuario a un destino
"""

MODE_TO_ALGORITHM = {
    # TODO (EA): completar una vez existan las clases concretas
    # "dijkstra": "node.algorithms.dijkstra.dijkstra.DijkstraRoutingAlgorithm",
    # "flooding": "node.algorithms.flooding.flooding.FloodingRoutingAlgorithm",
    # "lsr": "node.algorithms.lsr.link_state.LinkStateRouter",
}


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
