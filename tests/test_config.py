import json
import logging
import os
import re
import stat
import sys
import uuid
from pathlib import Path

import pytest

from ew_to_obs.config import Config, ConfigStore, clean, default_config_dir
from ew_to_obs.logs import LOG_NAME, setup_logging


def store_in(tmp_path) -> ConfigStore:
    return ConfigStore(tmp_path / "cfg")


# --------------------------------------------------------------- dossier selon l'OS
def test_config_dir_per_platform():
    home = {"HOME": "/home/u", "APPDATA": "C:/Users/u/AppData/Roaming", "USERPROFILE": "C:/Users/u"}
    assert default_config_dir(home, "darwin") == Path(
        "/home/u/Library/Application Support/ew_to_obs"
    )
    assert default_config_dir(home, "win32") == Path("C:/Users/u/AppData/Roaming/ew_to_obs")
    assert default_config_dir(home, "linux") == Path("/home/u/.config/ew_to_obs")
    assert default_config_dir({**home, "XDG_CONFIG_HOME": "/x"}, "linux") == Path("/x/ew_to_obs")


def test_config_dir_override_and_windows_fallback_without_appdata():
    assert default_config_dir({"EW_TO_OBS_CONFIG_DIR": "/tmp/z"}, "win32") == Path("/tmp/z")
    fallback = default_config_dir({"USERPROFILE": "C:/Users/u"}, "win32")
    assert fallback == Path("C:/Users/u/AppData/Roaming/ew_to_obs")


# --------------------------------------------------------------- lecture / écriture
def test_missing_file_gives_defaults_and_a_fresh_identity_without_writing(tmp_path):
    store = store_in(tmp_path)
    config = store.load()
    assert store.status == "missing" and not store.path.exists()
    assert config.ew_host == "" and config.web_port == 8000 and config.lost_grace_seconds == 2.0
    assert uuid.UUID(config.client_id)  # identité générée
    assert config.client_id != Config().client_id  # chaque installation a la sienne


def test_save_then_load_roundtrip_keeps_the_identity(tmp_path):
    store = store_in(tmp_path)
    store.load()
    store.update(ew_host="PC-REGIE", last_ip="192.168.1.78", web_port=8123)
    again = store_in(tmp_path)
    config = again.load()
    assert again.status == "ok"
    assert (config.ew_host, config.last_ip, config.web_port) == ("PC-REGIE", "192.168.1.78", 8123)
    assert config.client_id == store.config.client_id


def test_first_update_writes_the_file_even_without_changes(tmp_path):
    store = store_in(tmp_path)
    store.load()
    assert store.update() and store.path.exists()  # l'identité générée est mémorisée tout de suite


def test_update_only_writes_when_something_changed(tmp_path):
    store = store_in(tmp_path)
    store.load()
    store.update(ew_host="A")
    before = store.path.stat().st_mtime_ns
    store.update(ew_host="A")
    assert store.path.stat().st_mtime_ns == before
    with pytest.raises(KeyError):
        store.update(inconnu=1)


def test_write_is_atomic_and_private(tmp_path):
    store = store_in(tmp_path)
    store.load()
    store.update(ew_host="A")
    assert sorted(p.name for p in store.directory.iterdir()) == ["config.json"]  # pas de .tmp
    if sys.platform != "win32":
        assert stat.S_IMODE(store.path.stat().st_mode) == 0o600


def test_unwritable_directory_does_not_crash(tmp_path):
    blocker = tmp_path / "bloqueur"
    blocker.write_text("un fichier là où il faudrait un dossier")
    store = ConfigStore(blocker / "cfg")
    store.load()
    assert store.update(ew_host="A") is False  # échec signalé, pas d'exception


def test_corrupt_file_is_set_aside_and_defaults_are_used(tmp_path, caplog):
    store = store_in(tmp_path)
    store.directory.mkdir(parents=True)
    store.path.write_text("{ pas du json", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        config = store.load()
    assert store.status == "corrupt" and config.ew_host == ""
    assert (store.directory / "config.json.bak").read_text(encoding="utf-8") == "{ pas du json"
    assert not store.path.exists()
    assert "ré-accepter" in caplog.text


def test_json_that_is_not_an_object_is_corrupt(tmp_path):
    store = store_in(tmp_path)
    store.directory.mkdir(parents=True)
    store.path.write_text("[1, 2]", encoding="utf-8")
    store.load()
    assert store.status == "corrupt"


# --------------------------------------------------------------- validation champ par champ
def test_invalid_fields_fall_back_individually_and_valid_ones_are_kept():
    config, warnings = clean(
        {
            "ew_host": "PC-REGIE",
            "last_ip": "pas une ip",
            "web_port": 99999,
            "web_bind": "0.0.0.0",
            "lost_grace_seconds": -1,
            "device_name": "",
            "client_id": "x",
        }
    )
    assert config.ew_host == "PC-REGIE" and config.web_bind == "0.0.0.0"
    assert config.last_ip == "" and config.web_port == 8000
    assert config.lost_grace_seconds == 2.0 and config.device_name == "EasyWorship vers OBS"
    assert len(warnings) >= 5
    assert any("ré-accepter" in w for w in warnings)  # client_id invalide : nouvelle identité


@pytest.mark.parametrize(
    "field,value",
    [
        ("ew_host", 5),
        ("ew_host", "a b"),
        ("ew_host", "http://x/"),
        ("last_ip", "::1"),  # IPv6 refusée : last_ip est une IPv4
        ("last_ip", 12),
        ("web_port", "8000"),
        ("web_port", True),
        ("web_port", 80.5),
        ("web_bind", "pas-une-adresse"),
        ("lost_grace_seconds", "2"),
        ("lost_grace_seconds", 600),
    ],
)
def test_bad_values_are_rejected(field, value):
    config, warnings = clean({field: value})
    assert getattr(config, field) == getattr(Config(), field) and warnings


@pytest.mark.parametrize(
    "field,value",
    [
        ("ew_host", "pc-regie.local"),
        ("ew_host", "192.168.1.78"),
        ("last_ip", "10.0.0.5"),
        ("web_port", 1),
        ("web_bind", "::1"),
        ("web_bind", "localhost"),
        ("lost_grace_seconds", 0),
        ("lost_grace_seconds", 3.5),
        ("device_name", "Régie ‘Sainte-Cène’"),
    ],
)
def test_good_values_are_accepted(field, value):
    config, warnings = clean({field: value})
    assert getattr(config, field) == value and not warnings


def test_unknown_keys_and_newer_version_do_not_break_loading():
    config, warnings = clean({"version": 99, "futur": {"a": 1}, "ew_host": "X"})
    assert config.ew_host == "X"
    assert any("plus récente" in w for w in warnings)


def test_existing_client_id_is_never_replaced_by_loading_valid_data():
    original = str(uuid.uuid4())
    config, _ = clean({"client_id": original})
    assert config.client_id == original


# --------------------------------------------------------------- journal
def test_log_file_is_written_rotating_and_never_contains_slide_text(tmp_path):
    path = setup_logging(tmp_path / "logs")
    try:
        assert path == tmp_path / "logs" / LOG_NAME
        logging.getLogger("ew_to_obs.client").info("état : connected")
        logging.getLogger("ew_to_obs.client").debug("détail debug")  # sous le seuil INFO
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = path.read_text(encoding="utf-8")
        assert re.search(r"INFO\s+ew_to_obs.client : état : connected", content)
        assert "détail debug" not in content
    finally:
        for handler in list(logging.getLogger().handlers):
            if getattr(handler, "_ew_to_obs", False):
                logging.getLogger().removeHandler(handler)
                handler.close()


def test_unwritable_log_location_returns_none_and_keeps_going(tmp_path):
    blocker = tmp_path / "bloqueur"
    blocker.write_text("x")
    try:
        assert setup_logging(blocker / "logs") is None
    finally:
        for handler in list(logging.getLogger().handlers):
            if getattr(handler, "_ew_to_obs", False):
                logging.getLogger().removeHandler(handler)
                handler.close()


def test_environment_is_not_modified_by_the_tests():
    assert "EW_TO_OBS_CONFIG_DIR" not in os.environ or os.environ["EW_TO_OBS_CONFIG_DIR"]


def test_saved_file_is_readable_json_with_all_fields(tmp_path):
    store = store_in(tmp_path)
    store.load()
    store.update(ew_host="PC")
    data = json.loads(store.path.read_text(encoding="utf-8"))
    assert set(data) == {
        "version",
        "ew_host",
        "last_ip",
        "client_id",
        "device_name",
        "web_port",
        "web_bind",
        "lost_grace_seconds",
        "obs_query",
        "serve",
        "log_level",
    }
