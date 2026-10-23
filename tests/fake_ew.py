"""Faux EasyWorship pour les tests : serveur TCP local qui parle le protocole de la télécommande."""

from __future__ import annotations

import asyncio
import contextlib

from ew_to_obs.protocol import FrameDecoder, encode, encode_live_data


class FakeEw:
    def __init__(self, paired: bool = True, chunk: int = 0) -> None:
        self.paired = paired
        self.chunk = chunk  # >0 : envoie les octets par morceaux de cette taille
        self.port = 0
        self.liverev = 100
        self.pres_rowid = 1
        self.slides: dict[int, str] = {}
        self.current = 0
        self.flags = {"logo": False, "black": False, "clear": False}
        self.heartbeats = 0
        self.connects: list[dict] = []
        self.requests: list[dict] = []
        self._writers: list[asyncio.StreamWriter] = []
        self._server: asyncio.Server | None = None

    async def start(self, port: int = 0) -> int:
        self._server = await asyncio.start_server(self._client, "127.0.0.1", port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        await self.kick()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def kick(self) -> None:
        """Ferme toutes les connexions sans message, comme EW qui quitte ou révoque l'appairage."""
        for writer in list(self._writers):
            writer.close()
        self._writers.clear()
        await asyncio.sleep(0)

    # ------------------------------------------------------------------ côté opérateur EW
    async def go_live(
        self, slides: dict[int, str], current: int, liverev: int | None = None
    ) -> None:
        self.slides = dict(slides)
        self.current = current
        self.liverev = liverev if liverev is not None else self.liverev + 1
        await self._broadcast(self._status())

    async def select(self, rowid: int) -> None:
        self.current = rowid
        await self._broadcast(self._status())

    async def set_flag(self, name: str, value: bool) -> None:
        self.flags[name] = value
        await self._broadcast(self._status())

    async def accept_pairing(self) -> None:
        self.paired = True
        for writer in list(self._writers):
            await self._send(writer, {"action": "paired", "requestrev": "0"})
            await self._send(writer, self._status())

    # ------------------------------------------------------------------ protocole
    def _status(self) -> dict:
        return {
            "action": "status",
            **self.flags,
            "rectype": 1,
            "pres_rowid": str(self.pres_rowid),
            "slide_rowid": str(self.current),
            "liverev": str(self.liverev),
            "imagehash": "h%d" % self.current if self.slides else "",
            "permissions": 0,
            "requestrev": "0",
        }

    async def _send(self, writer: asyncio.StreamWriter, message: dict, extra: bytes = b"") -> None:
        if extra:
            message = {**message, "size": len(extra)}
        data = encode(message) + extra
        step = self.chunk or len(data)
        for i in range(0, len(data), step):
            writer.write(data[i : i + step])
            await writer.drain()
            if self.chunk:
                await asyncio.sleep(0)

    async def _broadcast(self, message: dict) -> None:
        for writer in list(self._writers):
            with contextlib.suppress(OSError):
                await self._send(writer, message)

    async def _client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._writers.append(writer)
        decoder = FrameDecoder()
        try:
            while data := await reader.read(4096):
                for frame in decoder.feed(data):
                    await self._handle(frame.message or {}, writer)
        except (OSError, asyncio.CancelledError):
            pass
        finally:
            if writer in self._writers:
                self._writers.remove(writer)
            writer.close()

    async def _handle(self, message: dict, writer: asyncio.StreamWriter) -> None:
        action = message.get("action")
        if action == "connect":
            self.connects.append(message)
            if self.paired:
                await self._send(writer, {"action": "paired", "requestrev": "0"})
                await self._send(writer, self._status())
            else:
                await self._send(writer, {"action": "notPaired", "requestrev": "0"})
        elif action == "heartbeat":
            self.heartbeats += 1
        elif action == "GetLiveData" and self.paired:
            self.requests.append(message)
            body = encode_live_data(
                self.liverev, self.pres_rowid, [(r, r * 10) for r in self.slides]
            )
            await self._send(writer, {"action": "LiveData"}, body)
        elif action == "getSlideInfo" and self.paired:
            self.requests.append(message)
            rowid = int(message["slide_rowid"])
            if rowid in self.slides:
                await self._send(
                    writer,
                    {
                        "action": "slideInfo",
                        "slide_rowid": str(rowid),
                        "revision": str(rowid * 10),
                        "title": "",
                        "content": self.slides[rowid],
                    },
                )
