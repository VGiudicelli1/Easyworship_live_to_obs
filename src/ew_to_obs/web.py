"""Serveur web local : sert la page d'affichage et pousse l'état aux navigateurs (WebSocket).

Un seul message, du serveur vers le navigateur : `{"visible": bool, "text": str}`. À chaque nouvelle
connexion le serveur envoie l'état courant ; ensuite seulement les changements. Un navigateur lent
ne ralentit ni les autres ni l'application : seul le dernier état compte pour lui.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from pathlib import Path

from aiohttp import WSMsgType, web

from .config import local_hostname
from .live import LiveState

log = logging.getLogger("ew_to_obs.web")

PUBLIC = Path(__file__).parent / "public"
PAGES = {"/": "index.html", "/index.js": "index.js", "/index.css": "index.css"}
NO_STORE = {"Cache-Control": "no-store"}  # OBS garde sinon d'anciennes versions de la page


def encode_state(state: LiveState) -> str:
    return json.dumps({"visible": state.visible, "text": state.text}, ensure_ascii=False)


class _Browser:
    """Un navigateur connecté : ne garde que le dernier état à envoyer."""

    def __init__(self, ws: web.WebSocketResponse) -> None:
        self.ws = ws
        self._latest: LiveState | None = None
        self._sent: LiveState | None = None
        self._event = asyncio.Event()

    def push(self, state: LiveState) -> None:
        self._latest = state
        self._event.set()

    async def run(self) -> None:
        while True:
            await self._event.wait()
            self._event.clear()
            state = self._latest
            if state is not None and state != self._sent:
                self._sent = state
                await self.ws.send_str(encode_state(state))


class StateHub:
    """Dernier état connu et navigateurs à tenir informés."""

    def __init__(self) -> None:
        self.state = LiveState.hidden()
        self._browsers: set[_Browser] = set()

    @property
    def browser_count(self) -> int:
        return len(self._browsers)

    def publish(self, state: LiveState) -> None:
        if state == self.state:
            return
        self.state = state
        for browser in self._browsers:
            browser.push(state)

    async def close_all(self) -> None:
        for browser in list(self._browsers):
            with contextlib.suppress(Exception):
                await browser.ws.close()

    async def serve_browser(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20)  # ping : détecte un navigateur disparu
        await ws.prepare(request)
        browser = _Browser(ws)
        self._browsers.add(browser)
        browser.push(self.state)
        sender = asyncio.ensure_future(browser.run())
        log.info("navigateur connecté (%d)", len(self._browsers))
        try:
            async for message in ws:  # le navigateur n'envoie rien : on attend la fermeture
                if message.type == WSMsgType.ERROR:
                    break
        finally:
            self._browsers.discard(browser)
            sender.cancel()
            log.info("navigateur déconnecté (%d)", len(self._browsers))
        return ws


class WebServer:
    def __init__(
        self,
        hub: StateHub,
        host: str = "127.0.0.1",
        port: int = 8000,
        browser_grace: float = 2.0,
    ) -> None:
        self.hub = hub
        self.browser_grace = browser_grace  # servi à la page : /settings.json
        self.host = host
        self._requested_port = port
        self.port = port
        self._runner: web.AppRunner | None = None

    @property
    def url(self) -> str:
        if self.host in ("0.0.0.0", "::"):
            shown = local_hostname()  # écoute sur tout le réseau : l'adresse à saisir dans OBS
        else:
            shown = "localhost" if self.host == "127.0.0.1" else self.host
        return "http://%s:%d/" % (shown, self.port)

    async def start(self) -> None:
        app = web.Application()
        for path, name in PAGES.items():
            app.router.add_get(path, self._page(name))
        app.router.add_get("/settings.json", self._settings)
        app.router.add_get("/ws", self.hub.serve_browser)
        app.router.add_get("/favicon.ico", self._no_content)
        self._runner = web.AppRunner(app, shutdown_timeout=1.0)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self._requested_port)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        log.info("serveur web sur %s", self.url)

    async def stop(self) -> None:
        await self.hub.close_all()
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    @staticmethod
    def _page(name: str):  # type: ignore[no-untyped-def]
        path = PUBLIC / name

        async def handler(request: web.Request) -> web.StreamResponse:
            return web.FileResponse(path, headers=NO_STORE)

        return handler

    async def _settings(self, request: web.Request) -> web.Response:
        """Réglages de la config utiles à la page (le paramètre d'URL ?grace= les remplace)."""
        return web.json_response({"grace": self.browser_grace}, headers=NO_STORE)

    @staticmethod
    async def _no_content(request: web.Request) -> web.Response:
        return web.Response(status=204, headers=NO_STORE)
