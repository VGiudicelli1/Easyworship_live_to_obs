"""La page d'affichage dans un vrai navigateur (Chromium via Playwright).

Ignorés quand Playwright ou Chromium sont absents (CI) : `pip install playwright` puis
`playwright install chromium` pour les lancer.
"""

import asyncio
import threading

import pytest

from ew_to_obs.live import LiveState
from ew_to_obs.web import StateHub, WebServer

LONG = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 17  # ≈ 990 caractères


class BackgroundServer:
    """Le serveur dans son propre thread : Playwright (API synchrone) garde le thread des tests."""

    def __init__(self):
        self.hub = StateHub()
        self.loop = asyncio.new_event_loop()
        self.server = None
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def _call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(10)

    def start(self, port=0):
        self.server = WebServer(self.hub, "127.0.0.1", port)
        self._call(self.server.start())
        return self.server.port

    def stop(self):
        if self.server is not None:
            self._call(self.server.stop())
            self.server = None

    def publish(self, state):
        self.loop.call_soon_threadsafe(self.hub.publish, state)

    def close(self):
        self.stop()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except Exception as exc:  # noqa: BLE001
            pytest.skip("Chromium indisponible : %s" % str(exc)[:80])
        yield instance
        instance.close()


@pytest.fixture
def server():
    background = BackgroundServer()
    background.port = background.start()
    yield background
    background.close()


def open_page(browser, server, query="", width=1280, height=720):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.goto("http://127.0.0.1:%d/%s" % (server.port, query))
    return page


def shown(page, text):
    page.wait_for_function(
        "t => { const b = document.getElementById('text');"
        " return !b.hidden && b.textContent === t }",
        arg=text,
        timeout=5000,
    )


def hidden(page):
    page.wait_for_function("document.getElementById('text').hidden", timeout=5000)


def metrics(page):
    return page.evaluate(
        """() => {
          const b = document.getElementById('text'), r = b.getBoundingClientRect();
          return {font: parseFloat(getComputedStyle(b).fontSize), overflow:
                  b.scrollHeight > b.clientHeight + 1 || b.scrollWidth > b.clientWidth + 1,
                  left: r.left, top: r.top, right: r.right, bottom: r.bottom,
                  vw: innerWidth, vh: innerHeight};
        }"""
    )


def test_shows_and_hides_the_live_text(browser, server):
    page = open_page(browser, server)
    hidden(page)
    server.publish(LiveState(True, "Dieu est amour"))
    shown(page, "Dieu est amour")
    server.publish(LiveState.hidden())
    hidden(page)
    server.publish(LiveState(True, ""))  # diapo vide : rien à afficher
    page.wait_for_timeout(200)
    assert page.evaluate("document.getElementById('text').hidden")
    page.close()


def test_state_published_before_the_page_opened_is_shown_at_once(browser, server):
    server.publish(LiveState(True, "déjà en direct"))
    page = open_page(browser, server)
    shown(page, "déjà en direct")
    page.close()


@pytest.mark.parametrize("size", [(1920, 1080), (1280, 720), (854, 480), (640, 360)])
def test_long_text_always_fits_inside_the_screen(browser, server, size):
    page = open_page(browser, server, width=size[0], height=size[1])
    server.publish(LiveState(True, LONG))
    shown(page, LONG)
    m = metrics(page)
    assert not m["overflow"], m
    assert 0 <= m["left"] and m["right"] <= m["vw"] and 0 <= m["top"] and m["bottom"] <= m["vh"], m
    page.close()


def test_when_there_is_really_no_room_the_text_is_clipped_but_never_leaves_the_screen(
    browser, server
):
    page = open_page(browser, server, width=320, height=180)  # 990 caractères n'y tiennent pas
    server.publish(LiveState(True, LONG))
    shown(page, LONG)
    m = metrics(page)
    assert m["font"] == 8  # police minimale
    assert 0 <= m["left"] and m["right"] <= m["vw"] and 0 <= m["top"] and m["bottom"] <= m["vh"], m
    page.close()


def test_short_text_is_big_and_bigger_screens_give_bigger_text(browser, server):
    sizes = []
    for width, height in ((640, 360), (1920, 1080)):
        page = open_page(browser, server, width=width, height=height)
        server.publish(LiveState(True, "Amen"))
        shown(page, "Amen")
        sizes.append(metrics(page)["font"])
        page.close()
        server.publish(LiveState.hidden())
    assert sizes[0] > 60 and sizes[1] > sizes[0] * 2, sizes


def test_text_shrinks_when_there_is_more_of_it_and_the_window_is_resized(browser, server):
    page = open_page(browser, server)
    server.publish(LiveState(True, "Court"))
    shown(page, "Court")
    short = metrics(page)["font"]
    server.publish(LiveState(True, LONG))
    shown(page, LONG)
    long_font = metrics(page)["font"]
    assert long_font < short / 3
    page.set_viewport_size({"width": 640, "height": 360})
    page.wait_for_timeout(200)
    m = metrics(page)
    assert not m["overflow"] and m["font"] < long_font
    page.close()


def test_line_breaks_and_double_spaces_are_kept(browser, server):
    page = open_page(browser, server)
    server.publish(LiveState(True, "Ligne 1\nLigne 2\n\nLigne 4  deux espaces"))
    shown(page, "Ligne 1\nLigne 2\n\nLigne 4  deux espaces")
    assert (
        page.evaluate("getComputedStyle(document.getElementById('text')).whiteSpace") == "pre-wrap"
    )
    lines = page.evaluate("document.getElementById('text').innerText.split('\\n').length")
    assert lines == 4
    page.close()


def test_text_is_never_interpreted_as_html(browser, server):
    page = open_page(browser, server)
    evil = (
        "<b>gras</b><img src=x onerror=\"document.title='pwned'\">"
        '<script>document.title="pwned"</script>'
    )
    server.publish(LiveState(True, evil))
    shown(page, evil)
    page.wait_for_timeout(200)
    assert page.evaluate("document.getElementById('text').children.length") == 0
    assert page.title() == "Easyworship vers OBS"
    page.close()


def test_emojis_and_accents_render(browser, server):
    text = "Émoji : 😁🙂‍↔️❤️‍🔥 — « é à ô ’ » �"
    page = open_page(browser, server)
    server.publish(LiveState(True, text))
    shown(page, text)
    assert not metrics(page)["overflow"]
    page.close()


def test_style_comes_from_the_url_and_bad_values_are_ignored(browser, server):
    page = open_page(
        browser, server, "?bg=%23ff0000&color=blue&align=left&valign=top&padding=5&radius=0&max=40"
    )
    server.publish(LiveState(True, "style"))
    shown(page, "style")
    style = page.evaluate(
        """() => { const s = getComputedStyle(document.getElementById('text'));
                   return {bg: s.backgroundColor, color: s.color, align: s.textAlign,
                           padding: s.paddingTop, radius: s.borderTopLeftRadius,
                           font: parseFloat(s.fontSize)}; }"""
    )
    assert style["bg"] == "rgb(255, 0, 0)" and style["color"] == "rgb(0, 0, 255)"
    assert style["align"] == "left" and style["padding"] == "5px" and style["radius"] == "0px"
    assert style["font"] <= 40
    top = page.evaluate("document.getElementById('text').getBoundingClientRect().top")
    assert top <= 25  # valign=top (marge 20 px)
    page.close()

    page = open_page(
        browser, server, "?bg=url(http://exemple.invalid/x.png)&color=pas-une-couleur&padding=-4"
    )
    shown(page, "style")
    style = page.evaluate(
        """() => { const s = getComputedStyle(document.getElementById('text'));
                   return [s.backgroundColor, s.backgroundImage, s.paddingTop]; }"""
    )
    assert style == ["rgba(127, 127, 127, 0.7)", "none", "20px"]
    page.close()


def test_background_stays_transparent_for_obs(browser, server):
    page = open_page(browser, server)
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgba(0, 0, 0, 0)"
    page.close()


def test_demo_mode_shows_text_for_styling_without_any_websocket(browser, server):
    page = open_page(browser, server, "?demo=Bonjour%20OBS&bg=%23003366", 800, 400)
    shown(page, "Bonjour OBS")
    page.wait_for_timeout(300)
    assert server.hub.browser_count == 0  # aucun WebSocket ouvert : aperçu du style seulement
    page.close()


def test_page_hides_when_the_application_stops_and_comes_back_when_it_restarts(browser, server):
    page = open_page(browser, server)
    server.publish(LiveState(True, "avant l'arrêt"))
    shown(page, "avant l'arrêt")
    port = server.port
    server.stop()
    hidden(page)  # connexion perdue : pas de texte périmé dans OBS
    server.hub.publish(LiveState(True, "après le redémarrage"))
    server.start(port)
    shown(page, "après le redémarrage")  # le navigateur s'est reconnecté tout seul
    page.close()
