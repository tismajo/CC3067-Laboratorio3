# TODO - Laboratorio 3 (Algoritmos de Enrutamiento)

## Grupo
- **MJ** = María José Girón
- **LDM** = Leonardo Dufrey Mejía
- **EA** = Ernesto Ascencio
- **HDB** = Hugo Daniel Barillas
---

## Fase 1 — MJ: Dijkstra (completa, de inicio a fin)
- [ ] Modelo de topología (nodos, aristas, pesos) leído desde config
- [ ] Implementación del algoritmo de Dijkstra
- [ ] Modo standalone "dijkstra" (nodo ejecutándose con este algoritmo como algoritmo de red)
- [ ] Pruebas unitarias de Dijkstra
- [ ] Su parte del reporte: descripción del algoritmo Dijkstra y de su implementación

## Fase 2 — LDM: Flooding (completa, de inicio a fin)
- [ ] Descubrimiento de vecinos (paquete hello/ping)
- [ ] Implementación de flooding (reenvío a todos los vecinos menos el emisor, control de TTL y duplicados)
- [ ] Modo standalone "flooding" (nodo ejecutándose con este algoritmo como algoritmo de red)
- [ ] Pruebas unitarias de Flooding
- [ ] Su parte del reporte: descripción del algoritmo Flooding y de su implementación

## Fase 3 — EA: Infraestructura de red (completa, de inicio a fin)
- [ ] Manejo de sockets (envío/recepción de paquetes)
- [ ] Serialización/deserialización de paquetes según el protocolo JSON
- [ ] Separación en hilos/procesos paralelos: forwarding y routing
- [ ] Manejo genérico de paquetes entrantes/salientes (data, info, hello) a nivel forwarding
- [ ] Chequeo de salud de vecinos (health check)
- [ ] Su parte del reporte: descripción de la arquitectura de red (sockets, hilos, protocolo)

## Fase 4 — HDB: Link State Routing (completa, de inicio a fin, una vez existan Dijkstra y Flooding)
- [ ] Formato del LSP (Link State Packet) dentro del `payload`
- [ ] Uso del módulo de Flooding (ya terminado por LDM) para inundar LSPs, sin modificarlo
- [ ] Uso del módulo de Dijkstra (ya terminado por MJ) para calcular tablas, sin modificarlo
- [ ] Lógica de actualización de tablas al recibir nuevos LSPs
- [ ] Modo standalone "lsr"
- [ ] Su parte del reporte: descripción de Link State Routing y de su implementación, encabezado, ortografía y formato general del documento
