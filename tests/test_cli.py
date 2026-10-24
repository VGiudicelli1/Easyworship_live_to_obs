"""Ligne de commande : mémorisation du PC EW, de l'identité et de la dernière IP."""

import asyncio
import contextlib
import json
import logging

from ew_to_obs.__main__ import build_parser, resolve, run
from ew_to_obs.config import ConfigStore
from fake_ew import FakeEw


def parse(*argv):
    return build_parser().parse_args(list(argv))


def store_for(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    store.load()
    return store


def test_without_host_nor_saved_host_nothing_starts(tmp_path):
    assert resolve(parse(), store_for(tmp_path)) is None


def test_first_run_remembers_the_host_and_writes_the_generated_identity(tmp_path):
    store = store_for(tmp_path)
    settings = resolve(parse("--host", "PC-REGIE", "--serve"), store)
    assert settings.host == "PC-REGIE" and settings.serve
    saved = json.loads(store.path.read_text(encoding="utf-8"))
    assert saved["ew_host"] == "PC-REGIE" and saved["client_id"] == settings.client_id


def test_next_run_needs_no_argument_and_keeps_the_same_identity(tmp_path):
    first = resolve(parse("--host", "PC-REGIE"), store_for(tmp_path))
    again = resolve(parse(), store_for(tmp_path))
    assert again.host == "PC-REGIE" and again.client_id == first.client_id


def test_changing_the_host_forgets_the_old_last_ip_but_keeps_the_identity(tmp_path):
    store = store_for(tmp_path)
    first = resolve(parse("--host", "ANCIEN"), store)
    store.update(last_ip="192.168.1.5")
    resolve(parse("--host", "NOUVEAU"), store_for(tmp_path))
    after = store_for(tmp_path).config
    assert (after.ew_host, after.last_ip, after.client_id) == ("NOUVEAU", "", first.client_id)


def test_runtime_options_apply_to_this_run_only(tmp_path):
    store = store_for(tmp_path)
    settings = resolve(
        parse("--host", "PC", "--web-port", "9001", "--grace", "5", "--web-bind", "0.0.0.0"), store
    )
    assert (settings.web_port, settings.grace, settings.web_bind) == (9001, 5, "0.0.0.0")
    again = resolve(parse(), store_for(tmp_path))
    assert (again.web_port, again.grace, again.web_bind) == (8000, 2.0, "127.0.0.1")


def test_identity_and_device_name_can_be_set_explicitly_and_are_kept(tmp_path):
    store = store_for(tmp_path)
    resolve(
        parse(
            "--host",
            "PC",
            "--client-id",
            "a164e834-fc66-4cff-8e47-aa904ee9e62b",
            "--device-name",
            "Régie",
        ),
        store,
    )
    config = store_for(tmp_path).config
    assert (
        config.client_id == "a164e834-fc66-4cff-8e47-aa904ee9e62b" and config.device_name == "Régie"
    )


def test_saved_values_edited_by_hand_are_used(tmp_path):
    store = store_for(tmp_path)
    resolve(parse("--host", "PC"), store)
    data = json.loads(store.path.read_text(encoding="utf-8"))
    data.update(web_port=8222, lost_grace_seconds=4)
    store.path.write_text(json.dumps(data), encoding="utf-8")
    settings = resolve(parse(), store_for(tmp_path))
    assert (settings.web_port, settings.grace) == (8222, 4.0)


def test_two_runs_against_a_fake_ew_reuse_the_identity_and_the_last_ip(tmp_path):
    async def one_run(argv, ew):
        store = store_for(tmp_path)
        settings = resolve(parse(*argv, "--port", str(ew.port)), store)
        task = asyncio.ensure_future(run(settings, store))
        for _ in range(300):
            if len(ew.connects) >= one_run.expected:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.1)  # laisser le temps de mémoriser l'IP
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "texte"}, current=1)
        one_run.expected = 1
        await one_run(["--host", "127.0.0.1"], ew)
        one_run.expected = 2
        await one_run([], ew)  # 2e lancement : aucun argument
        await ew.stop()
        return ew

    ew = asyncio.run(asyncio.wait_for(scenario(), 20))
    first, second = ew.connects[0], ew.connects[1]
    assert first["uid"] == second["uid"]  # même identité : l'appairage est conservé
    assert first["device_name"] == "EasyWorship vers OBS"
    saved = store_for(tmp_path).config
    assert saved.ew_host == "127.0.0.1" and saved.last_ip == "127.0.0.1"


def test_show_config_prints_path_and_exits_without_starting(tmp_path, capsys):
    from ew_to_obs.__main__ import main

    assert main(["--config-dir", str(tmp_path / "cfg"), "--show-config"]) == 0
    out = capsys.readouterr().out
    assert "config.json" in out and '"web_port": 8000' in out


def test_main_without_host_explains_what_to_do(tmp_path, capsys):
    from ew_to_obs.__main__ import main

    try:
        assert main(["--headless", "--config-dir", str(tmp_path / "cfg")]) == 2
        err = capsys.readouterr().err
        assert "--host" in err and "mémorisé" in err
    finally:
        for handler in list(logging.getLogger().handlers):
            if getattr(handler, "_ew_to_obs", False):
                logging.getLogger().removeHandler(handler)
                handler.close()


def test_corrupt_config_warning_reaches_the_log_file(tmp_path):
    from ew_to_obs.__main__ import main
    from ew_to_obs.logs import LOG_NAME

    directory = tmp_path / "cfg"
    directory.mkdir()
    (directory / "config.json").write_text("{ cassé", encoding="utf-8")
    try:
        assert main(["--headless", "--config-dir", str(directory)]) == 2  # pas de PC EW connu
        log = (directory / LOG_NAME).read_text(encoding="utf-8")
        assert "mise de côté" in log and "ré-accepter" in log
        assert (directory / "config.json.bak").exists()
    finally:
        for handler in list(logging.getLogger().handlers):
            if getattr(handler, "_ew_to_obs", False):
                logging.getLogger().removeHandler(handler)
                handler.close()


def test_show_config_is_read_only(tmp_path):
    from ew_to_obs.__main__ import main

    directory = tmp_path / "cfg"
    assert main(["--config-dir", str(directory), "--show-config"]) == 0
    assert not directory.exists()  # rien créé : ni dossier, ni journal, ni config


def test_ci_mode_means_headless_and_serve(tmp_path):
    settings = resolve(parse("--ci", "--host", "PC"), store_for(tmp_path))
    assert settings.serve and settings.ci
    assert not resolve(parse("--headless", "--host", "PC"), store_for(tmp_path)).serve


def test_loglevel_only_accepts_0_to_3():
    import pytest

    assert parse("--loglevel", "2").loglevel == 2
    with pytest.raises(SystemExit):
        parse("--loglevel", "4")


def test_ci_mode_runs_as_a_service_and_logs_on_stderr(tmp_path):
    """Lancement réel `--ci --loglevel 2` : page servie, état sur stderr (pas sur stdout)."""
    import socket
    import sys
    import urllib.request

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        web_port = probe.getsockname()[1]

    async def fetch(url):
        return await asyncio.to_thread(lambda: urllib.request.urlopen(url, timeout=2).read())

    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "Bonjour"}, current=1)
        process = await asyncio.create_subprocess_exec(
            *[sys.executable, "-m", "ew_to_obs", "--ci", "--host", "127.0.0.1"],
            *["--port", str(ew.port), "--web-port", str(web_port)],
            *["--loglevel", "2", "--config-dir", str(tmp_path / "cfg")],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            page = b""
            for _ in range(200):
                try:
                    page = await fetch("http://127.0.0.1:%d/" % web_port)
                    break
                except OSError:
                    await asyncio.sleep(0.1)
            for _ in range(100):
                if ew.connects:
                    break
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.5)
        finally:
            process.terminate()
            out, err = await asyncio.wait_for(process.communicate(), 10)
            await ew.stop()
        return page, out.decode(), err.decode()

    page, out, err = asyncio.run(asyncio.wait_for(scenario(), 40))
    assert b"<html" in page.lower()
    assert out == ""  # rien sur la sortie standard : stderr seul est redirigé vers le journal
    assert "INFO" in err and "page pour OBS" in err and "connexion" in err
    assert "Bonjour" not in err  # jamais le texte des diapos dans le journal


def test_saveconf_records_service_options_and_does_not_start(tmp_path, capsys):
    from ew_to_obs.__main__ import main

    cfg = str(tmp_path / "cfg")
    code = main(
        ["--host", "pc.local", "--serve", "--loglevel", "2", "--web-port", "8123"]
        + ["--grace", "3", "--saveconf", "--config-dir", cfg]
    )
    assert code == 0
    saved = ConfigStore(cfg)
    saved.load()
    config = saved.config
    assert (config.ew_host, config.serve, config.log_level) == ("pc.local", True, 2)
    assert (config.web_port, config.lost_grace_seconds) == (8123, 3.0)
    assert '"ew_host": "pc.local"' in capsys.readouterr().out


def test_saved_options_are_the_defaults_of_a_plain_headless_run(tmp_path):
    store = store_for(tmp_path)
    resolve(parse("--host", "pc", "--serve", "--web-port", "8123", "--saveconf"), store)
    again = resolve(parse("--headless"), store_for(tmp_path))  # le lancement du démarrage
    assert again.serve and again.web_port == 8123 and again.host == "pc"


def test_without_saveconf_service_options_are_not_recorded(tmp_path):
    resolve(parse("--host", "pc", "--serve", "--web-port", "8123"), store_for(tmp_path))
    config = store_for(tmp_path).config
    assert not config.serve and config.web_port == 8000


def test_invalid_saved_serve_and_log_level_fall_back_to_defaults(tmp_path):
    from ew_to_obs.config import clean

    config, warnings = clean({"serve": "oui", "log_level": 9})
    assert not config.serve and config.log_level == 1 and len(warnings) == 2
