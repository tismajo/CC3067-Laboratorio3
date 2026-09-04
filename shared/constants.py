"""
Fase 0 / Protocolo Unificado

Carga shared/config/protocol_schema.json y expone constantes para que el
resto del código NUNCA use strings literales como "proto" o "hello".

Por qué: si hay que renombrar un campo o agregar un type/proto, se edita SOLO
el JSON y se llama a reload() (o se reinicia el nodo). El resto del código
sigue funcionando porque referencia c.FIELD_PROTO / c.TYPE_HELLO, etc.

Uso en cualquier otro archivo:
    from shared import constants as c
    packet = {c.FIELD_PROTO: c.PROTO_LSR, c.FIELD_TYPE: c.TYPE_HELLO, ...}
"""

import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "config" / "protocol_schema.json"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _apply(schema: dict, module_globals: dict) -> None:
    fields = schema["field_names"]
    module_globals["FIELD_VERSION"] = fields["version"]
    module_globals["FIELD_PROTO"] = fields["proto"]
    module_globals["FIELD_TYPE"] = fields["type"]
    module_globals["FIELD_FROM"] = fields["from"]
    module_globals["FIELD_TO"] = fields["to"]
    module_globals["FIELD_TTL"] = fields["ttl"]
    module_globals["FIELD_HEADERS"] = fields["headers"]
    module_globals["FIELD_PAYLOAD"] = fields["payload"]

    protos = schema["proto_values"]
    module_globals["PROTO_DIJKSTRA"] = protos["DIJKSTRA"]
    module_globals["PROTO_FLOODING"] = protos["FLOODING"]
    module_globals["PROTO_LSR"] = protos["LSR"]

    types_ = schema["type_values"]
    module_globals["TYPE_HELLO"] = types_["HELLO"]
    module_globals["TYPE_ECHO"] = types_["ECHO"]
    module_globals["TYPE_MESSAGE"] = types_["MESSAGE"]
    module_globals["TYPE_INFO"] = types_["INFO"]

    headers = schema["header_keys"]
    module_globals["HEADER_MSG_ID"] = headers["MSG_ID"]
    module_globals["HEADER_CHECKSUM"] = headers["CHECKSUM"]
    module_globals["HEADER_T0"] = headers["T0"]
    module_globals["HEADER_VIA"] = headers["VIA"]
    module_globals["HEADER_TRACE"] = headers["TRACE"]

    module_globals["PROTOCOL_VERSION"] = schema["version"]
    module_globals["DEFAULT_TTL"] = schema["defaults"]["ttl"]
    module_globals["HELLO_TTL"] = schema["defaults"]["hello_ttl"]
    module_globals["MAX_LINE_BYTES"] = schema["limits"]["max_line_bytes"]
    module_globals["BROADCAST_TO"] = schema["broadcast_to"]
    module_globals["REQUIRED_FIELD_KEYS"] = schema["required_fields"]
    module_globals["REQUIRED_HEADER_KEYS"] = schema["required_headers"]
    module_globals["_SCHEMA"] = schema


_apply(_load_schema(), globals())


def reload() -> None:
    """Vuelve a leer protocol_schema.json en caliente."""
    _apply(_load_schema(), globals())
