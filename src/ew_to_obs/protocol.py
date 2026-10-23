"""Protocole de la télécommande EasyWorship : trames, messages et binaire de LiveData.

Non documenté par EasyWorship : tout ce qui est ici vient du code de la V1 et des captures réelles
(`doc/protocole_easyworship.md`). Aucun message n'est inventé.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass

CRLF = b"\r\n"

# Messages suivis de `size` octets binaires juste après la ligne JSON.
EXTRA_ACTIONS = frozenset({"LiveData", "ScheduleData", "currentImage", "slideImage"})

_LIVEDATA_HEADER = struct.Struct("<lqqqlq")  # 40 octets
_LIVEDATA_SLIDE = struct.Struct("<qq")  # rowid, revision

MAX_LINE = 16 * 1024 * 1024  # au-delà, le flux est considéré corrompu
MAX_EXTRA = 64 * 1024 * 1024


class ProtocolError(Exception):
    """Flux ou message illisible."""


@dataclass(frozen=True)
class Frame:
    """Un message reçu : le JSON (None s'il est illisible), ses octets joints, la ligne brute."""

    message: dict | None
    extra: bytes
    raw: bytes


class FrameDecoder:
    """Découpe le flux TCP en messages : une ligne JSON terminée par CRLF, puis `size` octets
    si l'action fait partie de EXTRA_ACTIONS. Tolère les messages coupés n'importe où."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self._buf += data
        frames: list[Frame] = []
        while True:
            end = self._buf.find(CRLF)
            if end == -1:
                if len(self._buf) > MAX_LINE:
                    raise ProtocolError("ligne trop longue sans CRLF")
                break
            line = bytes(self._buf[:end])
            message = _parse_line(line)
            size = 0
            if message is not None and message.get("action") in EXTRA_ACTIONS:
                size = _as_int(message.get("size"))
                if size < 0 or size > MAX_EXTRA:
                    raise ProtocolError("taille de données jointes invalide : %r" % size)
            total = end + len(CRLF) + size
            if len(self._buf) < total:
                break  # message incomplet : attendre la suite
            extra = bytes(self._buf[end + len(CRLF) : total])
            del self._buf[:total]
            frames.append(Frame(message, extra, line))
        return frames


def _parse_line(line: bytes) -> dict | None:
    # EW peut envoyer un U+FFFD, et un octet invalide ne doit pas faire perdre tout le message.
    text = line.decode("utf-8", errors="replace")
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _as_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return 0


def encode(message: dict) -> bytes:
    return json.dumps(message, separators=(",", ":")).encode("utf-8") + CRLF


def connect_message(uid: str, device_name: str) -> dict:
    return {"device_type": 0, "action": "connect", "uid": uid, "device_name": device_name}


def heartbeat_message(requestrev: int = 0) -> dict:
    return {"action": "heartbeat", "requestrev": requestrev}


def get_live_data_message(requestrev: int = 0) -> dict:
    return {"action": "GetLiveData", "requestrev": requestrev}


def get_slide_info_message(
    slide_rowid: int, revision: int, pres_rowid: int, requestrev: int = 0
) -> dict:
    return {
        "slide_rowid": slide_rowid,
        "revision": revision,
        "action": "getSlideInfo",
        "requestrev": requestrev,
        "rectype": 1,
        "pres_rowid": pres_rowid,
    }


@dataclass(frozen=True)
class SlideRef:
    rowid: int
    revision: int


@dataclass(frozen=True)
class LiveData:
    liverev: str
    pres_rowid: int
    title_revision: int
    slides: tuple[SlideRef, ...]


def decode_live_data(extra: bytes) -> LiveData:
    """Décode le binaire de LiveData : en-tête de 40 octets puis n × (rowid, revision)."""
    if len(extra) < _LIVEDATA_HEADER.size:
        raise ProtocolError("LiveData trop court : %d octets" % len(extra))
    _, liverev, pres_rowid, title_revision, count, _ = _LIVEDATA_HEADER.unpack_from(extra)
    needed = _LIVEDATA_HEADER.size + _LIVEDATA_SLIDE.size * max(count, 0)
    if count < 0 or needed > len(extra):
        raise ProtocolError("LiveData incohérent : %d diapos pour %d octets" % (count, len(extra)))
    slides = tuple(
        SlideRef(
            *_LIVEDATA_SLIDE.unpack_from(extra, _LIVEDATA_HEADER.size + _LIVEDATA_SLIDE.size * i)
        )
        for i in range(count)
    )
    return LiveData(str(liverev), pres_rowid, title_revision, slides)


def encode_live_data(liverev: int, pres_rowid: int, slides: list[tuple[int, int]]) -> bytes:
    """Fabrique le binaire de LiveData (tests et faux EW)."""
    body = _LIVEDATA_HEADER.pack(1, liverev, pres_rowid, 0, len(slides), 0)
    return body + b"".join(_LIVEDATA_SLIDE.pack(rowid, rev) for rowid, rev in slides)
