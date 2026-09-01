"""
Fase 3 (Infraestructura de red)

Punto de entrada del nodo. Debe permitir levantar un nodo en cualquiera de
los 3 modos de forma independiente:

    python -m node.main --config shared/config/topology_example.json --mode dijkstra
    python -m node.main --config shared/config/topology_example.json --mode flooding
    python -m node.main --config shared/config/topology_example.json --mode lsr

TODO:
- [ ] Parsear argumentos: --config, --mode
- [ ] Cargar configuración (node_id, ip, port, neighbors) desde el JSON
- [ ] Instanciar SocketManager (node/network/socket_manager.py)
- [ ] Según --mode, instanciar el algoritmo correspondiente:
        "dijkstra" -> node/algorithms/dijkstra
        "flooding" -> node/algorithms/flooding
        "lsr"      -> node/algorithms/lsr (usa dijkstra + flooding internamente)
- [ ] Levantar los 2 hilos/procesos: forwarding y routing (ver node/network/forwarding.py
      y node/routing/routing_table.py)
- [ ] Levantar el health check de vecinos (node/network/health_check.py)
- [ ] Loop principal / CLI para enviar mensajes de usuario a un destino
"""

def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
