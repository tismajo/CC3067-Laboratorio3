"""
Fase 3 (Infraestructura de red)

Abre el socket del nodo, escucha paquetes entrantes y envía a otro nodo por
IP:puerto.

Transporte (ver PROTOCOLO.md §Transporte): TCP, UTF-8, NDJSON — un objeto JSON
por línea terminado en ``\\n``. El receptor acumula bytes hasta el delimitador y
procesa cada línea. Una línea mayor a ``MAX_LINE_BYTES`` se descarta y se
registra. Se puede abrir una conexión por envío o mantener una por vecino.
"""

import logging
import socket
import threading

from shared.protocol import MAX_LINE_BYTES, serialize

logger = logging.getLogger("socket")

CONNECT_TIMEOUT_SECONDS = 5
# Escuchar en todas las interfaces: el `ip` del config es solo la identidad
# anunciada, no siempre una dirección asignable localmente.
LISTEN_HOST = "0.0.0.0"


class NeighborUnreachableError(Exception):
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
        self._server_socket.bind((LISTEN_HOST, self.port))
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
            buffer = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self._deliver(line, addr, on_packet_received)
                if len(buffer) > MAX_LINE_BYTES:
                    logger.warning("Línea > %d bytes de %s: descartada", MAX_LINE_BYTES, addr)
                    buffer = b""
            self._deliver(buffer, addr, on_packet_received)

    @staticmethod
    def _deliver(line: bytes, addr, on_packet_received) -> None:
        line = line.strip()
        if not line:
            return
        if len(line) > MAX_LINE_BYTES:
            logger.warning("Línea > %d bytes de %s: descartada", MAX_LINE_BYTES, addr)
            return
        on_packet_received(line, addr)

    def send(self, to_ip: str, to_port: int, packet: dict) -> None:
        raw = serialize(packet) + b"\n"
        try:
            with socket.create_connection(
                (to_ip, to_port), timeout=CONNECT_TIMEOUT_SECONDS
            ) as conn:
                conn.sendall(raw)
        except OSError as error:
            raise NeighborUnreachableError(to_ip, to_port, error) from error

    def stop(self) -> None:
        self._running = False
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
