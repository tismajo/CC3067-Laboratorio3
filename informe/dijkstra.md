# Algoritmo de Dijkstra

## Propósito

Dijkstra calcula el camino de menor costo desde un nodo de origen hacia los demás nodos de una red. El cálculo usa una topología completa con nodos, enlaces y el peso de cada enlace. En este laboratorio, el peso representa el costo de atravesar una conexión.

El algoritmo requiere pesos no negativos. La implementación rechaza un enlace con peso negativo para evitar resultados incorrectos.

## Funcionamiento

El cálculo comienza con costo cero para el origen y costo infinito para los demás nodos. Una cola de prioridad selecciona el nodo pendiente con menor costo conocido. Después se revisan sus vecinos y se actualiza una ruta cuando el nuevo costo es menor que el anterior.

Cada actualización conserva el primer salto desde el origen. Ese dato permite reenviar un paquete sin guardar la ruta completa. El proceso termina cuando la cola queda vacía.

Para cada destino, `shortest_paths` devuelve el costo total y el siguiente salto. Los destinos aislados conservan costo infinito y no tienen siguiente salto. `build_routing_table` elimina esos destinos y produce el formato que consumirá el módulo de forwarding:

```python
{
    "B": "C",
    "C": "C",
}
```

En este ejemplo, un paquete dirigido a `B` debe salir primero por `C`. Un paquete dirigido a `C` se entrega directamente a ese vecino.

Con una cola de prioridad, el tiempo de ejecución es `O((V + E) log V)`, donde `V` es la cantidad de nodos y `E` es la cantidad de enlaces. La memoria utilizada es `O(V + E)`.

## Modelo de topología

La clase `Topology` guarda una lista de adyacencia no dirigida. `add_edge` registra el enlace en ambos sentidos y `get_neighbors` devuelve los vecinos con sus pesos. `mark_down` elimina un nodo y todas sus conexiones, lo que permite recalcular las rutas después de una caída.

`Topology.from_json` acepta una sección con este formato:

```json
{
  "nodes": ["A", "B", "C"],
  "edges": [
    {"node_a": "A", "node_b": "B", "weight": 4},
    {"node_a": "A", "node_b": "C", "weight": 1},
    {"node_a": "C", "node_b": "B", "weight": 2}
  ]
}
```

El método también puede recibir el archivo completo de configuración. En ese caso, toma los datos incluidos bajo la clave `topology`. Esta decisión permite usar el mismo modelo en el modo estático y, más adelante, con la topología construida por Link State Routing.

## Modo standalone

El punto de entrada carga el nodo de origen y la topología desde el archivo JSON. Luego calcula e imprime el costo y el siguiente salto de cada destino:

```powershell
python -m node.main --config shared/config/topology_example.json --mode dijkstra
```

La configuración incluida produce esta salida:

```text
Rutas desde A
destino costo   siguiente salto
B       7       B
C       7       C
I       1       I
```

Este modo no abre sockets. Su función durante la fase 1 es comprobar el cálculo estático antes de conectarlo con la infraestructura de red.

## Pruebas

Las pruebas cubren la carga de una topología, una ruta indirecta más barata, un nodo inalcanzable, el recálculo después de una caída y la ejecución del modo standalone.

```powershell
..\.venv\Scripts\python.exe -m pytest tests\test_dijkstra.py -q
```
