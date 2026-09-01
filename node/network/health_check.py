"""
DUEÑO: EA (Ernesto Ascencio) - Fase 3 (Infraestructura de red)

Chequeo periódico de salud de los vecinos (mencionado en las notas del
profesor: "Deberemos tener un tipo de chequeo de salud para validar que
nuestros vecinos están en pie").

TODO (EA):
- [ ] Enviar HELLO/PING periódico a cada vecino
- [ ] Marcar vecino como "caído" si no responde tras N intentos
- [ ] Marcar vecino como "recuperado" cuando vuelva a responder
- [ ] Notificar al proceso de routing cuando cambie el estado de un vecino
      (esto dispara recomputo de tabla en dijkstra/flooding/lsr)
"""

class HealthChecker:
    def __init__(self, neighbors, on_status_change=None, interval_seconds=5):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
