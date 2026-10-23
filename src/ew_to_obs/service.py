"""Le client EasyWorship et le serveur web, dans un thread, pour une interface graphique.

Tkinter doit rester dans le thread principal : le service fait tourner la boucle asynchrone dans un
thread à part et expose un **instantané** (`Snapshot`) que la fenêtre lit à intervalle régulier.
Aucun appel Tk ne vient jamais d'un autre thread.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field

from .client import ConnectionStatus, EwClient
from .config import ConfigStore
from .live import LiveState
from .web import StateHub, WebServer

log = logging.getLogger("ew_to_obs.service")


@dataclass(frozen=True)
class Snapshot:
    configured: bool = False  # un PC EasyWorship est connu
    host: str = ""
    status: ConnectionStatus = ConnectionStatus.SEARCHING
    detail: str = ""
    state: LiveState = field(default_factory=LiveState.hidden)
    browsers: int = 0
    url: str = ""  # adresse de la page, sans réglages
    web_error: str = ""  # serveur web impossible à démarrer (port occupé…)


class Service:
    def __init__(self, store: ConfigStore, ew_port: int | None = None) -> None:
        self.store = store
        self._ew_port = ew_port  # diagnostic : port de la télécommande imposé
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._snapshot = Snapshot()
        self._hub = StateHub()
        self._client: EwClient | None = None
        self._task: asyncio.Task | None = None
        self._server: WebServer | None = None

    # ------------------------------------------------------------------ cycle de vie
    def start(self) -> None:
        """Démarre le thread, et la connexion si un PC EasyWorship est déjà mémorisé."""
        ready = threading.Event()

        def run() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.call_soon(ready.set)
            self._loop.run_forever()
            self._loop.close()

        self._thread = threading.Thread(target=run, name="ew_to_obs-service", daemon=True)
        self._thread.start()
        ready.wait(5)
        self._submit(self._restart())

    def stop(self) -> None:
        """Arrêt propre : sockets fermés, thread terminé. Sans effet si déjà arrêté."""
        if self._loop is None or self._thread is None:
            return
        with contextlib.suppress(Exception):
            self._submit(self._stop_runtime()).result(10)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(5)
        self._loop = self._thread = None

    def configure(
        self, host: str, web_port: int | None = None, obs_query: str | None = None
    ) -> Future:
        """Change le PC EasyWorship, le port de la page ou ses réglages, mémorise et redémarre."""
        return self._submit(self._configure(host.strip(), web_port, obs_query))

    def snapshot(self) -> Snapshot:
        with self._lock:
            snap = self._snapshot
        return Snapshot(**{**snap.__dict__, "browsers": self._hub.browser_count})

    def obs_url(self) -> str:
        """Adresse à coller dans OBS : page + réglages mémorisés."""
        snap = self.snapshot()
        query = self.store.config.obs_query
        return snap.url + ("?" + query if query and snap.url else "")

    # ------------------------------------------------------------------ interne
    def _submit(self, coro) -> Future:  # type: ignore[no-untyped-def]
        assert self._loop is not None, "service non démarré"
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _update(self, **values: object) -> None:
        with self._lock:
            self._snapshot = Snapshot(**{**self._snapshot.__dict__, **values})

    async def _configure(self, host: str, web_port: int | None, obs_query: str | None) -> None:
        await self._stop_runtime()
        config = self.store.config
        changes: dict[str, object] = {}
        if host != config.ew_host:
            changes.update(ew_host=host, last_ip="")  # la dernière IP était celle de l'ancien PC
        if web_port is not None and web_port != config.web_port:
            changes["web_port"] = web_port
        if obs_query is not None and obs_query != config.obs_query:
            changes["obs_query"] = obs_query
        self.store.update(**changes)
        await self._restart()

    async def _restart(self) -> None:
        config = self.store.config
        self._update(configured=bool(config.ew_host), host=config.ew_host, url="", web_error="")
        if not config.ew_host:
            return
        self._hub = StateHub()
        self._server = WebServer(self._hub, config.web_bind, config.web_port)
        try:
            await self._server.start()
            self._update(url=self._server.url)
        except OSError as exc:
            log.error(
                "serveur web impossible sur %s:%d : %s", config.web_bind, config.web_port, exc
            )
            self._update(
                web_error="Le port %d est déjà utilisé (ou interdit) : choisissez un autre "
                "port pour la page." % config.web_port
            )
            self._server = None
        self._client = EwClient(
            config.ew_host,
            config.client_id,
            config.device_name,
            port=self._ew_port,
            last_ip=config.last_ip or None,
            grace_seconds=config.lost_grace_seconds,
            on_state=self._on_state,
            on_status=self._on_status,
            on_ip=lambda ip: self.store.update(last_ip=ip),
        )
        self._task = asyncio.ensure_future(self._client.run())

    async def _stop_runtime(self) -> None:
        if self._client is not None:
            self._client.stop()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, 3)
            except asyncio.TimeoutError:
                self._task.cancel()
            except Exception:  # noqa: BLE001 - le client ne doit pas empêcher l'arrêt
                log.exception("arrêt du client")
        if self._server is not None:
            await self._server.stop()
        self._client = self._task = self._server = None

    def _on_state(self, state: LiveState) -> None:
        self._hub.publish(state)
        self._update(state=state)

    def _on_status(self, status: ConnectionStatus, detail: str) -> None:
        self._update(status=status, detail=detail)
