"""Formato del Link State Packet (LSP) — ver PROTOCOLO.md §info (LSP).

Payload canónico que se EMITE:

    {"origin": "10.0.0.1:5000", "seq": 7, "age_s": 0,
     "neighbors": [{"id": "10.0.0.2:5000", "weight": 4.8}]}

Al RECIBIR se aceptan además variantes equivalentes de otras implementaciones
(``sequence`` en vez de ``seq``, ``links`` en vez de ``neighbors``,
``node``/``node_id``/``cost``, un dict ``{dirección: costo}``, o el payload como
texto JSON). La identidad lógica es ``(origin, seq)``, no el ``msg_id``.
"""

from __future__ import annotations

import json

# Un seq muy por debajo del conocido es la señal inequívoca de un contador
# reiniciado (PROTOCOLO.md §Extensión: reinicio de un nodo).
SEQ_RESET_THRESHOLD = 16


def build_lsp(origin: str, seq: int, neighbors: list, age_s: float = 0) -> dict:
    """Arma el payload de un LSP a partir de los enlaces del nodo."""

    if not isinstance(origin, str) or not origin:
        raise ValueError("El LSP necesita un origin válido")
    if not isinstance(seq, int) or isinstance(seq, bool):
        raise ValueError("El seq del LSP debe ser un entero")

    links = []
    for neighbor in neighbors:
        link_id = neighbor.get("id", neighbor.get("node_id"))
        links.append({"id": link_id, "weight": neighbor["weight"]})
    return {"origin": origin, "seq": seq, "age_s": age_s, "neighbors": links}


def _coerce_links(raw) -> list:
    if isinstance(raw, dict):
        return [{"id": key, "weight": value} for key, value in raw.items()]
    links = []
    for link in raw or []:
        if not isinstance(link, dict):
            raise ValueError("Cada enlace del LSP debe ser un objeto")
        link_id = link.get("id", link.get("node", link.get("node_id")))
        weight = link.get("weight", link.get("cost"))
        links.append({"id": link_id, "weight": weight})
    return links


def parse_lsp(payload) -> dict:
    """Valida un LSP recibido y devuelve una copia normalizada."""

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as error:
            raise ValueError(f"LSP como texto no es JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("El payload del LSP debe ser un objeto")

    origin = payload.get("origin", payload.get("node_id"))
    seq = payload.get("seq", payload.get("sequence"))
    raw_neighbors = payload.get("neighbors", payload.get("links"))
    age_s = payload.get("age_s", 0)

    if not isinstance(origin, str) or not origin:
        raise ValueError("El LSP trae un origin inválido")
    if not isinstance(seq, int) or isinstance(seq, bool):
        raise ValueError("El LSP trae un seq inválido")
    if raw_neighbors is None or isinstance(raw_neighbors, (str, int, float)):
        raise ValueError("Los enlaces del LSP deben venir en lista o dict")

    neighbors = _coerce_links(raw_neighbors)
    for link in neighbors:
        if not isinstance(link["id"], str) or not link["id"]:
            raise ValueError("Un enlace del LSP no trae id válido")
        if not isinstance(link["weight"], (int, float)) or isinstance(link["weight"], bool):
            raise ValueError("Un enlace del LSP no trae weight numérico")

    return {"origin": origin, "seq": seq, "age_s": age_s, "neighbors": neighbors}


def is_newer(existing_lsp: dict | None, incoming_lsp: dict) -> bool:
    """Indica si ``incoming_lsp`` reemplaza al guardado para ese origen."""

    if existing_lsp is None:
        return True
    if incoming_lsp["seq"] > existing_lsp["seq"]:
        return True
    # Contador reiniciado: aceptar aunque el seq sea mucho menor.
    if existing_lsp["seq"] - incoming_lsp["seq"] > SEQ_RESET_THRESHOLD:
        return True
    return False
