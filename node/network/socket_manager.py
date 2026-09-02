"""
Fase 3 (Infraestructura de red)

Encargado de abrir el socket del nodo, escuchar conexiones/paquetes entrantes
y exponer un método para enviar paquetes a otro nodo (por IP:puerto).

Un paquete = una conexión TCP: connect -> enviar JSON -> cerrar. No se
mantienen conexiones persistentes entre nodos.
"""

import socket
import threading

from shared.protocol import serialize

CONNECT_TIMEOUT_SECONDS = 5


class NeighborUnreachableError(Exception):
    """Se lanza cuando send() no logra conectar o entregar el paquete."""

    def __init__(self, to_ip: str, to_port: int, cause: Exception):
        super().__init__(f"No se pudo contactar a {to_ip}:{to_port}: {cause}")
        self.to_ip = to_ip
        self.to_port = to_port
        self.__cause__ = cause


class SocketManager:
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self._server_socket: socket.socket | None = None
        self._listen_thread: threading.Thread | None = None
        self._running = False

    def start_listening(self, on_packet_received) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.ip, self.port))
        self._server_socket.listen()
        self._running = True

        self._listen_thread = threading.Thread(
            target=self._accept_loop,
            args=(on_packet_received,),
            daemon=True,
        )
        self._listen_thread.start()

    def _accept_loop(self, on_packet_received) -> None:
        while self._running:
            try:
                conn, addr = self._server_socket.accept()
            except OSError:
                break
            threading.Thread(
                target=self._handle_connection,
                args=(conn, addr, on_packet_received),
                daemon=True,
            ).start()

    def _handle_connection(self, conn: socket.socket, addr, on_packet_received) -> None:
        with conn:
            chunks = []
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            if chunks:
                raw = b"".join(chunks).decode("utf-8")
                on_packet_received(raw, addr)

    def send(self, to_ip: str, to_port: int, packet: dict) -> None:
        raw = serialize(packet)
        try:
            with socket.create_connection(
                (to_ip, to_port), timeout=CONNECT_TIMEOUT_SECONDS
            ) as conn:
                conn.sendall(raw.encode("utf-8"))
        except OSError as error:
            raise NeighborUnreachableError(to_ip, to_port, error) from error

    def stop(self) -> None:
        self._running = False
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
