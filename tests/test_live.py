"""Cas limites de LiveSession qui ne sont pas (encore) dans les captures."""

from ew_to_obs.live import LiveSession, LiveState, Pairing
from ew_to_obs.protocol import encode_live_data


def status(slide, liverev="100", imagehash="h", pres="1", **flags):
    msg = {
        "action": "status",
        "pres_rowid": pres,
        "slide_rowid": str(slide),
        "liverev": str(liverev),
        "imagehash": imagehash,
        "logo": False,
        "black": False,
        "clear": False,
    }
    msg.update(flags)
    return msg


def live_data(liverev, slides, pres=1):
    extra = encode_live_data(int(liverev), pres, slides)
    return {"action": "LiveData", "size": len(extra)}, extra


def slide_info(rowid, revision, content):
    return {
        "action": "slideInfo",
        "slide_rowid": str(rowid),
        "revision": str(revision),
        "content": content,
    }


def load(session, liverev="100", slides=((11, 1), (12, 1)), texts=None):
    """status → LiveData → slideInfo de toutes les diapos ; renvoie le dernier état émis."""
    session.on_message(status(slides[0][0], liverev))
    session.on_message(*live_data(liverev, list(slides)))
    state = None
    for rowid, revision in slides:
        result = session.on_message(
            slide_info(rowid, revision, (texts or {}).get(rowid, "t%d" % rowid))
        )
        state = result.state or state
    return state


def test_first_status_requests_live_data_and_waits_for_the_text():
    s = LiveSession()
    result = s.on_message(status(11))
    assert [m["action"] for m in result.send] == ["GetLiveData"]
    assert result.state is None  # rien de périmé, rien de vide
    result = s.on_message(*live_data(100, [(11, 1)]))
    assert [m["slide_rowid"] for m in result.send] == [11]
    assert result.state is None
    assert s.on_message(slide_info(11, 1, "A\r\nB")).state == LiveState(True, "A\nB")


def test_liverev_zero_means_ew_not_ready_and_requests_nothing():
    s = LiveSession()
    result = s.on_message(status(0, liverev="0", imagehash=""))
    assert result.send == [] and result.state == LiveState.hidden()


def test_empty_imagehash_means_nothing_live():
    s = LiveSession()
    assert s.on_message(status(-100049, imagehash="")).state == LiveState.hidden()


def test_new_liverev_keeps_previous_state_until_new_text_arrives():
    s = LiveSession()
    assert load(s) == LiveState(True, "t11")
    result = s.on_message(status(21, liverev="200"))
    assert result.send[0]["action"] == "GetLiveData" and result.state is None
    s.on_message(*live_data(200, [(21, 7)]))
    assert s.on_message(slide_info(21, 7, "nouveau")).state == LiveState(True, "nouveau")


def test_stale_live_data_and_stale_slide_info_are_ignored():
    s = LiveSession()
    s.on_message(status(11, "100"))
    s.on_message(status(21, "200"))  # un nouveau liverev arrive avant la réponse du premier
    assert s.on_message(*live_data(100, [(11, 1)])).send == []  # réponse périmée
    s.on_message(*live_data(200, [(21, 7)]))
    assert s.on_message(slide_info(21, 3, "ancienne révision")).state is None
    assert s.on_message(slide_info(11, 1, "autre présentation")).state is None
    assert s.on_message(slide_info(21, 7, "bon")).state == LiveState(True, "bon")


def test_duplicate_live_data_does_not_request_slides_twice():
    s = LiveSession()
    s.on_message(status(11))
    first = s.on_message(*live_data(100, [(11, 1)]))
    second = s.on_message(*live_data(100, [(11, 1)]))
    assert len(first.send) == 1 and second.send == []


def test_slide_missing_from_live_data_is_hidden():
    s = LiveSession()
    load(s)
    assert s.on_message(status(99)).state == LiveState.hidden()


def test_flags_hide_and_restore_and_accept_strings():
    s = LiveSession()
    assert load(s) == LiveState(True, "t11")
    assert s.on_message(status(11, black=True)).state == LiveState.hidden()
    assert s.on_message(status(11, logo="true")).state is None  # toujours caché
    assert s.on_message(status(11)).state == LiveState(True, "t11")


def test_status_noise_does_not_republish_or_reload():
    s = LiveSession()
    load(s)
    for noisy in (
        status(11, permissions=1),
        status(11, schedulerev="9"),
        status(11, imagehash="x"),
    ):
        result = s.on_message(noisy)
        assert result.send == [] and result.state is None


def test_pairing_messages_and_unknown_actions():
    s = LiveSession()
    s.on_message({"action": "notPaired"})
    assert s.pairing is Pairing.NOT_PAIRED
    s.on_message({"action": "paired"})
    assert s.pairing is Pairing.PAIRED
    result = s.on_message({"action": "heartbeat"})
    assert result.send == [] and result.state is None
    assert s.on_message({"action": "inconnue", "x": 1}).state is None


def test_empty_text_slide_is_a_valid_visible_state():
    s = LiveSession()
    assert load(s, texts={11: ""}) == LiveState(True, "")
