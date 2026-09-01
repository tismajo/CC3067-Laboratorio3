# Laboratorio 3 — Algoritmos de Enrutamiento (Dijkstra, Flooding, LSR)

## Estructura del proyecto

```
lab3-routing/
├── shared/
│   ├── protocol.py              # EA - formato del paquete JSON (build/serialize/parse)
│   └── config/
│       └── topology_example.json
├── node/
│   ├── main.py                  # EA - entry point: levanta el nodo en modo dijkstra|flooding|lsr
│   ├── network/                 # EA - infraestructura (Fase 3)
│   │   ├── socket_manager.py
│   │   ├── forwarding.py
│   │   └── health_check.py
│   ├── routing/
│   │   └── routing_table.py     # EA - tabla de ruteo compartida (thread-safe)
│   └── algorithms/
│       ├── dijkstra/            # MJ (Fase 1)
│       │   ├── topology.py
│       │   └── dijkstra.py
│       ├── flooding/            # LDM (Fase 2)
│       │   ├── neighbor_discovery.py
│       │   └── flooding.py
│       └── lsr/                 # HDB (Fase 4, usa dijkstra + flooding ya terminados)
│           ├── lsp.py
│           └── link_state.py
├── tests/                       # una por módulo, mismo dueño que el módulo
├── requirements.txt
└── README.md
```

Cada carpeta bajo `node/algorithms/` y `node/network/` tiene **un solo dueño**.
Nadie edita el código de otro módulo; si una fase depende del módulo de otra
persona, se usa como ya quedó definido en `shared/protocol.py` (Fase 0), sin
modificarlo directamente.

## Orden de trabajo (ver TODO.md del grupo para el detalle fase por fase)

1. **Fase 1 — MJ:** `node/algorithms/dijkstra/`
2. **Fase 2 — LDM:** `node/algorithms/flooding/`
3. **Fase 3 — EA:** `shared/protocol.py`, `node/network/`, `node/routing/`, `node/main.py`
4. **Fase 4 — HDB:** `node/algorithms/lsr/` (empieza cuando Dijkstra y Flooding ya estén listos)

## Instrucciones por persona (en Python)

### MJ — Dijkstra (`node/algorithms/dijkstra/`)
- Implementar `topology.py`: clase `Topology` con nodos y aristas con peso,
  cargable desde JSON (`Topology.from_json`).
- Implementar `dijkstra.py`: `shortest_paths(topology, source)` y
  `build_routing_table(topology, source)`.
- **Importante:** este módulo no debe importar nada de `node/network/` ni
  usar sockets. Debe ser puro (input: `Topology` + nodo origen, output: tabla
  de ruteo) para poder testearlo con `pytest` y para que HDB lo reutilice
  dentro de LSR sin cambios.
- Escribir `tests/test_dijkstra.py`.
- El nodo debe poder correr en modo standalone: `python -m node.main --mode dijkstra`.

### LDM — Flooding (`node/algorithms/flooding/`)
- Implementar `neighbor_discovery.py`: clase `NeighborTable` que se actualiza
  con paquetes HELLO/PING (delay, estado activo/caído).
- Implementar `flooding.py`: `should_forward`, `get_forward_targets`,
  `decrement_ttl`. Debe controlar TTL y evitar reenviar paquetes duplicados.
- **Importante:** tampoco debe usar sockets directamente; recibe/regresa
  paquetes como `dict` para que `forwarding.py` (de EA) sea quien realmente
  envíe por la red, y para que HDB lo reutilice dentro de LSR sin cambios.
- Escribir `tests/test_flooding.py`.
- El nodo debe poder correr en modo standalone: `python -m node.main --mode flooding`.

### EA — Infraestructura de red (`shared/protocol.py`, `node/network/`, `node/routing/`, `node/main.py`)
- `shared/protocol.py`: definir `build_packet`, `serialize`, `deserialize`
  según el formato acordado en la Fase 0. Este archivo lo usan todos.
- `node/network/socket_manager.py`: abrir/escuchar el socket del nodo y
  enviar paquetes a otro nodo por IP:puerto.
- `node/network/forwarding.py`: lógica de forwarding (mensajes de usuario,
  paquetes de info, hello/ping), corriendo en su propio hilo.
- `node/network/health_check.py`: ping periódico a vecinos, detectar
  caídas/recuperaciones.
- `node/routing/routing_table.py`: tabla de ruteo compartida y thread-safe
  entre el hilo de routing y el de forwarding.
- `node/main.py`: entry point que arma todo lo anterior según `--mode`.

### HDB — Link State Routing (`node/algorithms/lsr/`)
- Empieza esta fase cuando MJ y LDM ya tengan Dijkstra y Flooding listos
  (los usa, no los reimplementa ni los modifica).
- `lsp.py`: formato del LSP (Link State Packet), `build_lsp`, `parse_lsp`,
  `is_newer` (por número de secuencia).
- `link_state.py`: clase `LinkStateRouter` que:
  1. Genera su propio LSP y lo distribuye con el `flooding.py` de LDM.
  2. Recibe LSPs de los demás y arma una `Topology` (la clase de MJ) con
     toda la red.
  3. Corre `dijkstra.build_routing_table` (de MJ) sobre esa topología para
     obtener su tabla de ruteo.
  4. Si llega un LSP más nuevo, reconstruye la topología y recalcula.
- Escribir `tests/test_lsr.py`.
- El nodo debe poder correr en modo: `python -m node.main --mode lsr`.

## Cómo correr (una vez implementado)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

pytest tests/

python -m node.main --config shared/config/topology_example.json --mode dijkstra
python -m node.main --config shared/config/topology_example.json --mode flooding
python -m node.main --config shared/config/topology_example.json --mode lsr
```
