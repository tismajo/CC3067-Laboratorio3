# Link State Routing

## Propósito

Link State Routing (LSR) combina los dos algoritmos anteriores sin reimplementar
ninguno. Cada nodo describe sus enlaces directos en un *Link State Packet* (LSP),
lo distribuye a toda la red con el módulo de Flooding y, cuando ya conoce los LSPs
de los demás, reconstruye la topología completa y corre Dijkstra sobre ella para
obtener su tabla de ruteo. Si llega un LSP más nuevo —por una caída, un enlace
nuevo o un cambio de peso— la topología se reconstruye y las rutas se recalculan.

El módulo vive en `node/algorithms/lsr/` y solo importa código ajeno: `should_forward`,
`get_forward_targets` y `decrement_ttl` de Flooding, `NeighborTable` para el estado
de vecinos, y `Topology` con `build_routing_table` de Dijkstra.

## Formato del LSP

El LSP viaja en el campo `payload` de un paquete con `proto="lsr"` y `type="info"`:

```json
{
  "proto": "lsr",
  "type": "info",
  "from": "A",
  "to": "B",
  "ttl": 8,
  "headers": [{"packet_id": "A-3"}],
  "payload": {
    "node_id": "A",
    "sequence": 3,
    "neighbors": [
      {"node_id": "B", "weight": 7},
      {"node_id": "I", "weight": 1}
    ]
  }
}
```

`node_id` es el nodo que originó el LSP y `sequence` es un contador que crece cada
vez que ese nodo detecta un cambio en sus enlaces. `build_lsp` arma el payload,
`parse_lsp` valida un LSP recibido y devuelve una copia normalizada, e `is_newer`
compara secuencias para decidir si un LSP reemplaza al que ya se tenía guardado.

El `packet_id` de los encabezados vale `"<origen>-<secuencia>"`. Esto permite que
la detección de duplicados de Flooding reconozca el mismo LSP en cualquier salto y
corte la inundación cuando ya circuló por toda la red.

## Distribución por flooding

`LinkStateRouter.broadcast_own_lsp` incrementa la secuencia, arma el LSP con los
vecinos activos según `NeighborTable`, lo guarda en la base local (`lsp_db`),
recalcula las rutas y encola una copia del paquete para cada vecino activo.

`handle_info_packet` procesa un LSP entrante en dos pasos:

1. `parse_lsp` y `on_lsp_received`: si el LSP es más nuevo que el guardado, se
   almacena y se dispara el recálculo; si es viejo o repetido, se descarta.
2. Reenvío: se aplica `should_forward` (control de TTL y duplicados) y
   `get_forward_targets`, que devuelve los vecinos activos excepto el que entregó
   el paquete. Cada copia sale con el TTL decrementado, el campo `from` puesto al
   nodo actual —el último salto— y el `to` al vecino destino. El originador real
   se conserva dentro de `payload.node_id`.

El módulo de Flooding se usa tal como quedó; LSR solo aporta el `packet_id` y la
lógica de cuándo un LSP amerita reenvío.

## Topología derivada y tabla de ruteo

`build_topology_from_lsps` recorre todos los LSPs guardados y agrega cada enlace a
una `Topology` de Dijkstra. Un enlace `(X, Y)` se incluye si `Y` no lo contradice:
si `Y` todavía no publicó su LSP se acepta el enlace anunciado por `X`, y si `Y` ya
publicó pero no lista a `X`, el enlace se descarta. Así, un nodo caído cuyo LSP
viejo sigue en la base queda aislado en cuanto sus vecinos anuncian un LSP sin él.

`recompute_routing_table` corre `build_routing_table` de Dijkstra sobre esa
topología y guarda el resultado en `routing_table` (`{destino: siguiente_salto}`),
que es el atributo que `forwarding.py` sincroniza hacia la `RoutingTable` compartida
mediante `get_next_hop`.

## Actualización ante cambios

- **LSP más nuevo:** `on_lsp_received` compara secuencias con `is_newer`, reemplaza
  el LSP y recalcula. Los LSPs viejos o duplicados no alteran el estado.
- **Vecino caído o recuperado:** `handle_neighbor_down` y `handle_neighbor_up`
  actualizan `NeighborTable` y llaman a `broadcast_own_lsp`, de modo que el nodo
  publica un LSP nuevo con la lista de enlaces corregida y la red converge.

## Modo standalone

```bash
python -m node.main --config shared/config/topology_example.json --mode lsr
```

Sin sockets, el nodo solo conoce sus propios enlaces, así que imprime su LSP y la
tabla de ruteo derivada de él (los vecinos directos):

```text
LSP de A (seq 1)
B	7
I	1
C	7
Rutas desde A
destino	siguiente salto
B	B
C	C
I	I
```

Con `--live` se arma la infraestructura de la Fase 3 (`SocketManager`, `Forwarder`,
`HealthChecker`): los LSPs se propagan por la red real, la topología se completa a
medida que llegan y la tabla converge al camino de menor costo.

## Pruebas

Las pruebas cubren la construcción y lectura del LSP, la comparación por secuencia,
la reconstrucción de la topología al llegar un LSP nuevo, el recálculo de la tabla,
el descarte de LSPs viejos, el reenvío sin duplicados y excluyendo al emisor, el
reanuncio y reruteo cuando cae un vecino, y la ejecución del modo standalone.

```bash
python -m pytest tests/test_lsr.py -q
python -m pytest tests/ -q
```
