import asyncio
import socket
import struct
import time

import pytest

from ew_to_obs import discovery
from ew_to_obs.client import EwClient
from ew_to_obs.discovery import DiscoveryError, Target, build_query, discover_port, parse_response
from ew_to_obs.live import LiveState
from fake_ew import FakeEw


def run(coro, timeout=15):
    return asyncio.run(asyncio.wait_for(coro, timeout))


def fake_response(query: bytes, tcp_port: int) -> bytes:
    """Réponse « legacy unicast » : écho de l'id et de la question, PTR + SRV, noms compressés."""
    pkt = query[:2] + struct.pack(">HHHHH", 0x8400, 1, 1, 0, 1) + query[12:]
    inst = bytes([8]) + b"PC-REGIE" + b"\xc0\x0c"  # pointeur vers le nom du service (offset 12)
    pkt += b"\xc0\x0c" + struct.pack(">HHIH", 12, 1, 120, len(inst))
    inst_off = len(pkt)
    pkt += inst
    srv = struct.pack(">HHH", 0, 0, tcp_port) + discovery._encode_name("PC-REGIE.local")
    pkt += struct.pack(">H", 0xC000 | inst_off) + struct.pack(">HHIH", 33, 1, 120, len(srv)) + srv
    return pkt


class Responder(asyncio.DatagramProtocol):
    def __init__(self, tcp_port: int | None) -> None:
        self.tcp_port = tcp_port  # None : répondeur muet
        self.queries = 0

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data, addr) -> None:
        self.queries += 1
        if self.tcp_port is not None:
            self.transport.sendto(fake_response(data, self.tcp_port), addr)


async def responder(tcp_port, host="127.0.0.1", port=0):
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(
        lambda: Responder(tcp_port), local_addr=(host, port), family=socket.AF_INET
    )
    return transport, proto, transport.get_extra_info("sockname")[1]


def test_query_and_compressed_response_roundtrip():
    parsed = parse_response(fake_response(build_query(4242), 51234))
    assert parsed["ptr"] == ["PC-REGIE._ezwremote._tcp.local"]
    assert parsed["srv"] == [("PC-REGIE._ezwremote._tcp.local", 51234, "PC-REGIE.local")]


def test_discover_port_returns_port_and_answering_ip():
    async def scenario():
        transport, proto, udp = await responder(54321)
        targets = [Target(socket.AF_INET, "127.0.0.1", ("127.0.0.1", udp))]
        assert await discover_port(targets, udp, timeout=2) == (54321, "127.0.0.1")
        transport.close()

    run(scenario())


def test_silent_address_before_the_good_one_does_not_delay_the_answer():
    async def scenario():
        good, _, udp = await responder(54321, "127.0.0.1")
        try:
            silent, _, _ = await responder(None, "127.0.0.2", udp)
        except OSError:
            good.close()
            pytest.skip("127.0.0.2 indisponible")
        targets = [
            Target(socket.AF_INET, "127.0.0.2", ("127.0.0.2", udp)),  # muette, en premier
            Target(socket.AF_INET, "127.0.0.1", ("127.0.0.1", udp)),
        ]
        start = time.monotonic()
        port, via = await discover_port(targets, udp, timeout=3)
        assert (port, via) == (54321, "127.0.0.1")
        assert time.monotonic() - start < 1.0  # et non 3 s
        good.close()
        silent.close()

    run(scenario())


def test_discover_port_fails_cleanly_when_nobody_answers():
    async def scenario():
        transport, _, udp = await responder(None)
        targets = [Target(socket.AF_INET, "127.0.0.1", ("127.0.0.1", udp))]
        with pytest.raises(DiscoveryError):
            await discover_port(targets, udp, timeout=0.2, attempts=2)
        transport.close()

    run(scenario())


def test_resolve_prefers_ipv4_and_skips_ipv6_lookup(monkeypatch):
    calls = []

    async def fake_getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
        calls.append(family)
        if family == socket.AF_INET:
            return [(socket.AF_INET, type, 6, "", ("192.168.1.78", port))]
        return [(socket.AF_INET6, type, 6, "", ("fe80::1", port, 0, 0))]

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", fake_getaddrinfo)
    targets = run(discovery.resolve("pc.local", 5353))
    assert [t.ip for t in targets] == ["192.168.1.78"]
    assert calls == [socket.AF_INET]  # aucune requête IPv6


def test_resolve_falls_back_to_ipv6_only_without_ipv4(monkeypatch):
    async def fake_getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET:
            raise socket.gaierror("pas d'IPv4")
        return [(socket.AF_INET6, type, 6, "", ("fe80::1", port, 0, 0))]

    monkeypatch.setattr(asyncio.BaseEventLoop, "getaddrinfo", fake_getaddrinfo)
    assert [t.ip for t in run(discovery.resolve("pc.local", 5353))] == ["fe80::1"]


def test_resolve_unknown_name_is_a_discovery_error():
    with pytest.raises(DiscoveryError):
        run(discovery.resolve("nom-inexistant.invalid", 5353))


def test_client_finds_the_port_by_mdns_and_follows_the_slide():
    async def scenario():
        ew = FakeEw()
        tcp_port = await ew.start()
        await ew.go_live({1: "via mdns"}, current=1)
        transport, _, udp = await responder(tcp_port)
        states = []
        client = EwClient(
            "127.0.0.1", "uid", mdns_port=udp, on_state=states.append, backoff=(0.0, 0.05)
        )
        task = asyncio.ensure_future(client.run())
        for _ in range(300):
            if states:
                break
            await asyncio.sleep(0.01)
        client.stop()
        await asyncio.wait_for(task, 3)
        assert states[0] == LiveState(True, "via mdns")
        assert client.last_ip == "127.0.0.1"
        transport.close()
        await ew.stop()

    run(scenario())


def test_last_known_ip_is_used_first_even_if_the_name_does_not_resolve():
    async def scenario():
        ew = FakeEw()
        tcp_port = await ew.start()
        await ew.go_live({1: "rapide"}, current=1)
        transport, _, udp = await responder(tcp_port)
        states, ips = [], []
        client = EwClient(
            "nom-inexistant.invalid",
            "uid",
            last_ip="127.0.0.1",
            mdns_port=udp,
            on_state=states.append,
            on_ip=ips.append,
            backoff=(0.0, 0.05),
        )
        task = asyncio.ensure_future(client.run())
        for _ in range(300):
            if states:
                break
            await asyncio.sleep(0.01)
        client.stop()
        await asyncio.wait_for(task, 3)
        assert states[0] == LiveState(True, "rapide")
        transport.close()
        await ew.stop()

    run(scenario())


def test_stale_last_ip_falls_back_to_the_name():
    async def scenario():
        ew = FakeEw()
        tcp_port = await ew.start()
        await ew.go_live({1: "repli"}, current=1)
        transport, _, udp = await responder(tcp_port)
        states, ips = [], []
        client = EwClient(
            "127.0.0.1",
            "uid",
            last_ip="192.0.2.1",  # TEST-NET : injoignable (ancienne adresse DHCP)
            mdns_port=udp,
            on_state=states.append,
            on_ip=ips.append,
            backoff=(0.0, 0.05),
        )
        task = asyncio.ensure_future(client.run())
        for _ in range(500):
            if states:
                break
            await asyncio.sleep(0.01)
        client.stop()
        await asyncio.wait_for(task, 3)
        assert states[0] == LiveState(True, "repli")
        assert ips[-1] == "127.0.0.1"  # nouvelle IP signalée pour être mémorisée
        transport.close()
        await ew.stop()

    run(scenario())
