"""État de sortie (visible, texte) calculé à partir des messages d'EasyWorship.

Logique pure, sans réseau ni horloge : on lui passe les messages reçus, elle renvoie les messages
à envoyer et le nouvel état s'il a changé. Les règles viennent des captures réelles
(`spec/technique.md`, « Règle d'émission de l'état ») :

* la diapo en direct est `slide_rowid` du dernier `status`, jamais `imagehash` ;
* l'état est recalculé à chaque message et n'est rendu que s'il change ;
* un nouveau `liverev` vide le cache et fait tout recharger ;
* rien en direct (`imagehash` vide, `liverev "0"`, diapo absente du LiveData) ou logo/noir/clear
  donne un état caché ;
* tant que le texte d'une diapo n'est pas arrivé, on ne diffuse rien (ni texte périmé, ni vide).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .protocol import (
    ProtocolError,
    SlideRef,
    decode_live_data,
    get_live_data_message,
    get_slide_info_message,
)


@dataclass(frozen=True)
class LiveState:
    """Ce que la page affiche. Caché ⇒ texte vide, donc deux états cachés sont toujours égaux."""

    visible: bool
    text: str = ""

    @classmethod
    def hidden(cls) -> LiveState:
        return cls(False, "")


class Pairing(Enum):
    UNKNOWN = "unknown"
    PAIRED = "paired"
    NOT_PAIRED = "not_paired"


@dataclass
class Result:
    send: list[dict] = field(default_factory=list)
    state: LiveState | None = None  # nouvel état, seulement s'il a changé


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _truthy(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1")
    return bool(value)


class LiveSession:
    """Une connexion à EW. Recommencer avec une nouvelle instance après toute reconnexion."""

    def __init__(self) -> None:
        self.pairing = Pairing.UNKNOWN
        self.state: LiveState | None = None
        self._status: dict | None = None
        self._liverev: str | None = None
        self._loaded = False
        self._refs: dict[str, SlideRef] = {}
        self._pending: dict[str, int] = {}
        self._texts: dict[str, str] = {}

    def on_message(self, message: dict, extra: bytes = b"") -> Result:
        result = Result()
        action = message.get("action")
        if action == "paired":
            self.pairing = Pairing.PAIRED
        elif action == "notPaired":
            self.pairing = Pairing.NOT_PAIRED
        elif action == "status":
            self._on_status(message, result)
        elif action == "LiveData":
            self._on_live_data(extra, result)
        elif action == "slideInfo":
            self._on_slide_info(message)
        # heartbeat d'EW et actions inconnues : ignorés
        result.state = self._recompute()
        return result

    def _on_status(self, status: dict, result: Result) -> None:
        self._status = status
        liverev = str(status.get("liverev", "0"))
        if liverev == "0" or liverev == self._liverev:
            return  # EW pas prêt, ou même contenu : rien à recharger
        self._liverev = liverev
        self._loaded = False
        self._refs.clear()
        self._pending.clear()
        self._texts.clear()
        result.send.append(get_live_data_message())

    def _on_live_data(self, extra: bytes, result: Result) -> None:
        try:
            data = decode_live_data(extra)
        except ProtocolError:
            return
        if data.liverev != self._liverev or self._loaded:
            return  # réponse périmée ou doublon
        self._loaded = True
        for ref in data.slides:
            key = str(ref.rowid)
            self._refs[key] = ref
            self._pending[key] = ref.revision
            # Le titre de la présentation (diapo 0) ne sert pas : on n'en veut que le texte.
            result.send.append(get_slide_info_message(ref.rowid, ref.revision, data.pres_rowid))

    def _on_slide_info(self, info: dict) -> None:
        key = str(info.get("slide_rowid"))
        revision = self._pending.get(key)
        if revision is None or str(info.get("revision")) != str(revision):
            return  # titre de présentation, ou réponse à une requête d'un liverev précédent
        del self._pending[key]
        self._texts[key] = normalize_text(str(info.get("content", "")))

    def _recompute(self) -> LiveState | None:
        new = self._compute()
        if new is None or new == self.state:
            return None
        self.state = new
        return new

    def _compute(self) -> LiveState | None:
        status = self._status
        if status is None:
            return None
        if str(status.get("liverev", "0")) == "0" or not status.get("imagehash"):
            return LiveState.hidden()  # EW pas prêt, ou rien en direct
        if any(_truthy(status.get(flag)) for flag in ("logo", "black", "clear")):
            return LiveState.hidden()
        if not self._loaded:
            return None  # rechargement en cours : garder l'état précédent
        key = str(status.get("slide_rowid"))
        if key not in self._refs:
            return LiveState.hidden()  # diapo absente du LiveData : rien d'affichable
        if key not in self._texts:
            return None  # texte pas encore arrivé
        return LiveState(True, self._texts[key])
