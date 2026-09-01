"""
DUEÑO: EA (Ernesto Ascencio) - Fase 3 (Infraestructura de red)

Encargado de abrir el socket del nodo, escuchar conexiones/paquetes entrantes
y exponer un método para enviar paquetes a otro nodo (por IP:puerto).

TODO (EA):
- [ ] Clase SocketManager(ip, port)
- [ ] Método start_listening(on_packet_received: callable) -> corre en su propio hilo
- [ ] Método send(to_ip, to_port, packet: dict) -> usa shared/protocol.serialize()
- [ ] Manejo de errores de conexión (vecino caído, timeout, etc.)
- [ ] Método stop() para cerrar el socket limpiamente
"""

class SocketManager:
    def __init__(self, ip: str, port: int):
        raise NotImplementedError

    def start_listening(self, on_packet_received):
        raise NotImplementedError

    def send(self, to_ip: str, to_port: int, packet: dict):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
