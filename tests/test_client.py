"""EwClient contre un faux EW sur un vrai socket TCP local."""

import asyncio
import contextlib

import pytest

from ew_to_obs.client import ConnectionStatus, EwClient
from ew_to_obs.live import LiveState
from fake_ew import FakeEw

FAST = (0.0, 0.02, 0.05, 0.1)


def run(coro, timeout=15):
    return asyncio.run(asyncio.wait_for(coro, timeout))


class Harness:
    def __init__(self, ew, **options):
        self.states: list[LiveState] = []
        self.statuses: list[ConnectionStatus] = []
        options.setdefault("heartbeat_interval", 0.05)
        options.setdefault("backoff", FAST)
        self.client = EwClient(
            "127.0.0.1",
            "uid-test",
            "test",
            port=ew.port,
            on_state=self.states.append,
            on_status=lambda status, detail: self.statuses.append(status),
            **options,
        )
        self.task = None

    async def __aenter__(self):
        self.task = asyncio.ensure_future(self.client.run())
        return self

    async def __aexit__(self, *exc):
        self.client.stop()
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(self.task, 3)

    async def until(self, predicate, timeout=5):
        end = asyncio.get_running_loop().time() + timeout
        while not predicate():
            if asyncio.get_running_loop().time() > end:
                raise AssertionError(
                    "condition non atteinte : états=%r statuts=%r" % (self.states, self.statuses)
                )
            await asyncio.sleep(0.01)


def test_follows_the_live_slide_and_hides_on_logo():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "un", 2: "deux\r\nlignes"}, current=1)
        async with Harness(ew) as h:
            await h.until(lambda: h.states == [LiveState(True, "un")])
            await ew.select(2)
            await h.until(lambda: h.states[-1] == LiveState(True, "deux\nlignes"))
            await ew.set_flag("logo", True)
            await h.until(lambda: h.states[-1] == LiveState.hidden())
            await ew.set_flag("logo", False)
            await h.until(lambda: h.states[-1] == LiveState(True, "deux\nlignes"))
            assert ew.connects[0]["uid"] == "uid-test"
            assert h.client.status is ConnectionStatus.CONNECTED
        await ew.stop()

    run(scenario())


def test_heartbeats_are_sent():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        async with Harness(ew) as h:
            await h.until(lambda: ew.heartbeats >= 3)
        await ew.stop()

    run(scenario())


def test_messages_split_in_single_bytes_over_real_tcp():
    async def scenario():
        ew = FakeEw(chunk=1)
        await ew.start()
        await ew.go_live({1: "émojis 😁 et accents é"}, current=1)
        async with Harness(ew) as h:
            await h.until(
                lambda: h.states == [LiveState(True, "émojis 😁 et accents é")], timeout=10
            )
        await ew.stop()

    run(scenario())


def test_waits_for_pairing_then_publishes():
    async def scenario():
        ew = FakeEw(paired=False)
        await ew.start()
        await ew.go_live({1: "texte"}, current=1)
        async with Harness(ew) as h:
            await h.until(lambda: ConnectionStatus.WAITING_PAIRING in h.statuses)
            before = ew.heartbeats
            await h.until(
                lambda: ew.heartbeats >= before + 2
            )  # reste connecté, heartbeats maintenus
            assert h.states == []
            await ew.accept_pairing()
            await h.until(lambda: h.states == [LiveState(True, "texte")])
            assert h.client.status is ConnectionStatus.CONNECTED
        await ew.stop()

    run(scenario())


def test_micro_cut_does_not_blink():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "stable"}, current=1)
        async with Harness(ew, grace_seconds=1.0) as h:
            await h.until(lambda: h.states == [LiveState(True, "stable")])
            await ew.kick()  # EW ferme la connexion, mais reste joignable
            await h.until(lambda: len(ew.connects) == 2)  # reconnexion immédiate
            await h.until(lambda: h.client.status is ConnectionStatus.CONNECTED)
            await asyncio.sleep(1.3)  # plus que le délai de grâce
            assert h.states == [LiveState(True, "stable")]  # jamais masqué
            assert ConnectionStatus.LOST in h.statuses
        await ew.stop()

    run(scenario())


def test_long_loss_hides_after_grace_then_recovers_on_new_port():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "avant"}, current=1)
        async with Harness(ew, grace_seconds=0.3) as h:
            await h.until(lambda: h.states == [LiveState(True, "avant")])
            await ew.stop()  # EW fermé : plus personne n'écoute
            await h.until(lambda: h.states[-1] == LiveState.hidden())
            assert h.client.status is ConnectionStatus.LOST
            # EW relancé : même client, mais cette fois le port a changé
            ew2 = FakeEw()
            await ew2.start()
            await ew2.go_live({7: "après"}, current=7)
            h.client.port = ew2.port
            await h.until(lambda: h.states[-1] == LiveState(True, "après"))
            await ew2.stop()

    run(scenario())


def test_revoked_pairing_waits_again_and_hides_after_grace():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "secret"}, current=1)
        async with Harness(ew, grace_seconds=0.3) as h:
            await h.until(lambda: h.states == [LiveState(True, "secret")])
            ew.paired = False  # appairage révoqué dans EW
            await ew.kick()
            await h.until(lambda: ConnectionStatus.WAITING_PAIRING in h.statuses)
            await h.until(lambda: h.states[-1] == LiveState.hidden())
            await ew.accept_pairing()
            await h.until(lambda: h.states[-1] == LiveState(True, "secret"))
        await ew.stop()

    run(scenario())


def test_stop_hides_output_and_ends_run():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "x"}, current=1)
        h = Harness(ew)
        async with h:
            await h.until(lambda: h.states == [LiveState(True, "x")])
        assert h.states[-1] == LiveState.hidden()
        assert h.client.status is ConnectionStatus.STOPPED
        await ew.stop()

    run(scenario())


def test_unreachable_ew_keeps_retrying_without_crashing():
    async def scenario():
        ew = FakeEw()
        await ew.start()
        port = ew.port
        await ew.stop()  # port fermé
        h = Harness(ew)
        h.client.port = port
        async with h:
            await h.until(lambda: h.statuses.count(ConnectionStatus.LOST) >= 3)
            assert h.states == []

    run(scenario())


@pytest.mark.parametrize("grace", [0.0])
def test_zero_grace_hides_immediately(grace):
    async def scenario():
        ew = FakeEw()
        await ew.start()
        await ew.go_live({1: "a"}, current=1)
        async with Harness(ew, grace_seconds=grace) as h:
            await h.until(lambda: h.states == [LiveState(True, "a")])
            await ew.stop()
            await h.until(lambda: h.states[-1] == LiveState.hidden())

    run(scenario())
