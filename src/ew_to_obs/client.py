"""Client asynchrone de la télécommande EasyWorship.

Se connecte à EW, suit la diapo en direct et publie un `LiveState` à chaque changement. Gère :

* la découverte du port à **chaque** tentative (le port change à chaque lancement d'EW) ;
* l'attente de l'appairage (`notPaired` : l'opérateur doit accepter sur le PC EW) ;
* la reconnexion automatique, la première tentative étant immédiate ;
* un délai de grâce : à la perte de connexion le dernier texte reste affiché, et l'état ne passe à
  caché qu'au bout de `grace_seconds`, pour que les micro-coupures ne fassent pas clignoter OBS.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import sys
import warnings
from collections.abc import Awaitable, Callable, Sequence
from enum import Enum

from .discovery import (
    MDNS_PORT,
    DiscoveryError,
    Target,
    discover_port,
    open_connection,
    resolve,
)
from .live import LiveSession, LiveState, Pairing
from .protocol import FrameDecoder, connect_message, encode, heartbeat_message

log = logging.getLogger("ew_to_obs.client")

DEFAULT_BACKOFF = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0)


class ConnectionStatus(Enum):
    SEARCHING = "searching"  # résolution du nom, découverte du port, connexion
    WAITING_PAIRING = "waiting_pairing"  # EW attend l'acceptation de la télécommande
    CONNECTED = "connected"
    LOST = "lost"  # coupure, EW fermé ou appairage révoqué : nouvel essai programmé
    STOPPED = "stopped"


class ConnectionLost(Exception):
    pass


class Backoff:
    """Attente entre deux tentatives : immédiate d'abord, puis croissante jusqu'à 10 s."""

    def __init__(self, delays: Sequence[float] = DEFAULT_BACKOFF) -> None:
        self._delays = tuple(delays)
        self._index = 0

    def next(self) -> float:
        delay = self._delays[min(self._index, len(self._delays) - 1)]
        self._index += 1
        return delay

    def reset(self) -> None:
        self._index = 0


def _windows_keepalive(sock: socket.socket, idle: int, interval: int) -> None:
    """Repli pour Windows sans constantes TCP_KEEP* : SIO_KEEPALIVE_VALS, sur un doublon du socket
    (le socket d'asyncio n'expose pas `ioctl`). Les réglages portent sur la même connexion."""
    real = sock.dup()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            real.ioctl(socket.SIO_KEEPALIVE_VALS, (1, idle * 1000, interval * 1000))  # type: ignore[attr-defined]
    finally:
        real.close()


def enable_keepalive(
    sock: socket.socket | None, idle: int = 10, interval: int = 3, count: int = 3
) -> None:
    """TCP keepalive pour détecter une coupure silencieuse (aucun EOF reçu). Au mieux selon l'OS."""
    if sock is None:
        return
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "TCP_KEEPIDLE"):  # Linux, Windows récent
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)
        elif hasattr(socket, "TCP_KEEPALIVE"):  # macOS
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, idle)
        elif sys.platform == "win32":
            _windows_keepalive(sock, idle, interval)
            return
        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)
    except (OSError, AttributeError, ValueError) as exc:
        log.debug("keepalive TCP indisponible : %s", exc)


class EwClient:
    def __init__(
        self,
        host: str,
        client_id: str,
        device_name: str = "ew to obs",
        *,
        port: int | None = None,
        last_ip: str | None = None,
        mdns_port: int = MDNS_PORT,
        grace_seconds: float = 2.0,
        heartbeat_interval: float = 3.0,
        backoff: Sequence[float] = DEFAULT_BACKOFF,
        on_state: Callable[[LiveState], None] | None = None,
        on_status: Callable[[ConnectionStatus, str], None] | None = None,
        on_ip: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self.client_id = client_id
        self.device_name = device_name
        self.port = port  # imposé seulement pour les tests et le diagnostic
        self.last_ip = last_ip  # dernière IPv4 qui a fonctionné, tentée en premier
        self._mdns_port = mdns_port
        self._grace = grace_seconds
        self._hb_interval = heartbeat_interval
        self._backoff = Backoff(backoff)
        self._on_state = on_state
        self._on_status = on_status
        self._on_ip = on_ip
        self.published = LiveState.hidden()
        self.status = ConnectionStatus.SEARCHING
        self._grace_handle: asyncio.TimerHandle | None = None
        self._stopping = False
        self._wake = asyncio.Event()
        self._writer: asyncio.StreamWriter | None = None
        self._tasks: set[asyncio.Task] = set()

    # ---------------------------------------------------------------- cycle de vie
    async def run(self) -> None:
        """Boucle principale : tourne jusqu'à `stop()` ou l'annulation de la tâche."""
        try:
            while not self._stopping:
                try:
                    await self._connect_and_serve()
                    reason = "connexion terminée"
                except asyncio.CancelledError:
                    raise
                except (OSError, ConnectionLost, asyncio.TimeoutError) as exc:
                    reason = str(exc) or exc.__class__.__name__
                if self._stopping:
                    break
                delay = self._backoff.next()
                log.info("connexion perdue (%s) ; nouvel essai dans %.1f s", reason, delay)
                self._start_grace()
                self._set_status(
                    ConnectionStatus.LOST, "%s ; nouvel essai dans %.1f s" % (reason, delay)
                )
                await self._sleep(delay)
        finally:
            self._cancel_grace()
            self._publish(LiveState.hidden())
            self._set_status(ConnectionStatus.STOPPED, "")

    def stop(self) -> None:
        self._stopping = True
        self._wake.set()
        if self._writer is not None:
            self._writer.close()

    async def _sleep(self, delay: float) -> None:
        if delay <= 0:
            await asyncio.sleep(0)
            return
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._wake.wait(), delay)

    # ---------------------------------------------------------------- connexion
    async def _connect_and_serve(self) -> None:
        self._set_status(ConnectionStatus.SEARCHING, self.host)
        reader, writer, ip, fast = await self._open()
        self._writer = writer
        if ip != self.last_ip:
            self.last_ip = ip
            if self._on_ip is not None and ip.count(".") == 3:
                self._on_ip(ip)
        if fast:
            self._spawn(self._refresh_ip())
        await self._serve(reader, writer)

    async def _open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, str, bool]:
        """Ouvre la connexion TCP : la dernière IP connue d'abord (rapide), sinon le nom résolu."""
        if self.last_ip:
            fast_targets = [Target(socket.AF_INET, self.last_ip, (self.last_ip, 0))]
            try:
                return (*await self._open_via(fast_targets, timeout=1.0, attempts=1), True)
            except DiscoveryError as exc:
                log.info("dernière IP connue (%s) injoignable : %s", self.last_ip, exc)
        targets = await resolve(self.host, self._mdns_port, socket.SOCK_DGRAM)
        return (*await self._open_via(targets, timeout=3.0, attempts=2), False)

    async def _open_via(
        self, targets: list[Target], timeout: float, attempts: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, str]:
        if self.port is None:
            port, via = await discover_port(targets, self._mdns_port, timeout, attempts)
        else:
            port, via = self.port, None
        log.info("EasyWorship sur le port %d", port)
        return await open_connection(targets, port, first_ip=via, timeout=max(timeout, 1.5))

    async def _refresh_ip(self) -> None:
        """Après une connexion rapide par IP mémorisée : re-résout le nom pour suivre un changement
        d'adresse (DHCP)."""
        try:
            targets = await asyncio.wait_for(resolve(self.host, self._mdns_port), 10)
        except (OSError, asyncio.TimeoutError):
            return
        if self.last_ip not in {t.ip for t in targets}:
            self.last_ip = targets[0].ip
            if self._on_ip is not None:
                self._on_ip(self.last_ip)

    def _spawn(self, coro: Awaitable) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        enable_keepalive(writer.get_extra_info("socket"))
        session = LiveSession()
        decoder = FrameDecoder()
        writer.write(encode(connect_message(self.client_id, self.device_name)))
        heartbeat = asyncio.ensure_future(self._heartbeat(writer))
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    raise ConnectionLost(
                        "connexion fermée (par EasyWorship ou coupure du réseau local)"
                    )
                for frame in decoder.feed(data):
                    self._handle(frame.message, frame.extra, session, writer)
        finally:
            heartbeat.cancel()
            writer.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(writer.wait_closed(), 1)

    async def _heartbeat(self, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                await asyncio.sleep(self._hb_interval)
                writer.write(encode(heartbeat_message()))
                await asyncio.wait_for(writer.drain(), 5)
        except (OSError, asyncio.TimeoutError):
            writer.transport.abort()  # la lecture en cours échoue et déclenche la reconnexion

    def _handle(
        self, message: dict | None, extra: bytes, session: LiveSession, writer: asyncio.StreamWriter
    ) -> None:
        if message is None:
            log.debug("ligne illisible ignorée")
            return
        before = session.pairing
        result = session.on_message(message, extra)
        for outgoing in result.send:
            writer.write(encode(outgoing))
        if session.pairing != before:
            self._on_pairing(session.pairing)
        if result.state is not None:
            self._publish(result.state)

    def _on_pairing(self, pairing: Pairing) -> None:
        if pairing is Pairing.PAIRED:
            self._cancel_grace()
            self._backoff.reset()
            self._set_status(ConnectionStatus.CONNECTED, "")
        elif pairing is Pairing.NOT_PAIRED:
            self._set_status(
                ConnectionStatus.WAITING_PAIRING,
                "acceptez la télécommande « %s » sur le PC EasyWorship" % self.device_name,
            )

    # ---------------------------------------------------------------- sortie
    def _publish(self, state: LiveState) -> None:
        if state == self.published:
            return
        self.published = state
        # jamais le texte : le journal peut être joint à un rapport (recette, diagnostic)
        log.info("état publié : visible=%s, %d caractères", state.visible, len(state.text))
        if self._on_state is not None:
            self._on_state(state)

    def _start_grace(self) -> None:
        if self._grace_handle is None and self.published.visible:
            self._grace_handle = asyncio.get_running_loop().call_later(self._grace, self._hide)

    def _hide(self) -> None:
        self._grace_handle = None
        self._publish(LiveState.hidden())

    def _cancel_grace(self) -> None:
        if self._grace_handle is not None:
            self._grace_handle.cancel()
            self._grace_handle = None

    def _set_status(self, status: ConnectionStatus, detail: str) -> None:
        self.status = status
        log.info("état : %s %s", status.value, detail)
        if self._on_status is not None:
            self._on_status(status, detail)
