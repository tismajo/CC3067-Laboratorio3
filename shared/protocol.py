"""Envelope y utilidades del Protocolo Unificado de Comunicación (ver PROTOCOLO.md).

Punto único para construir, serializar y validar paquetes. Nadie más arma el
dict a mano ni llama a json.dumps/loads directamente.

Direcciones: un nodo se identifica por ``IP:puerto``. ``normalize_addr`` completa
el puerto por defecto para que ``"10.0.0.7"`` y ``"10.0.0.7:5000"`` sean el
mismo nodo cuando el puerto común es 5000.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
import zlib
from typing import Any, Optional

from shared import constants as c

logger = logging.getLogger("protocol")

PROTOCOL_VERSION = c.PROTOCOL_VERSION
VALID_TYPES = {c.TYPE_HELLO, c.TYPE_ECHO, c.TYPE_INFO, c.TYPE_MESSAGE}
VALID_PROTOS = {c.PROTO_DIJKSTRA, c.PROTO_FLOODING, c.PROTO_LSR}
HELLO_TTL = c.HELLO_TTL
DEFAULT_TTL = c.DEFAULT_TTL
MAX_LINE_BYTES = c.MAX_LINE_BYTES
BROADCAST_TO = c.BROADCAST_TO

CHECKSUM_HEADER = c.HEADER_CHECKSUM
MSG_ID_HEADER = c.HEADER_MSG_ID
T0_HEADER = c.HEADER_T0
VIA_HEADER = c.HEADER_VIA
TRACE_HEADER = c.HEADER_TRACE

REQUIRED_FIELDS = tuple(c.REQUIRED_FIELD_KEYS)
REQUIRED_HEADERS = tuple(c.REQUIRED_HEADER_KEYS)


class ProtocolError(ValueError):
    """El mensaje no cumple el protocolo unificado."""


# -- direcciones ------------------------------------------------------------

def normalize_addr(addr: str, default_port: int) -> str:
    """Completa el puerto por defecto: ``"1.2.3.4"`` -> ``"1.2.3.4:5000"``."""
    if not isinstance(addr, str) or not addr:
        return addr
    if addr == BROADCAST_TO:
        return addr
    if ":" in addr:
        return addr
    return f"{addr}:{default_port}"


# -- checksum -------------------------------------------------------------

def _canonical_payload_bytes(payload: Any) -> bytes:
    """Bytes acordados para el checksum (ver PROTOCOLO.md §Checksum).

    Texto: UTF-8 crudo, sin comillas. Objeto/lista: JSON con claves ordenadas,
    separadores compactos y sin escapar no-ASCII.
    """
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_checksum(payload: Any) -> str:
    return f"{zlib.crc32(_canonical_payload_bytes(payload)):08x}"


# -- headers -------------------------------------------------------------

def _headers_get(headers: list, key: str) -> Any | None:
    for item in headers or []:
        if isinstance(item, dict) and key in item:
            return item[key]
    return None


def _headers_set(headers: list, key: str, value: Any) -> list:
    result = [
        item
        for item in (headers or [])
        if not (isinstance(item, dict) and key in item)
    ]
    result.append({key: value})
    return result


def get_header(message: dict, key: str, default: Any = None) -> Any:
    value = _headers_get(message.get("headers", []), key)
    return default if value is None else value


def set_header(message: dict, key: str, value: Any) -> dict:
    """Copia un mensaje y reemplaza un header sin alterar el payload."""
    result = dict(message)
    result["headers"] = _headers_set(message.get("headers", []), key, value)
    return result


# -- construcción -------------------------------------------------------

def build_message(
    proto: str,
    type_: str,
    src: str,
    dst: str,
    payload: Any,
    ttl: Optional[int] = None,
    headers: Optional[list] = None,
    msg_id: Optional[str] = None,
    t0: Optional[float] = None,
) -> dict:
    """Construye un paquete canónico con version, msg_id (UUIDv4) y checksum."""
    if proto not in VALID_PROTOS:
        raise ProtocolError(f"proto inválido: {proto!r}")
    if type_ not in VALID_TYPES:
        raise ProtocolError(f"type inválido: {type_!r}")
    if ttl is None:
        ttl = HELLO_TTL if type_ in (c.TYPE_HELLO, c.TYPE_ECHO) else DEFAULT_TTL
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
        raise ProtocolError("ttl debe ser un entero positivo")

    output_headers = list(headers or [])
    if type_ in (c.TYPE_HELLO, c.TYPE_ECHO):
        if t0 is None and _headers_get(output_headers, T0_HEADER) is None:
            t0 = time.time()
        if t0 is not None:
            output_headers = _headers_set(output_headers, T0_HEADER, t0)
    output_headers = _headers_set(
        output_headers, MSG_ID_HEADER, msg_id or str(uuid.uuid4())
    )
    output_headers = _headers_set(
        output_headers, CHECKSUM_HEADER, compute_checksum(payload)
    )
    return {
        "version": PROTOCOL_VERSION,
        "proto": proto,
        "type": type_,
        "from": src,
        "to": dst,
        "ttl": ttl,
        "headers": output_headers,
        "payload": payload,
    }


def build_echo(hello: dict, my_addr: str) -> dict:
    """Respuesta a un ``hello``: conserva msg_id y t0, invierte from/to."""
    return build_message(
        proto=hello["proto"],
        type_=c.TYPE_ECHO,
        src=my_addr,
        dst=hello["from"],
        payload=hello.get("payload") or {},
        ttl=HELLO_TTL,
        msg_id=get_header(hello, MSG_ID_HEADER),
        t0=get_header(hello, T0_HEADER),
    )


def make_hello_payload(listen_port: int) -> dict:
    return {"listen_port": listen_port}


# -- serialización (NDJSON: un objeto por línea, terminado en \n) --------

def serialize(message: dict) -> bytes:
    """Bytes de UNA línea JSON, sin el ``\\n`` final (lo agrega el transporte)."""
    return json.dumps(message, separators=(",", ":")).encode("utf-8")


def parse_message(data: bytes | str) -> Optional[dict]:
    """Deserializa y valida un paquete. Devuelve None si es estructuralmente inválido.

    Un checksum que no coincide o un version distinto de 1 se registran pero NO
    descartan el paquete (PROTOCOLO.md §Checksum).
    """
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            logger.warning("Paquete descartado: UTF-8 inválido (%s)", exc)
            return None
    try:
        message = json.loads(data)
    except json.JSONDecodeError as exc:
        logger.warning("Paquete descartado: JSON inválido (%s)", exc)
        return None
    if not isinstance(message, dict):
        logger.warning("Paquete descartado: el mensaje no es un objeto JSON")
        return None

    message.setdefault("version", PROTOCOL_VERSION)
    missing = [f for f in REQUIRED_FIELDS if f not in message]
    if missing:
        logger.warning("Paquete descartado: faltan campos %s", missing)
        return None
    if message["proto"] not in VALID_PROTOS or message["type"] not in VALID_TYPES:
        logger.warning("Paquete descartado: proto/type inválido")
        return None
    if not isinstance(message["from"], str) or not isinstance(message["to"], str):
        logger.warning("Paquete descartado: from/to inválidos")
        return None
    ttl = message["ttl"]
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
        logger.warning("Paquete descartado: ttl inválido (%r)", ttl)
        return None
    if not isinstance(message["headers"], list):
        logger.warning("Paquete descartado: headers no es lista")
        return None
    missing_headers = [k for k in REQUIRED_HEADERS if get_header(message, k) is None]
    if missing_headers:
        logger.warning("Paquete descartado: faltan headers %s", missing_headers)
        return None
    if not isinstance(get_header(message, MSG_ID_HEADER), str):
        logger.warning("Paquete descartado: msg_id inválido")
        return None

    # Blandos: se registran, no descartan.
    if message["version"] != PROTOCOL_VERSION:
        logger.warning("version no soportada %r, se procesa igual", message["version"])
    if get_header(message, CHECKSUM_HEADER) != compute_checksum(message["payload"]):
        logger.warning("checksum no coincide (de %s), se procesa igual", message["from"])

    if message["type"] in (c.TYPE_HELLO, c.TYPE_ECHO):
        if not isinstance(message["payload"], dict):
            logger.warning("Paquete descartado: payload hello/echo no es objeto")
            return None
        if not isinstance(message["payload"].get("listen_port"), int):
            logger.warning("hello/echo sin listen_port entero (de %s)", message["from"])
    return message


# -- reenvío -----------------------------------------------------------

def decrement_ttl(message: dict) -> Optional[dict]:
    """Copia con TTL-1. None si llega a 0 (se descarta)."""
    new_ttl = message["ttl"] - 1
    if new_ttl <= 0:
        logger.info("TTL_EXPIRED: %s -> %s", message.get("from"), message.get("to"))
        return None
    result = dict(message)
    result["ttl"] = new_ttl
    return result


def prepare_forward(message: dict, via: str) -> Optional[dict]:
    """Decrementa TTL y actualiza los headers de reenvío (via, trace)."""
    forwarded = decrement_ttl(message)
    if forwarded is None:
        return None
    forwarded = set_header(forwarded, VIA_HEADER, via)
    if forwarded["type"] == c.TYPE_MESSAGE:
        trace = list(get_header(forwarded, TRACE_HEADER, []))
        if not trace or trace[-1] != via:
            trace.append(via)
        forwarded = set_header(forwarded, TRACE_HEADER, trace)
    return forwarded
