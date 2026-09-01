"""
DUEÑO: EA (Ernesto Ascencio) - Fase 0 / Fase 3
USADO POR: todos los demás módulos (Dijkstra, Flooding, LSR)

Único punto de entrada para construir/leer paquetes. Nadie más debería
armar un dict de paquete a mano ni usar json.dumps/loads directamente:
siempre pasar por build_packet / serialize / deserialize, así el formato
completo (nombres de campo, TTL por defecto, validación) vive en un solo
lugar y respeta shared/constants.py.
"""

import json
from shared import constants as c


def build_packet(proto: str, type_: str, from_: str, to: str,
                  ttl: int = None, headers: list = None, payload=None) -> dict:
    """Construye un paquete (dict) siguiendo el esquema de protocol_schema.json."""
    packet = {
        c.FIELD_PROTO: proto,
        c.FIELD_TYPE: type_,
        c.FIELD_FROM: from_,
        c.FIELD_TO: to,
        c.FIELD_TTL: ttl if ttl is not None else c.DEFAULT_TTL,
        c.FIELD_HEADERS: headers if headers is not None else [],
        c.FIELD_PAYLOAD: payload,
    }
    validate_packet(packet)
    return packet


def serialize(packet: dict) -> str:
    """Convierte un paquete (dict) a un string JSON listo para enviar por socket."""
    validate_packet(packet)
    return json.dumps(packet)


def deserialize(raw: str) -> dict:
    """Convierte un string JSON recibido por socket a un paquete (dict) validado."""
    packet = json.loads(raw)
    validate_packet(packet)
    return packet


def validate_packet(packet: dict) -> None:
    """
    Valida que el paquete tenga los campos obligatorios definidos en
    protocol_schema.json. No valida el contenido del payload (eso lo hace
    cada algoritmo: ver node/algorithms/lsr/lsp.py para el caso de LSR).
    """
    required = [getattr(c, f"FIELD_{key.upper()}") for key in c.REQUIRED_FIELD_KEYS]
    missing = [field for field in required if field not in packet]
    if missing:
        raise ValueError(f"Paquete inválido, faltan campos: {missing}")


def decrement_ttl(packet: dict) -> dict:
    """Regresa una copia del paquete con el TTL decrementado en 1 (para forwarding/flooding)."""
    new_packet = dict(packet)
    new_packet[c.FIELD_TTL] = packet[c.FIELD_TTL] - 1
    return new_packet
