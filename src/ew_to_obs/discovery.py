"""Retrouver EasyWorship sur le réseau : résolution du nom, port TCP par mDNS, connexion.

EW attribue lui-même le port de la télécommande (il change à chaque lancement) et l'annonce par
mDNS (`_ezwremote._tcp.local`). Constats des captures (`doc/protocole_easyworship.md` §12 et §14) :

* l'IPv6 ne répond jamais côté EW : IPv4 d'abord, IPv6 en dernier recours seulement ;
* le nom n'est résolu qu'en IPv4 (pas de requête AAAA, qui attend un délai sur un nom ".local") ;
* les adresses sont interrogées en parallèle, jamais l'une après l'autre.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import struct
from dataclasses import dataclass

log = logging.getLogger("ew_to_obs.discovery")

MDNS_PORT = 5353
MDNS_SERVICE = "_ezwremote._tcp.local"


class DiscoveryError(OSError):
    """Nom non résolu, port introuvable ou connexion impossible."""


@dataclass(frozen=True)
class Target:
    family: int
    ip: str
    sockaddr: tuple


# --------------------------------------------------------------------------------------------
# Résolution du nom
# --------------------------------------------------------------------------------------------
async def resolve(host: str, port: int, socktype: int = socket.SOCK_STREAM) -> list[Target]:
    """Adresses de `host` : IPv4 seulement si le nom en a, sinon IPv6."""
    loop = asyncio.get_running_loop()
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            infos = await loop.getaddrinfo(host, port, family=family, type=socktype)
        except socket.gaierror:
            continue
        targets: list[Target] = []
        seen: set[str] = set()
        for fam, _, _, _, addr in infos:
            if fam == family and addr[0] not in seen:
                seen.add(addr[0])
                targets.append(Target(fam, addr[0], addr))
        if targets:
            return targets
    raise DiscoveryError("nom non résolu : %s" % host)


# --------------------------------------------------------------------------------------------
# mDNS (requête unicast, comme la V1)
# --------------------------------------------------------------------------------------------
def _encode_name(name: str) -> bytes:
    out = b""
    for label in name.strip(".").split("."):
        raw = label.encode("utf-8")
        out += bytes([len(raw)]) + raw
    return out + b"\0"


def _read_name(data: bytes, pos: int) -> tuple[str, int]:
    """Lit un nom DNS (avec compression). Renvoie (nom, position après le nom)."""
    labels: list[str] = []
    end: int | None = None
    hops = 0
    while True:
        if pos >= len(data):
            raise ValueError("nom DNS tronqué")
        n = data[pos]
        if n == 0:
            pos += 1
            break
        if n & 0xC0 == 0xC0:
            if end is None:
                end = pos + 2
            pos = ((n & 0x3F) << 8) | data[pos + 1]
            hops += 1
            if hops > 20:
                raise ValueError("boucle de compression DNS")
            continue
        labels.append(data[pos + 1 : pos + 1 + n].decode("utf-8", "replace"))
        pos += 1 + n
    return ".".join(labels), (end if end is not None else pos)


def build_query(query_id: int | None = None) -> bytes:
    """Requête PTR `_ezwremote._tcp.local`, drapeau RD comme dnspython (V1)."""
    qid = query_id if query_id is not None else (int.from_bytes(os.urandom(2), "big") or 1)
    header = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)
    return header + _encode_name(MDNS_SERVICE) + struct.pack(">HH", 12, 1)


def parse_response(data: bytes) -> dict[str, list]:
    """Renvoie {'ptr': [cibles], 'srv': [(propriétaire, port, cible)]}."""
    _, _, qdcount, ancount, nscount, arcount = struct.unpack(">HHHHHH", data[:12])
    pos = 12
    for _ in range(qdcount):
        _, pos = _read_name(data, pos)
        pos += 4
    result: dict[str, list] = {"ptr": [], "srv": []}
    for _ in range(ancount + nscount + arcount):
        owner, pos = _read_name(data, pos)
        rtype, _, _, rdlen = struct.unpack(">HHIH", data[pos : pos + 10])
        rdata = pos + 10
        if rtype == 12:
            target, _ = _read_name(data, rdata)
            result["ptr"].append(target)
        elif rtype == 33:
            port = struct.unpack(">H", data[rdata + 4 : rdata + 6])[0]
            target, _ = _read_name(data, rdata + 6)
            result["srv"].append((owner, port, target))
        pos = rdata + rdlen
    return result


def _port_from_response(data: bytes) -> int | None:
    try:
        parsed = parse_response(data)
    except (ValueError, struct.error, IndexError):
        return None
    for owner, port, _ in parsed["srv"]:
        if owner in parsed["ptr"]:
            return port
    return parsed["srv"][0][1] if parsed["srv"] else None


class _Query(asyncio.DatagramProtocol):
    def __init__(self, query: bytes, answer: asyncio.Future, ip: str, errors: list[str]) -> None:
        self._query = query
        self._answer = answer
        self._ip = ip
        self._errors = errors

    def connection_made(self, transport) -> None:  # type: ignore[no-untyped-def]
        transport.sendto(self._query)

    def datagram_received(self, data: bytes, addr) -> None:  # type: ignore[no-untyped-def]
        port = _port_from_response(data)
        if port is not None and not self._answer.done():
            self._answer.set_result((port, self._ip))

    def error_received(self, exc: Exception) -> None:
        self._errors.append("%s : %s" % (self._ip, exc))


async def discover_port(
    targets: list[Target],
    mdns_port: int = MDNS_PORT,
    timeout: float = 3.0,
    attempts: int = 2,
) -> tuple[int, str]:
    """Port TCP de la télécommande et IP qui a répondu. Toutes les adresses sont interrogées en
    parallèle, la première réponse gagne."""
    loop = asyncio.get_running_loop()
    errors: list[str] = []
    for _ in range(attempts):
        answer: asyncio.Future = loop.create_future()
        query = build_query()
        transports = []
        try:
            for target in targets:
                try:
                    transport, _ = await loop.create_datagram_endpoint(
                        lambda t=target, q=query, f=answer: _Query(q, f, t.ip, errors),
                        remote_addr=(target.ip, mdns_port),
                        family=target.family,
                    )
                    transports.append(transport)
                except OSError as exc:
                    errors.append("%s : %s" % (target.ip, exc))
            try:
                return await asyncio.wait_for(answer, timeout)
            except asyncio.TimeoutError:
                errors.append("aucune réponse en %.0f s de %s" % (timeout, [t.ip for t in targets]))
        finally:
            for transport in transports:
                transport.close()
    raise DiscoveryError("; ".join(errors) or "aucune réponse mDNS")


# --------------------------------------------------------------------------------------------
# Connexion TCP
# --------------------------------------------------------------------------------------------
async def open_connection(
    targets: list[Target],
    port: int,
    first_ip: str | None = None,
    timeout: float = 3.0,
    total: float = 10.0,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, str]:
    """Connexion TCP : l'IP qui a répondu au mDNS d'abord, 3 s par adresse, 10 s au total."""
    ordered = sorted(targets, key=lambda t: 0 if t.ip == first_ip else 1)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + total
    errors: list[str] = []
    for target in ordered:
        left = deadline - loop.time()
        if left <= 0:
            break
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(target.ip, port, family=target.family),
                min(timeout, left),
            )
            return reader, writer, target.ip
        except (OSError, asyncio.TimeoutError) as exc:
            errors.append("%s : %s" % (target.ip, exc or "délai dépassé"))
    raise DiscoveryError("connexion impossible : " + "; ".join(errors))
