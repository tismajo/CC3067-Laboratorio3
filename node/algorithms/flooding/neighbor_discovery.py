"""Descubrimiento y estado de vecinos directos para Flooding.

Este módulo no abre sockets. Construye paquetes HELLO y actualiza una tabla
en memoria a partir de paquetes recibidos; la infraestructura de red decide
cuándo y cómo enviarlos.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable

from shared import constants as c
from shared.protocol import build_packet


class NeighborTable:
    """Tabla thread-safe de vecinos configurados o descubiertos.

    Los vecinos configurados empiezan inactivos hasta recibir un HELLO. Esto
    evita reenviar tráfico por un enlace que todavía no se ha comprobado.
    ``expire_stale`` permite al health check marcar caídas por timeout.
    """

    def __init__(
        self,
        initial_neighbors: Iterable[dict] | None = None,
        timeout: float = 15.0,
        clock: Callable[[], float] | None = None,
    ):
        if timeout <= 0:
            raise ValueError("El timeout debe ser mayor que cero")

        self.timeout = float(timeout)
        # HELLO viaja entre procesos y equipos, por lo que su timestamp debe
        # pertenecer a un reloj comparable entre hosts.
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
        """Construye un HELLO dirigido a un vecino."""

        node_id = self_info.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("self_info debe incluir un node_id válido")
        if not isinstance(target, str) or not target:
            raise ValueError("target debe ser un node_id válido")

        sent_at = self._clock() if timestamp is None else float(timestamp)
        payload = {
            "node_id": node_id,
            "ip": self_info.get("ip"),
            "port": self_info.get("port"),
            "sent_at": sent_at,
        }
        return build_packet(
            proto=c.PROTO_FLOODING,
            type_=c.TYPE_HELLO,
            from_=node_id,
            to=target,
            ttl=1,
            payload=payload,
        )

    def build_hello_packets(self, self_info: dict) -> list[dict]:
        """Construye un HELLO para cada vecino conocido."""

        return [
            self.build_hello_packet(self_info, neighbor["node_id"])
            for neighbor in self.get_neighbors()
        ]

    def on_hello_received(self, packet: dict) -> dict:
        """Marca activo al emisor de un HELLO y actualiza su retardo."""

        if packet.get(c.FIELD_TYPE) != c.TYPE_HELLO:
            raise ValueError("Se esperaba un paquete HELLO")

        node_id = packet.get(c.FIELD_FROM)
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("El paquete HELLO no contiene un emisor válido")

        payload = packet.get(c.FIELD_PAYLOAD)
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("El payload de HELLO debe ser un objeto")

        now = self._clock()
        sent_at = payload.get("sent_at")
        delay = None
        if isinstance(sent_at, (int, float)) and not isinstance(sent_at, bool):
            delay = max(0.0, now - float(sent_at))

        with self._lock:
            entry = self._neighbors.setdefault(node_id, {"node_id": node_id})
            for field in ("ip", "port"):
                if payload.get(field) is not None:
                    entry[field] = payload[field]
            entry.update(
                {
                    "active": True,
                    "delay": delay,
                    "last_seen": now,
                }
            )
            return dict(entry)

    def mark_up(self, node_id: str, delay: float | None = None) -> None:
        """Marca manualmente un vecino activo (integración con health check)."""

        with self._lock:
            entry = self._neighbors.setdefault(node_id, {"node_id": node_id})
            entry["active"] = True
            entry["last_seen"] = self._clock()
            if delay is not None:
                entry["delay"] = float(delay)

    def mark_down(self, node_id: str) -> None:
        """Marca un vecino caído sin eliminar su configuración."""

        with self._lock:
            if node_id in self._neighbors:
                self._neighbors[node_id]["active"] = False

    def expire_stale(self, now: float | None = None) -> list[str]:
        """Marca caídos los vecinos cuyo último HELLO superó el timeout."""

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
        """Devuelve una copia de un vecino o ``None`` si no existe."""

        with self._lock:
            entry = self._neighbors.get(node_id)
            return dict(entry) if entry is not None else None

    def get_neighbors(self) -> list[dict]:
        """Devuelve copias de todos los vecinos en orden de configuración."""

        with self._lock:
            return [dict(entry) for entry in self._neighbors.values()]

    def get_active_neighbors(self) -> list[dict]:
        """Devuelve copias de los vecinos cuyo enlace está activo."""

        with self._lock:
            return [
                dict(entry)
                for entry in self._neighbors.values()
                if entry.get("active")
            ]
