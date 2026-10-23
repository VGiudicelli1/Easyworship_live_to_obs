"""Service (client EW + serveur web dans un thread) contre un faux EW. Sans Tk."""

import asyncio
import json
import socket
import time

import aiohttp
import pytest

from ew_to_obs.client import ConnectionStatus
from ew_to_obs.config import ConfigStore
from ew_to_obs.live import LiveState
from ew_to_obs.service import Service
from fake_ew import FakeEw


class EwThread:
    """Un faux EW dans son propre thread (le service a le sien)."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        import threading

        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.ew = FakeEw()
        self.port = self.call(self.ew.start())

    def call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(10)

    def close(self):
        self.call(self.ew.stop())
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)


@pytest.fixture
def ew():
    thread = EwThread()
    thread.call(thread.ew.go_live({1: "premier", 2: "deuxième"}, current=1))
    yield thread
    thread.close()


def make_service(tmp_path, ew_port, host="127.0.0.1", web_port=0):
    store = ConfigStore(tmp_path / "cfg")
    store.load()
    store.update(ew_host=host, web_port=web_port)
    return Service(store, ew_port=ew_port)


def wait_for(predicate, timeout=8, what="condition"):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.02)
    raise AssertionError("%s non atteinte" % what)


def ws_messages(url, count, timeout=5):
    async def go():
        out = []
        async with aiohttp.ClientSession() as http:
            async with http.ws_connect(url.replace("http", "ws", 1) + "ws") as ws:
                for _ in range(count):
                    out.append(json.loads((await asyncio.wait_for(ws.receive(), timeout)).data))
        return out

    return asyncio.run(go())


def test_without_a_known_pc_nothing_runs_and_stop_is_clean(tmp_path):
    store = ConfigStore(tmp_path / "cfg")
    store.load()
    service = Service(store)
    service.start()
    snap = service.snapshot()
    assert not snap.configured and snap.url == "" and snap.web_error == ""
    service.stop()
    service.stop()  # idempotent


def test_connects_serves_the_page_and_reports_the_live_text(tmp_path, ew):
    service = make_service(tmp_path, ew.port)
    service.start()
    try:
        snap = wait_for(
            lambda: (
                (s := service.snapshot()).status is ConnectionStatus.CONNECTED
                and s.state.text == "premier"
                and s
            ),
            what="connexion et texte",
        )
        assert (
            snap.configured
            and snap.host == "127.0.0.1"
            and snap.url.startswith("http://localhost:")
        )
        assert service.obs_url() == snap.url + "?lines=4"  # réglages mémorisés
        assert ws_messages(snap.url, 1) == [{"visible": True, "text": "premier"}]
        wait_for(lambda: service.store.config.last_ip == "127.0.0.1", what="IP mémorisée")
    finally:
        service.stop()


def test_browser_count_follows_connections(tmp_path, ew):
    service = make_service(tmp_path, ew.port)
    service.start()
    try:
        wait_for(lambda: service.snapshot().url, what="serveur")
        url = service.snapshot().url

        async def hold():
            async with aiohttp.ClientSession() as http:
                async with http.ws_connect(url.replace("http", "ws", 1) + "ws"):
                    await asyncio.sleep(0.5)
                    return service.snapshot().browsers

        assert asyncio.run(hold()) == 1
        wait_for(lambda: service.snapshot().browsers == 0, what="déconnexion")
    finally:
        service.stop()


def test_live_changes_reach_the_snapshot(tmp_path, ew):
    service = make_service(tmp_path, ew.port)
    service.start()
    try:
        wait_for(lambda: service.snapshot().state.text == "premier")
        ew.call(ew.ew.select(2))
        wait_for(lambda: service.snapshot().state == LiveState(True, "deuxième"))
        ew.call(ew.ew.set_flag("black", True))
        wait_for(lambda: service.snapshot().state == LiveState.hidden())
    finally:
        service.stop()


def test_configure_switches_pc_resets_last_ip_and_restarts(tmp_path, ew):
    service = make_service(tmp_path, ew.port, host="localhost")
    service.start()
    try:
        wait_for(lambda: service.snapshot().state.text == "premier")
        service.configure("127.0.0.1", obs_query="lines=6&valign=bottom").result(10)
        wait_for(
            lambda: (
                service.snapshot().state.text == "premier"
                and service.snapshot().host == "127.0.0.1"
            )
        )
        config = service.store.config
        assert (config.ew_host, config.obs_query) == ("127.0.0.1", "lines=6&valign=bottom")
        assert service.obs_url().endswith("?lines=6&valign=bottom")
        assert len(ew.ew.connects) >= 2  # reconnecté après le changement
        assert ew.ew.connects[0]["uid"] == ew.ew.connects[-1]["uid"]  # même identité
    finally:
        service.stop()


def test_configure_to_a_new_web_port_moves_the_page(tmp_path, ew):
    service = make_service(tmp_path, ew.port)
    service.start()
    try:
        old = wait_for(lambda: service.snapshot().url)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = probe.getsockname()[1]
        service.configure("127.0.0.1", web_port=free).result(10)
        new = wait_for(lambda: (u := service.snapshot().url) and u != old and u)
        assert new == "http://localhost:%d/" % free
        assert ws_messages(new, 1)[0]["text"] in ("", "premier")
        with pytest.raises(OSError):
            socket.create_connection(
                ("127.0.0.1", int(old.split(":")[2].strip("/"))), timeout=1
            ).close()
    finally:
        service.stop()


def test_busy_web_port_is_reported_but_the_connection_to_ew_still_works(tmp_path, ew):
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        busy = blocker.getsockname()[1]
        service = make_service(tmp_path, ew.port, web_port=busy)
        service.start()
        try:
            snap = wait_for(
                lambda: (s := service.snapshot()).web_error and s, what="erreur de port"
            )
            assert str(busy) in snap.web_error and snap.url == ""
            wait_for(lambda: service.snapshot().status is ConnectionStatus.CONNECTED)
            assert service.obs_url() == ""  # pas d'adresse à donner à OBS
        finally:
            service.stop()


def test_pairing_wait_is_visible_in_the_snapshot(tmp_path, ew):
    ew.ew.paired = False
    service = make_service(tmp_path, ew.port)
    service.start()
    try:
        wait_for(lambda: service.snapshot().status is ConnectionStatus.WAITING_PAIRING)
        ew.call(ew.ew.accept_pairing())
        wait_for(lambda: service.snapshot().status is ConnectionStatus.CONNECTED)
    finally:
        service.stop()


def test_stop_closes_everything(tmp_path, ew):
    service = make_service(tmp_path, ew.port)
    service.start()
    url = wait_for(lambda: service.snapshot().url)
    port = int(url.split(":")[2].strip("/"))
    wait_for(lambda: service.snapshot().status is ConnectionStatus.CONNECTED)
    service.stop()
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
    wait_for(lambda: not ew.ew._writers, what="connexion à EW fermée")
