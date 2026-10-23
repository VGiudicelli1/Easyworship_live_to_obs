import pytest

from ew_to_obs.client import ConnectionStatus
from ew_to_obs.live import LiveState
from ew_to_obs.service import Snapshot
from ew_to_obs.status_text import PREVIEW_MAX, browsers_text, describe, preview_text

DEVICE = "EasyWorship vers OBS"


def snap(**values):
    return Snapshot(**{"configured": True, "host": "PC", **values})


def test_not_configured_asks_for_the_pc_name():
    view = describe(Snapshot(), DEVICE)
    assert view.color == "off" and "Aucun PC" in view.label
    assert "Appliquer" in view.banner and not view.banner_is_error


@pytest.mark.parametrize(
    "status,color,words",
    [
        (ConnectionStatus.SEARCHING, "wait", "Recherche"),
        (ConnectionStatus.CONNECTED, "ok", "Connecté"),
        (ConnectionStatus.LOST, "bad", "perdue"),
        (ConnectionStatus.STOPPED, "off", "Arrêté"),
    ],
)
def test_each_connection_status_has_a_color_and_a_french_label(status, color, words):
    view = describe(snap(status=status), DEVICE)
    assert view.color == color and words in view.label


def test_waiting_for_pairing_tells_the_operator_what_to_do_with_the_device_name():
    view = describe(snap(status=ConnectionStatus.WAITING_PAIRING), "Régie 2")
    assert view.color == "wait"
    assert "acceptez la télécommande « Régie 2 »" in view.banner


def test_lost_connection_exposes_the_detail_for_the_retry_countdown():
    view = describe(
        snap(status=ConnectionStatus.LOST, detail="fermée ; nouvel essai dans 1.0 s"), DEVICE
    )
    assert "nouvel essai dans 1.0 s" in view.detail


def test_web_error_takes_the_banner_and_is_an_error():
    view = describe(
        snap(status=ConnectionStatus.CONNECTED, web_error="Le port 8000 est occupé"), DEVICE
    )
    assert view.banner == "Le port 8000 est occupé" and view.banner_is_error
    assert view.color == "ok"  # la connexion à EW reste affichée comme telle


def test_browsers_text_singular_plural_and_none():
    assert "aucun" in browsers_text(0)
    assert browsers_text(1) == "1 connecté"
    assert browsers_text(3) == "3 connectés"


def test_preview_text_cases():
    assert preview_text(LiveState.hidden()) == "— rien d'affiché —"
    assert preview_text(LiveState(True, "")) == "— diapo sans texte —"
    assert preview_text(LiveState(True, "Dieu est amour")) == "Dieu est amour"
    long = preview_text(LiveState(True, "mot " * 500))
    assert len(long) <= PREVIEW_MAX + 3 and long.endswith("…")
