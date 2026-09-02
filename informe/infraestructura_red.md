# Infraestructura de red

## Propósito

Dijkstra y Flooding calculan rutas o deciden reenvíos, pero ninguno abre un socket. La Fase 3 es la capa que los conecta con la red real: escuchar paquetes entrantes, enviarlos por IP:puerto, decidir qué hacer con cada uno según su tipo, y detectar cuándo un vecino se cae o se recupera. Todo el código de esta fase conoce únicamente el contrato `RoutingAlgorithm` de `shared/interfaces.py`; nunca importa una clase concreta de Dijkstra, Flooding o LSR.

## Transporte

`node/network/socket_manager.py` usa TCP con un patrón de un paquete por conexión: `connect` → enviar el JSON serializado (`shared/protocol.serialize`) → cerrar. No se mantienen conexiones persistentes entre nodos.

- `start_listening(on_packet_received)` abre un socket servidor en un hilo daemon. Cada conexión aceptada se atiende en su propio hilo, que lee hasta que el emisor cierra la conexión y entrega el contenido crudo al callback.
- `send(to_ip, to_port, packet)` abre una conexión con timeout, envía y cierra. Si el vecino no responde (caído, timeout, puerto cerrado), la excepción de socket se traduce a `NeighborUnreachableError`, para que el resto del sistema no dependa de excepciones crudas de `socket`.

## Forwarding

`node/network/forwarding.py` define la clase `Forwarder`, que junta al algoritmo activo, la tabla de ruteo compartida, el `SocketManager` y el mapa de direcciones de los vecinos configurados. `handle_incoming_packet` despacha cada paquete según `type`:

- **message**: si el destino es este nodo, se imprime; si no, se busca el siguiente salto en `RoutingTable` y se reenvía con el TTL decrementado (`shared.protocol.decrement_ttl`). Un TTL agotado o un destino sin ruta conocida se descartan silenciosamente.
- **info**: se delega en `algorithm.handle_info_packet`, que es el único método de la interfaz pensado para que cada algoritmo actualice su estado interno (LSP, vector de distancias, etc.).
- **hello**: si el algoritmo expone `handle_hello_packet` (como Flooding) se usa; si no, se cae a `algorithm.handle_neighbor_up`, que sí es parte del contrato común.

Después de procesar un `info` o un `hello`, `Forwarder` reenvía lo que el algoritmo haya dejado pendiente en `get_outgoing_packets()` y llama a `sync_routing_table()`.

### Por qué `forward_data_packet` no llama al algoritmo directamente

`node/routing/routing_table.py` es la estructura pensada para desacoplar el hilo de routing (que actualiza al algoritmo) del hilo de forwarding (que reenvía datos). `forward_data_packet` solo lee de `RoutingTable`, nunca del algoritmo. `sync_routing_table` es quien traduce el estado del algoritmo a esa tabla, usando exclusivamente `algorithm.get_next_hop(destino)` — el método que la interfaz documenta explícitamente para este propósito — para cada destino conocido (los vecinos configurados, más las claves de `algorithm.routing_table` cuando ese atributo existe, como en Dijkstra). Así, el módulo de forwarding no necesita conocer los internals de cada algoritmo concreto.

## Health check

`node/network/health_check.py` define `HealthChecker`, que cada `interval_seconds` intenta enviar un HELLO a cada vecino configurado. Un envío que falla (`NeighborUnreachableError`) cuenta como intento fallido; tras `max_failures` fallos consecutivos el vecino se marca caído y se notifica vía `on_status_change`. Si un vecino caído vuelve a responder, se notifica la recuperación.

`HealthChecker` es agnóstico del algoritmo de ruteo: en `node/main.py`, `on_status_change` es quien llama `algorithm.handle_neighbor_up`/`handle_neighbor_down` y dispara `forwarder.sync_routing_table()`.

## Modo en vivo

```bash
python -m node.main --config shared/config/topology_example.json --mode flooding --live
```

Con `--live`, el nodo arma `RoutingTable`, `SocketManager`, `Forwarder` y `HealthChecker`, empieza a escuchar, envía los paquetes iniciales que el algoritmo tenga pendientes (por ejemplo, los HELLO de Flooding) y arranca el chequeo de salud. Luego entra en un loop interactivo por stdin: una línea `destino: mensaje` construye y envía un paquete `message` real. `Ctrl+C` o EOF detiene el health check y cierra el socket antes de salir.

Sin `--live`, el comportamiento es idéntico al de las fases 1 y 2: calcula e imprime un resumen estático sin abrir sockets.

## Pruebas

Cada módulo tiene su propio archivo de pruebas, con dobles de prueba (`SocketManager`/`RoutingAlgorithm` falsos) para no depender de la red real salvo en `test_socket_manager.py`, que sí abre sockets TCP reales en `127.0.0.1` con puertos efímeros.

```bash
python -m pytest tests/test_routing_table.py tests/test_socket_manager.py tests/test_forwarding.py tests/test_health_check.py -q
python -m pytest tests/ -q
```
