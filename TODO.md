# TODO - Laboratorio 3 (Algoritmos de Enrutamiento)

## Fase 1 Dijkstra
- [x] Modelo de topología (nodos, aristas, pesos) leído desde config
- [x] Implementación del algoritmo de Dijkstra
- [x] Modo standalone "dijkstra" (nodo ejecutándose con este algoritmo como algoritmo de red)
- [x] Pruebas unitarias de Dijkstra
- [x] Su parte del reporte: descripción del algoritmo Dijkstra y de su implementación

## Fase 2 Flooding
- [x] Descubrimiento de vecinos (paquete hello/ping)
- [x] Implementación de flooding (reenvío a todos los vecinos menos el emisor, control de TTL y duplicados)
- [x] Modo standalone "flooding" (nodo ejecutándose con este algoritmo como algoritmo de red)
- [x] Pruebas unitarias de Flooding
- [x] Su parte del reporte: descripción del algoritmo Flooding y de su implementación

## Fase 3 Infraestructura de red
- [x] Manejo de sockets (envío/recepción de paquetes)
- [x] Serialización/deserialización de paquetes según el protocolo JSON
- [x] Separación en hilos/procesos paralelos: forwarding y routing
- [x] Manejo genérico de paquetes entrantes/salientes (data, info, hello) a nivel forwarding
- [x] Chequeo de salud de vecinos (health check)
- [x] Su parte del reporte: descripción de la arquitectura de red (sockets, hilos, protocolo)

## Fase 4 Link State Routing (una vez existan Dijkstra y Flooding)
- [x] Formato del LSP (Link State Packet) dentro del `payload`
- [x] Uso del módulo de Flooding (ya terminado por LDM) para inundar LSPs, sin modificarlo
- [x] Uso del módulo de Dijkstra (ya terminado por MJ) para calcular tablas, sin modificarlo
- [x] Lógica de actualización de tablas al recibir nuevos LSPs
- [x] Modo standalone "lsr"
- [x] Su parte del reporte: descripción de Link State Routing y de su implementación, encabezado, ortografía y formato general del documento
