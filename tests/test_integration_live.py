"""Prueba de integración: 3 nodos reales (A—B—C) en modo LSR sobre sockets.

Levanta los procesos en orden inverso (C, B, A) para ejercitar el arranque con
vecinos que todavía no escuchan, espera la convergencia y verifica que un
mensaje de A a C se entrega pasando por B (no hay enlace directo A—C).

Es lenta (~20 s) a propósito: es el único test que cubre el camino multiproceso.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_config(path: Path, node_id: str, port: int, neighbors: list) -> Path:
    path.write_text(
        json.dumps(
            {
                "node_id": node_id,
                "ip": "127.0.0.1",
                "port": port,
                "neighbors": neighbors,
            }
        ),
        encoding="utf-8",
    )
    return path


class LiveNode:
    def __init__(self, config_path: Path):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "node.main", "--config", str(config_path),
             "--mode", "lsr", "--live"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        self.output = []
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()

    def _drain(self):
        for line in self.proc.stdout:
            self.output.append(line)

    def send(self, text: str):
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def saw(self, needle: str) -> bool:
        return any(needle in line for line in self.output)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def test_message_from_a_reaches_c_through_b(tmp_path):
    ports = {name: _free_port() for name in ("A", "B", "C")}

    def addr(name):
        return {"node_id": name, "ip": "127.0.0.1", "port": ports[name], "weight": 1}

    configs = {
        "A": _write_config(tmp_path / "A.json", "A", ports["A"], [addr("B")]),
        "B": _write_config(tmp_path / "B.json", "B", ports["B"], [addr("A"), addr("C")]),
        "C": _write_config(tmp_path / "C.json", "C", ports["C"], [addr("B")]),
    }

    nodes = {}
    try:
        for name in ("C", "B", "A"):  # orden inverso: A y B arrancan sin peers vivos
            nodes[name] = LiveNode(configs[name])
            time.sleep(0.5)

        for name, node in nodes.items():
            assert node.proc.poll() is None, f"el nodo {name} murió al arrancar"

        deadline = time.time() + 45
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            nodes["A"].send(f"C: ping-{attempt}")
            time.sleep(3)
            if nodes["C"].saw(f"ping-{attempt}"):
                break
        else:
            raise AssertionError("el mensaje de A nunca llegó a C pasando por B")

        assert nodes["C"].saw("mensaje de A")
    finally:
        for node in nodes.values():
            node.stop()
