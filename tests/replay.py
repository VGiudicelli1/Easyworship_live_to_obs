"""Rejoue une capture réelle (JSONL anonymisé) dans une LiveSession."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path

from ew_to_obs.live import LiveSession, LiveState

FIXTURES = Path(__file__).parent / "fixtures"


@dataclass
class Replay:
    states: list[LiveState] = field(default_factory=list)
    sent: list[dict] = field(default_factory=list)  # requêtes que le client aurait envoyées
    state_session: list[int] = field(default_factory=list)  # index de session de chaque état
    sessions: list[LiveSession] = field(default_factory=list)

    @property
    def session(self) -> LiveSession:
        return self.sessions[-1]


def load(name: str) -> list[dict]:
    path = FIXTURES / ("ew_session_%s.jsonl" % name)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def replay(name: str) -> Replay:
    """Une nouvelle LiveSession à chaque événement « connected » (captures avec reconnexion)."""
    out = Replay()
    session = None
    for rec in load(name):
        if rec["dir"] == "info" and rec.get("msg", {}).get("event") == "connected":
            session = LiveSession()
            out.sessions.append(session)
            continue
        if rec["dir"] != "recv" or "msg" not in rec:
            continue
        if session is None:  # captures plus anciennes : pas d'événement « connected »
            session = LiveSession()
            out.sessions.append(session)
        extra = base64.b64decode(rec["extra_b64"]) if "extra_b64" in rec else b""
        result = session.on_message(rec["msg"], extra)
        out.sent.extend(result.send)
        if result.state is not None:
            out.states.append(result.state)
            out.state_session.append(len(out.sessions) - 1)
    return out


def line(slide: int, n: int = 1) -> str:
    """Texte anonymisé d'une diapo à n lignes (voir la génération des fixtures)."""
    return "\n".join("Ligne %d de la diapo %d — é à ô ’ « »" % (i + 1, slide) for i in range(n))
