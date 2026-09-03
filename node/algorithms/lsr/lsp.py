"""
Fase 4 (Link State Routing)
DEPENDE DE: shared/protocol.py ya terminado antes de empezar esta fase

Formato del Link State Packet (LSP) que cada nodo genera y distribuye por
flooding para que todos conozcan la topología completa.

Un LSP describe los enlaces directos de un nodo en un instante dado:

    {
        "node_id": "A",
        "sequence": 3,
        "neighbors": [{"node_id": "B", "weight": 7}, {"node_id": "I", "weight": 1}]
    }

Este dict viaja en el campo ``payload`` de un paquete con ``proto="lsr"`` y
``type="info"``. El número de secuencia crece cada vez que el nodo detecta un
cambio en sus enlaces y sirve para descartar LSPs viejos o duplicados.
"""


def build_lsp(node_id: str, sequence: int, neighbors: list) -> dict:
    """Arma el payload de un LSP a partir de los vecinos activos del nodo."""

    if not isinstance(node_id, str) or not node_id:
        raise ValueError("El LSP necesita un node_id válido")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise ValueError("La secuencia del LSP debe ser un entero")

    links = []
    for neighbor in neighbors:
        links.append(
            {
                "node_id": neighbor["node_id"],
                "weight": neighbor["weight"],
            }
        )
    return {"node_id": node_id, "sequence": sequence, "neighbors": links}


def parse_lsp(payload) -> dict:
    """Valida un LSP recibido y devuelve una copia normalizada."""

    if not isinstance(payload, dict):
        raise ValueError("El payload del LSP debe ser un objeto")

    try:
        node_id = payload["node_id"]
        sequence = payload["sequence"]
        raw_neighbors = payload["neighbors"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"LSP incompleto: falta {error}") from error

    if not isinstance(node_id, str) or not node_id:
        raise ValueError("El LSP trae un node_id inválido")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise ValueError("El LSP trae una secuencia inválida")
    if not isinstance(raw_neighbors, list):
        raise ValueError("Los vecinos del LSP deben venir en una lista")

    neighbors = [
        {"node_id": link["node_id"], "weight": link["weight"]}
        for link in raw_neighbors
    ]
    return {"node_id": node_id, "sequence": sequence, "neighbors": neighbors}


def is_newer(existing_lsp: dict, incoming_lsp: dict) -> bool:
    """Indica si ``incoming_lsp`` reemplaza al que ya se tenía guardado."""

    if existing_lsp is None:
        return True
    return incoming_lsp["sequence"] > existing_lsp["sequence"]
