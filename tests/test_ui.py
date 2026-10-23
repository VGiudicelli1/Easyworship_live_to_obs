"""La fenêtre (Tkinter). Ignorés sans tkinter ni écran (CI sans affichage) :
`xvfb-run -a python -m pytest tests/test_ui.py` sous Linux."""

import socket
import sys
import time

import pytest

from test_service import EwThread, wait_for

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="fenêtre testée sous Linux (Xvfb) ; Windows et macOS : recette (doc/recette.md)",
)

tk = pytest.importorskip("tkinter")

from ew_to_obs import ui  # noqa: E402
from ew_to_obs.client import ConnectionStatus  # noqa: E402
from ew_to_obs.config import ConfigStore  # noqa: E402
from ew_to_obs.live import LiveState  # noqa: E402
from ew_to_obs.service import Service, Snapshot  # noqa: E402


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:
        pytest.skip("pas d'écran : %s" % exc)
    window.withdraw()
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass


class StubService:
    """Un service factice : la fenêtre ne dépend que de snapshot(), configure() et store."""

    def __init__(self, tmp_path, snapshot=None, **config):
        self.store = ConfigStore(tmp_path / "cfg")
        self.store.load()
        for name, value in config.items():
            setattr(self.store.config, name, value)
        self.snap = snapshot or Snapshot()
        self.calls = []

    def snapshot(self):
        return self.snap

    def configure(self, host, web_port=None, obs_query=None):
        self.calls.append((host, web_port, obs_query))


def pump(root, seconds=0.0):
    end = time.monotonic() + seconds
    root.update()
    while time.monotonic() < end:
        root.update()
        time.sleep(0.01)


def connected(**values):
    return Snapshot(
        configured=True,
        host="PC",
        status=ConnectionStatus.CONNECTED,
        url="http://localhost:8000/",
        **values,
    )


def test_initial_values_come_from_the_config(root, tmp_path):
    stub = StubService(tmp_path, ew_host="PC-REGIE", web_port=8123, obs_query="lines=5")
    app = ui.App(root, stub)
    assert (app.host_var.get(), app.port_var.get(), app.query_var.get()) == (
        "PC-REGIE",
        "8123",
        "lines=5",
    )


def test_not_configured_shows_the_help_banner_and_no_url(root, tmp_path):
    app = ui.App(root, StubService(tmp_path))
    pump(root)
    assert "Aucun PC" in app.status_var.get()
    assert "Appliquer" in app.banner_var.get()
    assert app.url_var.get() == "" and "disabled" in app.copy_button.state()
    assert app.preview_var.get() == ""


@pytest.mark.parametrize(
    "status,words,color",
    [
        (ConnectionStatus.SEARCHING, "Recherche", ui.COLORS["wait"]),
        (ConnectionStatus.CONNECTED, "Connecté", ui.COLORS["ok"]),
        (ConnectionStatus.LOST, "perdue", ui.COLORS["bad"]),
    ],
)
def test_status_text_and_dot_color_follow_the_service(root, tmp_path, status, words, color):
    app = ui.App(root, StubService(tmp_path, Snapshot(configured=True, host="PC", status=status)))
    pump(root)
    assert words in app.status_var.get()
    assert str(app.dot.cget("foreground")) == color


def test_pairing_wait_shows_a_banner_with_the_device_name(root, tmp_path):
    snap = Snapshot(configured=True, host="PC", status=ConnectionStatus.WAITING_PAIRING)
    app = ui.App(root, StubService(tmp_path, snap, device_name="Régie 2"))
    pump(root)
    assert "acceptez la télécommande « Régie 2 »" in app.banner_var.get()


def test_preview_browsers_and_url_follow_the_snapshot_and_typed_settings(root, tmp_path):
    stub = StubService(tmp_path, connected(state=LiveState(True, "Dieu est amour"), browsers=2))
    app = ui.App(root, stub)
    pump(root, 0.3)
    assert app.preview_var.get() == "Dieu est amour"
    assert app.browsers_var.get() == "2 connectés"
    assert app.url_var.get() == "http://localhost:8000/?lines=4"
    app.query_var.set("lines=6&valign=bottom")
    pump(root, 0.4)
    assert app.url_var.get() == "http://localhost:8000/?lines=6&valign=bottom"
    app.query_var.set("pas valide !")  # saisie invalide : on n'affiche pas une adresse piégée
    pump(root, 0.4)
    assert app.url_var.get() == "http://localhost:8000/"
    stub.snap = connected(state=LiveState.hidden())
    pump(root, 0.4)
    assert app.preview_var.get() == "— rien d'affiché —"


def test_copy_puts_the_url_in_the_clipboard(root, tmp_path):
    app = ui.App(root, StubService(tmp_path, connected()))
    pump(root, 0.3)
    app.copy_url()
    assert root.clipboard_get() == "http://localhost:8000/?lines=4"
    assert app.copied_var.get() == "Adresse copiée"


def test_apply_with_valid_values_calls_the_service_once(root, tmp_path):
    stub = StubService(tmp_path)
    app = ui.App(root, stub)
    app.host_var.set("  PC-REGIE.local ")
    app.port_var.set("8001")
    app.query_var.set("lines=4&bg=%23003366")
    app.apply()
    assert stub.calls == [("PC-REGIE.local", 8001, "lines=4&bg=%23003366")]


@pytest.mark.parametrize(
    "host,port,query,message",
    [
        ("", "8000", "", "Saisissez le nom du PC EasyWorship."),
        ("http://x/", "8000", "", "Nom de PC invalide"),
        ("PC", "huit mille", "", "Port de la page invalide"),
        ("PC", "70000", "", "Port de la page invalide"),
        ("PC", "8000", "a b", "Réglages de la page invalides"),
        ("PC", "8000", "x=<script>", "Réglages de la page invalides"),
    ],
)
def test_apply_rejects_bad_input_without_touching_the_service(
    root, tmp_path, host, port, query, message
):
    stub = StubService(tmp_path)
    app = ui.App(root, stub)
    app.host_var.set(host)
    app.port_var.set(port)
    app.query_var.set(query)
    app.apply()
    assert stub.calls == []
    assert message in app.banner_var.get()
    assert str(app.banner_label.cget("foreground")) == ui.COLORS["bad"]
    app.host_var.set("PC")
    app.port_var.set("8000")
    app.query_var.set("")
    app.apply()  # corrigé : le message d'erreur disparaît
    assert stub.calls == [("PC", 8000, "")] and message not in app.banner_var.get()


def test_enter_key_applies(root, tmp_path):
    stub = StubService(tmp_path)
    app = ui.App(root, stub)
    app.host_var.set("PC")
    root.deiconify()
    root.update()
    app.host_entry.focus_force()
    app.host_entry.event_generate("<Return>")
    pump(root, 0.2)
    assert stub.calls == [("PC", 8000, "lines=4")]


def test_web_error_is_shown_as_an_error_banner(root, tmp_path):
    snap = connected(web_error="Le port 8000 est déjà utilisé : choisissez un autre port.")
    app = ui.App(root, StubService(tmp_path, snap))
    pump(root)
    assert "déjà utilisé" in app.banner_var.get()
    assert str(app.banner_label.cget("foreground")) == ui.COLORS["bad"]


def test_open_log_folder_uses_the_config_directory(root, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(ui, "open_folder", opened.append)
    stub = StubService(tmp_path)
    app = ui.App(root, stub)
    app.open_log()
    assert opened == [stub.store.directory] and stub.store.directory.exists()


def test_quit_destroys_the_window_and_stops_refreshing(root, tmp_path):
    app = ui.App(root, StubService(tmp_path))
    pump(root, 0.3)
    app.quit()
    with pytest.raises(tk.TclError):
        root.winfo_exists()  # (update() ne lève rien après destroy)
    assert app._after_id is None


def test_window_with_the_real_service_follows_ew_end_to_end(root, tmp_path):
    ew = EwThread()
    ew.call(ew.ew.go_live({1: "Que précieux est ton amour", 2: "deuxième"}, current=1))
    store = ConfigStore(tmp_path / "cfg")
    store.load()
    with socket.socket() as probe:  # un vrai port libre : la fenêtre refuse le port 0
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    store.update(ew_host="127.0.0.1", web_port=free_port)
    service = Service(store, ew_port=ew.port)
    service.start()
    app = ui.App(root, service)
    try:
        wait_for(lambda: (pump(root, 0.05), "Connecté" in app.status_var.get())[1], what="statut")
        wait_for(
            lambda: (pump(root, 0.05), app.preview_var.get() == "Que précieux est ton amour")[1],
            what="aperçu",
        )
        assert app.url_var.get().startswith("http://localhost:") and app.url_var.get().endswith(
            "?lines=4"
        )
        ew.call(ew.ew.select(2))
        wait_for(
            lambda: (pump(root, 0.05), app.preview_var.get() == "deuxième")[1], what="aperçu 2"
        )
        ew.call(ew.ew.set_flag("logo", True))
        wait_for(
            lambda: (pump(root, 0.05), "rien d'affiché" in app.preview_var.get())[1], what="masqué"
        )
        app.query_var.set("lines=6")
        app.apply()
        wait_for(lambda: (pump(root, 0.05), app.url_var.get().endswith("?lines=6"))[1], what="url")
        wait_for(lambda: store.config.obs_query == "lines=6", what="config enregistrée")
    finally:
        app.quit()
        service.stop()
        ew.close()
