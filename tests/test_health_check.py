import threading

from node.network.health_check import HealthChecker
from node.network.socket_manager import NeighborUnreachableError

NEIGHBORS = [
    {"node_id": "B", "ip": "127.0.0.1", "port": 5001},
    {"node_id": "C", "ip": "127.0.0.1", "port": 5003},
]


class ScriptedPing:
    """send_ping falso: falla mientras `down` contenga el node_id del vecino."""

    def __init__(self):
        self.down = set()
        self.calls = []

    def __call__(self, neighbor):
        self.calls.append(neighbor["node_id"])
        if neighbor["node_id"] in self.down:
            raise NeighborUnreachableError(neighbor["ip"], neighbor["port"], OSError())


def test_check_once_marks_neighbor_down_after_max_failures():
    ping = ScriptedPing()
    ping.down.add("B")
    changes = []
    checker = HealthChecker(
        NEIGHBORS, send_ping=ping, on_status_change=lambda node_id, up: changes.append((node_id, up)),
        interval_seconds=0.05, max_failures=3,
    )

    checker.check_once()
    checker.check_once()
    assert changes == []
    checker.check_once()
    assert changes == [("B", False)]


def test_check_once_recovers_after_responding_again():
    ping = ScriptedPing()
    ping.down.add("B")
    changes = []
    checker = HealthChecker(
        NEIGHBORS, send_ping=ping, on_status_change=lambda node_id, up: changes.append((node_id, up)),
        interval_seconds=0.05, max_failures=2,
    )

    checker.check_once()
    checker.check_once()
    assert changes == [("B", False)]

    ping.down.discard("B")
    checker.check_once()
    assert changes == [("B", False), ("B", True)]


def test_on_tick_runs_once_per_loop_iteration():
    ticks = []
    checker = HealthChecker(
        [{"node_id": "B"}],
        send_ping=lambda neighbor: None,
        interval_seconds=0.02,
        on_tick=lambda: ticks.append(1),
    )
    checker.start()
    threading.Event().wait(0.1)
    checker.stop()

    assert len(ticks) >= 1


def test_start_runs_checks_periodically_until_stopped():
    ping = ScriptedPing()
    checker = HealthChecker(
        NEIGHBORS, send_ping=ping, interval_seconds=0.02, max_failures=99
    )

    checker.start()
    fired = threading.Event()
    threading.Timer(0.1, fired.set).start()
    fired.wait()
    checker.stop()

    calls_after_stop = len(ping.calls)
    assert calls_after_stop > 0

    threading.Event().wait(0.05)
    assert len(ping.calls) == calls_after_stop
