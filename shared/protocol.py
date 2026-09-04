"""
Fase 0 / Fase 3
USADO POR: todos los demás módulos (Dijkstra, Flooding, LSR)

Único punto de entrada para construir/leer paquetes. Nadie más debería
armar un dict de paquete a mano ni usar json.dumps/loads directamente:
siempre pasar por build_packet / serialize / deserialize, así el formato
completo (nombres de campo, TTL por defecto, validación) vive en un solo
lugar y respeta shared/constants.py.

Implementa el envelope del Protocolo Unificado de Comunicación LSR acordado
con los demás grupos de la clase, para poder interoperar con sus nodos:
- Campo "version" en el paquete.
- headers obligatorios "msg_id" (UUID) y "checksum" (CRC32 del payload),
  agregados automáticamente por build_packet.
- TTL por defecto distinto para hello/echo (1) que para el resto (16).

Nota de alcance: se valida lo que importa para interoperar (version,
checksum, campos obligatorios). No se rechazan paquetes por 'proto'/'type'
fuera de lo ya conocido ni por forma exacta del payload de hello/echo, para
no romper con variantes razonables de otros equipos en pleno ejercicio.
"""

import json
import uuid
import zlib
from shared import constants as c

PROTOCOL_VERSION = 1
_HELLO_LIKE_TYPES = {c.TYPE_HELLO, c.TYPE_ECHO}

MSG_ID_HEADER = "msg_id"
CHECKSUM_HEADER = "checksum"


class ProtocolError(ValueError):
    """El paquete no cumple el protocolo unificado."""


def _canonical_payload_bytes(payload) -> bytes:
    """Bytes deterministas de un payload, para el checksum.

    Los mensajes de usuario (texto) se firman sobre su UTF-8 tal cual;
    el resto de payloads (dict/list/...) usan una serialización JSON
    determinista para que todos los nodos calculen el mismo CRC32.
    """
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def compute_checksum(payload) -> str:
    return f"{zlib.crc32(_canonical_payload_bytes(payload)):08x}"


def _headers_get(headers, key):
    for item in headers or []:
        if isinstance(item, dict) and key in item:
            return item[key]
    return None


def _headers_set(headers: list, key: str, value) -> list:
    result = [item for item in (headers or []) if not (isinstance(item, dict) and key in item)]
    result.append({key: value})
    return result


def build_packet(proto: str, type_: str, from_: str, to: str,
                  ttl: int = None, headers: list = None, payload=None) -> dict:
    """Construye un paquete (dict) siguiendo el esquema de protocol_schema.json."""
    if ttl is None:
        ttl = c.HELLO_TTL if type_ in _HELLO_LIKE_TYPES else c.DEFAULT_TTL

    output_headers = list(headers or [])
    output_headers = _headers_set(output_headers, MSG_ID_HEADER, str(uuid.uuid4()))
    output_headers = _headers_set(output_headers, CHECKSUM_HEADER, compute_checksum(payload))

    packet = {
        c.FIELD_VERSION: PROTOCOL_VERSION,
        c.FIELD_PROTO: proto,
        c.FIELD_TYPE: type_,
        c.FIELD_FROM: from_,
        c.FIELD_TO: to,
        c.FIELD_TTL: ttl,
        c.FIELD_HEADERS: output_headers,
        c.FIELD_PAYLOAD: payload,
    }
    validate_packet(packet)
    return packet


def serialize(packet: dict) -> str:
    """Convierte un paquete (dict) a un string JSON listo para enviar por socket."""
    validate_packet(packet)
    return json.dumps(packet, separators=(",", ":"))


def deserialize(raw: str) -> dict:
    """Convierte un string JSON recibido por socket a un paquete (dict) validado."""
    packet = json.loads(raw)
    validate_packet(packet)
    return packet


def validate_packet(packet: dict) -> None:
    """
    Valida que el paquete tenga los campos obligatorios definidos en
    protocol_schema.json, la versión de protocolo correcta, y un checksum
    que coincida con el payload. No valida el contenido del payload en sí
    (eso lo hace cada algoritmo: ver node/algorithms/lsr/lsp.py para LSR).
    """
    if not isinstance(packet, dict):
        raise ProtocolError("El paquete debe ser un objeto JSON")

    required = [getattr(c, f"FIELD_{key.upper()}") for key in c.REQUIRED_FIELD_KEYS]
    missing = [field for field in required if field not in packet]
    if missing:
        raise ProtocolError(f"Paquete inválido, faltan campos: {missing}")

    if packet[c.FIELD_VERSION] != PROTOCOL_VERSION:
        raise ProtocolError(
            f"Versión de protocolo no soportada: {packet[c.FIELD_VERSION]!r}"
        )

    headers = packet.get(c.FIELD_HEADERS)
    if not isinstance(headers, list):
        raise ProtocolError("headers debe ser una lista")

    msg_id = _headers_get(headers, MSG_ID_HEADER)
    if not msg_id:
        raise ProtocolError("Falta el header obligatorio 'msg_id'")

    checksum = _headers_get(headers, CHECKSUM_HEADER)
    if not checksum:
        raise ProtocolError("Falta el header obligatorio 'checksum'")
    if checksum != compute_checksum(packet.get(c.FIELD_PAYLOAD)):
        raise ProtocolError("El checksum no coincide con el payload")


def decrement_ttl(packet: dict) -> dict:
    """Regresa una copia del paquete con el TTL decrementado en 1 (para forwarding/flooding)."""
    new_packet = dict(packet)
    new_packet[c.FIELD_TTL] = packet[c.FIELD_TTL] - 1
    return new_packet
