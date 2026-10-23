"""Libellés de la fenêtre, en fonction de l'état du service (sans Tk : testable partout)."""

from __future__ import annotations

from dataclasses import dataclass

from .client import ConnectionStatus
from .live import LiveState
from .service import Snapshot

PREVIEW_MAX = 400


@dataclass(frozen=True)
class StatusView:
    color: str  # "ok", "wait", "bad" ou "off"
    label: str
    banner: str  # message à lire absolument (vide si rien de particulier)
    banner_is_error: bool = False
    detail: str = ""


def describe(snapshot: Snapshot, device_name: str) -> StatusView:
    if snapshot.web_error:
        base = describe_connection(snapshot, device_name)
        return StatusView(base.color, base.label, snapshot.web_error, True, base.detail)
    return describe_connection(snapshot, device_name)


def describe_connection(snapshot: Snapshot, device_name: str) -> StatusView:
    if not snapshot.configured:
        return StatusView(
            "off",
            "Aucun PC EasyWorship configuré",
            "Saisissez le nom du PC EasyWorship, puis cliquez sur Appliquer.",
        )
    status = snapshot.status
    if status is ConnectionStatus.WAITING_PAIRING:
        return StatusView(
            "wait",
            "En attente d'acceptation sur le PC EasyWorship",
            "Dans EasyWorship, acceptez la télécommande « %s »." % device_name,
        )
    if status is ConnectionStatus.CONNECTED:
        return StatusView("ok", "Connecté à EasyWorship", "")
    if status is ConnectionStatus.LOST:
        return StatusView(
            "bad", "Connexion perdue : reconnexion automatique", "", detail=snapshot.detail
        )
    if status is ConnectionStatus.STOPPED:
        return StatusView("off", "Arrêté", "")
    return StatusView("wait", "Recherche d'EasyWorship…", "")


def browsers_text(count: int) -> str:
    if count == 0:
        return "aucun (rien n'est encore connecté dans OBS)"
    return "1 connecté" if count == 1 else "%d connectés" % count


def preview_text(state: LiveState) -> str:
    if not state.visible:
        return "— rien d'affiché —"
    if state.text == "":
        return "— diapo sans texte —"
    text = state.text
    return text if len(text) <= PREVIEW_MAX else text[:PREVIEW_MAX].rstrip() + " …"
