# Laboratorio 3 — Algoritmos de Enrutamiento (Dijkstra, Flooding, LSR)

## Estructura del proyecto

```
lab3-routing/
├── shared/
│   ├── config/
│   │   ├── protocol_schema.json     # ← EDITAR AQUÍ si hay que renombrar campos/valores
│   │   └── topology_example.json
│   ├── constants.py                 # EA (Fase 0) - carga protocol_schema.json
│   ├── protocol.py                  # EA (Fase 0) - build/serialize/deserialize/validate
│   └── interfaces.py                # EA (Fase 0) - contrato RoutingAlgorithm
├── node/
│   ├── main.py                      # EA (Fase 3)
│   ├── network/                     # EA (Fase 3)
│   │   ├── socket_manager.py
│   │   ├── forwarding.py
│   │   └── health_check.py
│   ├── routing/
│   │   └── routing_table.py         # EA (Fase 3)
│   └── algorithms/
│       ├── dijkstra/                # MJ (Fase 1)
│       │   ├── topology.py
│       │   └── dijkstra.py          # incluye DijkstraRoutingAlgorithm
│       ├── flooding/                # LDM (Fase 2)
│       │   ├── neighbor_discovery.py
│       │   └── flooding.py          # incluye FloodingRoutingAlgorithm
│       └── lsr/                     # HDB (Fase 4)
│           ├── lsp.py
│           └── link_state.py        # incluye LinkStateRouter
├── tests/
├── requirements.txt
└── README.md
```

## Fase 0 — qué es y por qué desbloquea el paralelismo

Fase 0 son 3 archivos en `shared/`, ya escritos, que MJ/LDM/EA/HDB usan
**sin tener que ponerse de acuerdo en tiempo real** mientras programan:

1. **`shared/config/protocol_schema.json`** — nombres de campos (`proto`,
   `type`, `from`, `to`, `ttl`, `headers`, `payload`) y valores válidos
   (`dijkstra|flooding|lsr`, `hello|message|info`). Si el día de la prueba
   hay que cambiar algo del esquema (otro grupo usa `"protocol"` en vez de
   `"proto"`, o se necesita un `type` nuevo), **se edita solo este archivo**.

2. **`shared/constants.py`** — lee ese JSON y expone constantes
   (`c.FIELD_PROTO`, `c.TYPE_HELLO`, etc). Todo el código del proyecto usa
   estas constantes, nunca el string literal. Así, un cambio en el JSON se
   propaga a todo el proyecto sin tocar `dijkstra.py`, `flooding.py`, ni
   `forwarding.py`. Tiene un `reload()` para releer el JSON sin reiniciar
   el proceso si hiciera falta.

3. **`shared/protocol.py`** — `build_packet`, `serialize`, `deserialize`,
   `validate_packet`, construidos sobre `constants.py`. Es el único lugar
   donde se arma o se lee un paquete; nadie más debería hacer
   `json.dumps`/`json.loads` a mano.

4. **`shared/interfaces.py`** — la clase abstracta `RoutingAlgorithm`. Este
   es el que realmente permite trabajar en paralelo: `node/main.py` y
   `node/network/forwarding.py` (de EA) solo conocen esta interfaz, nunca
   una clase concreta. Por eso EA puede construir toda la infraestructura de
   red sin esperar a que Dijkstra/Flooding/LSR existan, y MJ, LDM y HDB
   pueden implementar y testear su algoritmo de forma aislada sin esperar a
   que la infraestructura de EA esté lista. Cada algoritmo termina con una
   clase concreta que hereda de `RoutingAlgorithm`:
   `DijkstraRoutingAlgorithm`, `FloodingRoutingAlgorithm`, `LinkStateRouter`.

## Orden de trabajo

1. **Fase 0 (ya hecha, revisarla los 4 antes de empezar):** `shared/*`
2. **Fase 1 — MJ:** `node/algorithms/dijkstra/`
3. **Fase 2 — LDM:** `node/algorithms/flooding/`
4. **Fase 3 — EA:** `node/network/`, `node/routing/`, `node/main.py`
5. **Fase 4 — HDB:** `node/algorithms/lsr/` (usa Dijkstra y Flooding ya terminados, sin modificarlos)
6. **Fase 5 (todos):** pruebas conjuntas, 4 nodos, uno por persona
7. **Fase 6:** prueba en clase con el Access Point y los demás grupos

## Cómo correr (una vez implementado)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest tests/

python -m node.main --config shared/config/topology_example.json --mode dijkstra
python -m node.main --config shared/config/topology_example.json --mode flooding
python -m node.main --config shared/config/topology_example.json --mode lsr
```
