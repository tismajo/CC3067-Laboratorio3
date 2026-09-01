# Algoritmo Flooding

## Propósito

Flooding distribuye un paquete sin necesitar la topología completa ni una tabla de rutas. Cada nodo conoce únicamente a sus vecinos directos y reenvía una copia a todos los vecinos activos, excepto al que entregó el paquete. Esta característica permite utilizarlo como algoritmo standalone y como mecanismo de distribución de paquetes LSP en Link State Routing.

El costo de esta simplicidad es la generación de copias. Una red con ciclos podría reenviar el mismo paquete indefinidamente, por lo que la implementación combina un límite de saltos (TTL) con detección de duplicados.

## Descubrimiento de vecinos

La clase `NeighborTable`, ubicada en `neighbor_discovery.py`, recibe la lista de vecinos configurados del nodo. Cada entrada guarda el identificador, IP, puerto, peso, estado, último instante de actividad y retardo observado. Los vecinos empiezan inactivos hasta confirmar su presencia mediante un paquete `hello`.

Los paquetes de descubrimiento utilizan el protocolo JSON compartido:

```json
{
  "proto": "flooding",
  "type": "hello",
  "from": "A",
  "to": "B",
  "ttl": 1,
  "headers": [],
  "payload": {
    "node_id": "A",
    "ip": "127.0.0.1",
    "port": 5000,
    "sent_at": 10.5
  }
}
```

Al recibir el paquete, `on_hello_received` marca activo al emisor, actualiza su dirección y calcula un retardo aproximado como la diferencia entre recepción y envío. `expire_stale` marca como caído un vecino que no ha enviado actividad dentro del timeout. La tabla utiliza un bloqueo reentrante para permitir su consulta desde los futuros hilos de forwarding y health check.

## Reenvío por inundación

El procesamiento sigue cuatro pasos:

1. Obtener el identificador del paquete desde `headers.packet_id`. Si no existe, se calcula una huella SHA-256 estable con los campos del paquete, excluyendo el TTL.
2. Rechazar el paquete si ya fue procesado o si su TTL es menor o igual que 1.
3. Seleccionar todos los vecinos activos excepto el vecino que entregó el paquete.
4. Crear una copia por destino con el TTL decrementado, sin modificar el paquete original.

Excluir el TTL de la huella es importante porque su valor cambia en cada salto. Para mensajes distintos que tengan exactamente el mismo contenido se recomienda asignar un `packet_id` único en los encabezados.

Si un nodo tiene grado `d`, seleccionar destinos y crear copias requiere `O(d)` tiempo. Consultar o registrar un identificador visto tiene tiempo esperado `O(1)`. La memoria de duplicados crece `O(p)`, donde `p` es el número de paquetes procesados durante la ejecución.

## Modularidad e integración

`FloodingRoutingAlgorithm` implementa el contrato común `RoutingAlgorithm`. El método `flood` devuelve pares `(vecino, paquete)` listos para envío, pero nunca abre sockets. De esta forma, `forwarding.py` puede transmitirlos durante la Fase 3 y el módulo LSR puede reutilizar la misma lógica sin modificarla.

La clase también expone los eventos `handle_neighbor_up` y `handle_neighbor_down`, una cola de paquetes salientes y consulta directa de vecinos activos. El estado compartido se protege con bloqueos para soportar la ejecución asíncrona requerida por la práctica.

## Modo standalone

El modo standalone carga únicamente el nodo y sus vecinos desde la configuración, inicializa el algoritmo y prepara un paquete HELLO para cada vecino:

```bash
python -m node.main --config shared/config/topology_example.json --mode flooding
```

Mientras no exista la infraestructura de sockets de la Fase 3, este modo valida el arranque, la lectura de vecinos y la generación de descubrimiento sin transmitir por la red. Al integrarse `socket_manager.py`, los paquetes pendientes se entregarán al proceso de forwarding.

## Pruebas

Las pruebas unitarias verifican el control de TTL, el rechazo de duplicados, la exclusión del emisor, la inmutabilidad del paquete original, la construcción y recepción de HELLO, la medición de retardo, la caída por timeout, la interfaz del algoritmo y la ejecución standalone. También se ejecutan las pruebas de Dijkstra para detectar regresiones.

```bash
python -m pytest tests/test_flooding.py -q
python -m pytest tests/ -q
```
