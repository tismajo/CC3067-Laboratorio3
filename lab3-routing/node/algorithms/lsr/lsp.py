"""
DUEÑO: HDB (Hugo Daniel Barillas) - Fase 4 (Link State Routing)

El LSP va dentro del campo "payload" de un paquete con
proto=c.PROTO_LSR, type=c.TYPE_INFO (ver shared/constants.py).

TODO (HDB):
- [ ] Definir la estructura del LSP: node_id, sequence, neighbors (lista de {node_id, weight})
- [ ] build_lsp(node_id, sequence, neighbors) -> dict (para el "payload")
- [ ] parse_lsp(payload) -> dict
- [ ] is_newer(existing_lsp, incoming_lsp) -> bool (compara "sequence")
"""

def build_lsp(node_id: str, sequence: int, neighbors: list) -> dict:
    raise NotImplementedError


def parse_lsp(payload) -> dict:
    raise NotImplementedError


def is_newer(existing_lsp: dict, incoming_lsp: dict) -> bool:
    raise NotImplementedError
