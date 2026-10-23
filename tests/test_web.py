import asyncio
import json
import socket

import aiohttp
import pytest

from ew_to_obs.client import EwClient
from ew_to_obs.live import LiveState
from ew_to_obs.web import StateHub, WebServer, _Browser
from fake_ew import FakeEw


def run(coro, timeout=20):
    return asyncio.run(asyncio.wait_for(coro, timeout))


async def started(hub=None):
    hub = hub or StateHub()
    server = WebServer(hub, "127.0.0.1", 0)
    await server.start()
    return hub, server


async def receive(ws, timeout=3):
    message = await asyncio.wait_for(ws.receive(), timeout)
    assert message.type == aiohttp.WSMsgType.TEXT, message
    return json.loads(message.data)


async def silence(ws, delay=0.2):
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ws.receive(), delay)


def test_new_browser_gets_current_state_then_only_changes():
    async def scenario():
        hub, server = await started()
        async with aiohttp.ClientSession() as http:
            async with http.ws_connect(server.url + "ws") as ws:
                assert await receive(ws) == {"visible": False, "text": ""}
                hub.publish(LiveState(True, "Bonjour 😁\nà tous"))
                assert await receive(ws) == {"visible": True, "text": "Bonjour 😁\nà tous"}
                hub.publish(LiveState(True, "Bonjour 😁\nà tous"))  # identique : rien
                await silence(ws)
                hub.publish(LiveState.hidden())
                assert await receive(ws) == {"visible": False, "text": ""}
        await server.stop()

    run(scenario())


def test_late_browser_receives_the_state_already_published():
    async def scenario():
        hub, server = await started()
        hub.publish(LiveState(True, "déjà là"))
        async with aiohttp.ClientSession() as http:
            async with http.ws_connect(server.url + "ws") as ws:
                assert await receive(ws) == {"visible": True, "text": "déjà là"}
        await server.stop()

    run(scenario())


def test_all_browsers_are_served_and_disconnections_are_forgotten():
    async def scenario():
        hub, server = await started()
        async with aiohttp.ClientSession() as http:
            a = await http.ws_connect(server.url + "ws")
            b = await http.ws_connect(server.url + "ws")
            await receive(a), await receive(b)
            assert hub.browser_count == 2
            hub.publish(LiveState(True, "pour tous"))
            assert (await receive(a))["text"] == (await receive(b))["text"] == "pour tous"
            await a.close()
            for _ in range(100):
                if hub.browser_count == 1:
                    break
                await asyncio.sleep(0.02)
            assert hub.browser_count == 1
            hub.publish(LiveState(True, "toujours là"))
            assert (await receive(b))["text"] == "toujours là"
            await b.close()
        await server.stop()

    run(scenario())


def test_slow_browser_only_gets_the_latest_state():
    sent = []

    class FakeWs:
        async def send_str(self, data):
            sent.append(json.loads(data)["text"])

    async def scenario():
        browser = _Browser(FakeWs())
        for text in ("a", "b", "c"):  # trois changements avant que l'envoi ne s'exécute
            browser.push(LiveState(True, text))
        task = asyncio.ensure_future(browser.run())
        await asyncio.sleep(0.05)
        task.cancel()

    run(scenario())
    assert sent == ["c"]


def test_stopping_the_server_closes_the_browsers():
    async def scenario():
        hub, server = await started()
        async with aiohttp.ClientSession() as http:
            ws = await http.ws_connect(server.url + "ws")
            await receive(ws)
            await server.stop()
            message = await asyncio.wait_for(ws.receive(), 3)
            assert message.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.CLOSED,
            )

    run(scenario())


def test_serves_the_page_with_no_cache_and_nothing_else():
    async def scenario():
        _, server = await started()
        base = server.url
        async with aiohttp.ClientSession() as http:
            for path, kind in (
                ("", "text/html"),
                ("index.js", "javascript"),
                ("index.css", "text/css"),
            ):
                async with http.get(base + path) as response:
                    assert response.status == 200, path
                    assert kind in response.headers["Content-Type"], path
                    assert response.headers["Cache-Control"] == "no-store"
            async with http.get(base) as response:
                html = await response.text()
                assert "/index.js" in html and "/index.css" in html
                assert "http://" not in html and "https://" not in html  # aucun CDN
            async with http.get(base + "favicon.ico") as response:
                assert response.status == 204
            for path in ("secret", "..%2Fpyproject.toml", "public/index.html", "ws/x"):
                async with http.get(base + path) as response:
                    assert response.status == 404, path
        await server.stop()

    run(scenario())


def test_busy_port_raises_a_clear_error():
    async def scenario():
        hub, server = await started()
        other = WebServer(hub, "127.0.0.1", server.port)
        with pytest.raises(OSError):
            await other.start()
        await server.stop()

    run(scenario())


def test_url_hides_wildcard_address():
    server = WebServer(StateHub(), "0.0.0.0", 8123)
    assert server.url == "http://localhost:8123/"


def test_default_bind_is_local_only():
    async def scenario():
        _, server = await started()
        assert server.host == "127.0.0.1"
        sock = server._runner.addresses[0]
        assert sock[0] == "127.0.0.1"
        await server.stop()

    run(scenario())


def test_ew_to_browser_end_to_end():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "premier", 2: "deuxième\r\nligne"}, current=1)
        hub, server = await started()
        client = EwClient(
            "127.0.0.1",
            "uid",
            port=ew.port,
            on_state=hub.publish,
            heartbeat_interval=0.1,
            backoff=(0.0, 0.05),
        )
        task = asyncio.ensure_future(client.run())
        async with aiohttp.ClientSession() as http:
            async with http.ws_connect(server.url + "ws") as ws:
                seen = []
                for expected in ({"visible": True, "text": "premier"},):
                    while True:
                        message = await receive(ws, 5)
                        seen.append(message)
                        if message == expected:
                            break
                await ew.select(2)
                assert await receive(ws, 5) == {"visible": True, "text": "deuxième\nligne"}
                await ew.set_flag("logo", True)
                assert await receive(ws, 5) == {"visible": False, "text": ""}
        client.stop()
        await asyncio.wait_for(task, 3)
        await server.stop()
        await ew.stop()

    run(scenario())


def test_port_zero_reports_the_real_port():
    async def scenario():
        _, server = await started()
        assert server.port != 0
        with socket.create_connection(("127.0.0.1", server.port), timeout=2):
            pass
        await server.stop()

    run(scenario())
