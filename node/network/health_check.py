"""
Fase 3 (Infraestructura de red)

Es agnóstico del algoritmo de ruteo: quien conecta `on_status_change` con
`RoutingAlgorithm.handle_neighbor_up/down` es node/main.py.
"""

from __future__ import annotations

import threading

from node.network.socket_manager import NeighborUnreachableError

DEFAULT_MAX_FAILURES = 3


class HealthChecker:
    def __init__(
        self,
        neighbors: list,
        send_ping,
        on_status_change=None,
        interval_seconds: float = 5,
        max_failures: int = DEFAULT_MAX_FAILURES,
        on_tick=None,
    ):
        self.neighbors = list(neighbors)
        self._send_ping = send_ping
        self._on_status_change = on_status_change
        self._on_tick = on_tick
        self.interval_seconds = interval_seconds
        self.max_failures = max_failures

        self._failures = {neighbor["node_id"]: 0 for neighbor in self.neighbors}
        self._is_up = {neighbor["node_id"]: True for neighbor in self.neighbors}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            # ponytail: except amplio a propósito. Un fallo en check_once o en
            # on_tick no debe matar el hilo: sin heartbeat el nodo deja de
            # detectar caídas y de re-anunciar su LSP para siempre.
            try:
                self.check_once()
                if self._on_tick is not None:
                    self._on_tick()
            except Exception as error:  # noqa: BLE001
                print(f"[health-check] tick falló: {error}")

    def check_once(self) -> None:
        for neighbor in self.neighbors:
            node_id = neighbor["node_id"]
            try:
                self._send_ping(neighbor)
            except NeighborUnreachableError:
                self._record_failure(node_id)
            else:
                self._record_success(node_id)

    def _record_failure(self, node_id: str) -> None:
        self._failures[node_id] += 1
        if self._is_up[node_id] and self._failures[node_id] >= self.max_failures:
            self._is_up[node_id] = False
            if self._on_status_change is not None:
                self._on_status_change(node_id, False)

    def _record_success(self, node_id: str) -> None:
        self._failures[node_id] = 0
        if not self._is_up[node_id]:
            self._is_up[node_id] = True
            if self._on_status_change is not None:
                self._on_status_change(node_id, True)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
