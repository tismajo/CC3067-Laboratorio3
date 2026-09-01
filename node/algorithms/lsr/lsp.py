"""
DUEÑO: HDB (Hugo Daniel Barillas) - Fase 4 (Link State Routing)
DEPENDE DE: shared/protocol.py (EA), ya terminado antes de empezar esta fase

Formato del Link State Packet (LSP) que cada nodo genera y distribuye por
flooding para que todos conozcan la topología completa.

TODO (HDB):
- [ ] Definir la estructura del LSP: node_id, secuencia/timestamp, lista de
      (vecino, peso) del nodo que lo generó
- [ ] build_lsp(node_id, sequence, neighbors) -> dict (contenido para el
      campo "payload" de un paquete con proto="lsr", type="info")
- [ ] parse_lsp(payload) -> dict con la info anterior
- [ ] Lógica para saber si un LSP recibido es más nuevo que el que ya se tiene
      (comparar número de secuencia) y así descartar LSPs viejos/duplicados
"""

def build_lsp(node_id: str, sequence: int, neighbors: list) -> dict:
    raise NotImplementedError


def parse_lsp(payload) -> dict:
    raise NotImplementedError


def is_newer(existing_lsp: dict, incoming_lsp: dict) -> bool:
    raise NotImplementedError
