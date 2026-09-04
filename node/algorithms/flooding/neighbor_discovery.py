"""Descubrimiento y estado de vecinos directos.

No abre sockets. Construye paquetes ``hello`` y actualiza una tabla en memoria a
partir de ``hello``/``echo`` recibidos; la infraestructura de red decide cuándo
enviarlos.

RTT (ver PROTOCOLO.md §hello/echo): el ``hello`` lleva ``t0`` en un header. El
vecino responde un ``echo`` con el MISMO ``t0``. Quien envió el ``hello`` calcula
``RTT = ahora - t0`` contra su propio reloj, sin necesidad de relojes sincronizados.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable

from shared import constants as c
from shared.protocol import (
    T0_HEADER,
    build_message,
    get_header,
    make_hello_payload,
    normalize_addr,
)


def _addr_parts(address: str, default_port: int) -> tuple[str, int]:
    address = normalize_addr(address, default_port)
    host, _, port = address.partition(":")
    try:
        return host, int(port)
    except ValueError:
        return host, default_port


class NeighborTable:
    """Tabla thread-safe de vecinos. La identidad es la dirección ``IP:puerto``."""

    def __init__(
        self,
        initial_neighbors: Iterable[dict] | None = None,
        timeout: float = 15.0,
        clock: Callable[[], float] | None = None,
    ):
        if timeout <= 0:
            raise ValueError("El timeout debe ser mayor que cero")

        self.timeout = float(timeout)
        self._clock = clock or time.time
        self._neighbors: dict[str, dict] = {}
        self._lock = threading.RLock()

        for neighbor in initial_neighbors or []:
            self._store_initial_neighbor(neighbor)

    def _store_initial_neighbor(self, neighbor: dict) -> None:
        node_id = neighbor.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Cada vecino debe tener un node_id válido")

        entry = dict(neighbor)
        entry.update(
            {
                "node_id": node_id,
                "active": bool(neighbor.get("active", False)),
                "delay": neighbor.get("delay"),
                "last_seen": neighbor.get("last_seen"),
            }
        )
        self._neighbors[node_id] = entry

    def build_hello_packet(
        self,
        self_info: dict,
        target: str,
        timestamp: float | None = None,
    ) -> dict:
        """Construye un ``hello`` dirigido a un vecino."""

        node_id = self_info.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("self_info debe incluir un node_id válido")
        if not isinstance(target, str) or not target:
            raise ValueError("target debe ser un node_id válido")

        _, listen_port = _addr_parts(node_id, self_info.get("port", 5000))
        return build_message(
            proto=self_info.get("proto", c.PROTO_FLOODING),
            type_=c.TYPE_HELLO,
            src=node_id,
            dst=target,
            payload=make_hello_payload(self_info.get("port", listen_port)),
            ttl=c.HELLO_TTL,
            t0=self._clock() if timestamp is None else float(timestamp),
        )

    def build_hello_packets(self, self_info: dict) -> list[dict]:
        return [
            self.build_hello_packet(self_info, neighbor["node_id"])
            for neighbor in self.get_neighbors()
        ]

    def on_hello_received(self, packet: dict) -> dict:
        """Marca activo al emisor de un ``hello``. No mide RTT (llega con el echo)."""

        if packet.get(c.FIELD_TYPE) != c.TYPE_HELLO:
            raise ValueError("Se esperaba un paquete HELLO")
        return self._touch(packet, delay=None)

    def on_echo_received(self, packet: dict) -> dict:
        """Procesa la respuesta ``echo`` a un ``hello`` propio: mide el RTT."""

        if packet.get(c.FIELD_TYPE) != c.TYPE_ECHO:
            raise ValueError("Se esperaba un paquete ECHO")
        now = self._clock()
        t0 = get_header(packet, T0_HEADER)
        delay = None
        if isinstance(t0, (int, float)) and not isinstance(t0, bool):
            delay = max(0.0, now - float(t0))
        return self._touch(packet, delay=delay)

    def _touch(self, packet: dict, delay: float | None) -> dict:
        node_id = packet.get(c.FIELD_FROM)
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("El paquete no contiene un emisor válido")

        payload = packet.get(c.FIELD_PAYLOAD) or {}
        if not isinstance(payload, dict):
            raise ValueError("El payload de hello/echo debe ser un objeto")

        host, default_port = _addr_parts(node_id, 5000)
        listen_port = payload.get("listen_port")
        now = self._clock()
        with self._lock:
            entry = self._neighbors.setdefault(node_id, {"node_id": node_id})
            entry["ip"] = host
            entry["port"] = listen_port if isinstance(listen_port, int) else default_port
            entry["active"] = True
            entry["last_seen"] = now
            if delay is not None:
                entry["delay"] = delay
            return dict(entry)

    def mark_up(self, node_id: str, delay: float | None = None) -> None:
        with self._lock:
            entry = self._neighbors.setdefault(node_id, {"node_id": node_id})
            entry["active"] = True
            entry["last_seen"] = self._clock()
            if delay is not None:
                entry["delay"] = float(delay)

    def mark_down(self, node_id: str) -> None:
        with self._lock:
            if node_id in self._neighbors:
                self._neighbors[node_id]["active"] = False

    def expire_stale(self, now: float | None = None) -> list[str]:
        current = self._clock() if now is None else float(now)
        expired = []
        with self._lock:
            for node_id, entry in self._neighbors.items():
                last_seen = entry.get("last_seen")
                if (
                    entry.get("active")
                    and last_seen is not None
                    and current - last_seen >= self.timeout
                ):
                    entry["active"] = False
                    expired.append(node_id)
        return expired

    def get_neighbor(self, node_id: str) -> dict | None:
        with self._lock:
            entry = self._neighbors.get(node_id)
            return dict(entry) if entry is not None else None

    def get_neighbors(self) -> list[dict]:
        with self._lock:
            return [dict(entry) for entry in self._neighbors.values()]

    def get_active_neighbors(self) -> list[dict]:
        with self._lock:
            return [
                dict(entry)
                for entry in self._neighbors.values()
                if entry.get("active")
            ]
