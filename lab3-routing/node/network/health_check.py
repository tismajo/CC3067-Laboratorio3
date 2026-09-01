"""
DUEÑO: EA (Ernesto Ascencio) - Fase 3 (Infraestructura de red)

TODO (EA):
- [ ] Enviar HELLO periódico (shared.protocol.build_packet con c.TYPE_HELLO) a cada vecino
- [ ] Marcar vecino como "caído" si no responde tras N intentos -> algorithm.handle_neighbor_down
- [ ] Marcar vecino como "recuperado" cuando vuelva a responder -> algorithm.handle_neighbor_up
"""

from shared import constants as c


class HealthChecker:
    def __init__(self, neighbors, algorithm, interval_seconds=5):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
