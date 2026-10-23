"""Rejeu des captures réelles anonymisées dans la logique de LiveSession."""

import glob
import os

import pytest

from ew_to_obs.live import LiveState, Pairing
from replay import FIXTURES, line, load, replay

NAMES = sorted(os.path.basename(p)[11:-6] for p in glob.glob(str(FIXTURES / "ew_session_*.jsonl")))


def oracle_requests(name):
    """Nombre attendu de GetLiveData et de getSlideInfo, calculé directement sur la capture :
    un GetLiveData par liverev (≠ "0") vu dans un status, un getSlideInfo par diapo du premier
    LiveData reçu pour ce liverev (le titre de présentation n'est jamais demandé)."""
    live_data = slides = 0
    seen: set[str] = set()
    answered: set[str] = set()
    for rec in load(name):
        if rec["dir"] == "info" and rec.get("msg", {}).get("event") == "connected":
            seen, answered = set(), set()
        elif rec["dir"] == "recv" and rec["msg"].get("action") == "status":
            rev = str(rec["msg"]["liverev"])
            if rev != "0" and rev not in seen:
                seen.add(rev)
                live_data += 1
        elif rec["dir"] == "recv" and rec["msg"].get("action") == "LiveData":
            rev = str(rec["decoded"]["liverev"])
            if rev in seen and rev not in answered:
                answered.add(rev)
                slides += rec["decoded"]["pres_len"]
    return live_data, slides


@pytest.mark.parametrize("name", NAMES)
def test_requests_match_the_oracle_and_never_ask_for_the_title(name):
    result = replay(name)
    live_data = [m for m in result.sent if m["action"] == "GetLiveData"]
    slide_info = [m for m in result.sent if m["action"] == "getSlideInfo"]
    assert {m["action"] for m in result.sent} <= {"GetLiveData", "getSlideInfo"}
    assert (len(live_data), len(slide_info)) == oracle_requests(name)
    assert all(m["slide_rowid"] != 0 for m in slide_info)


@pytest.mark.parametrize("name", NAMES)
def test_no_state_is_emitted_twice_in_a_row_within_a_session(name):
    result = replay(name)
    for (a, sa), (b, sb) in zip(
        zip(result.states, result.state_session, strict=True),
        zip(result.states[1:], result.state_session[1:], strict=True),
        strict=False,
    ):
        assert not (sa == sb and a == b)


@pytest.mark.parametrize("name", NAMES)
def test_text_is_normalized_and_hidden_means_empty(name):
    for state in replay(name).states:
        assert "\r" not in state.text
        if not state.visible:
            assert state.text == ""


def test_real_session_shows_first_slide_then_follows_the_operator():
    r = replay("reelle_anonymisee")
    assert r.states[0] == LiveState(True, line(8759, 2))
    assert r.states[1] == LiveState(True, line(8830, 2))
    assert r.states[2] == LiveState(True, line(2779))


def test_real_session_logo_black_clear_hide_then_restore_the_same_text():
    states = replay("reelle_anonymisee").states
    restored = [
        i
        for i in range(1, len(states) - 1)
        if not states[i].visible and states[i - 1].visible and states[i + 1] == states[i - 1]
    ]
    assert restored, "aucun masquage suivi du même texte"


def test_empty_slides_share_one_state_instead_of_being_lost():
    # Les diapos vides ont le même imagehash : seul slide_rowid les distingue (10 changements
    # sur 11 invisibles avec la logique V1). Ici ils donnent un seul état vide, sans texte périmé.
    states = replay("diapos_vides_anonymisee").states
    assert states[6] == LiveState(True, "")  # diapo 8892, vide
    assert states[8] == LiveState(True, "")  # présentation de 5 diapos vides
    assert (
        states[9].text == "premiere slide sans label : ok"
    )  # 8 navigations vides : 0 état de plus


def test_live_edit_reloads_and_shows_the_new_slide():
    r = replay("edition_live_anonymisee")
    assert [m["action"] for m in r.sent].count("GetLiveData") == 2
    assert r.states[3].text == "premiere slide sans label : ok"
    assert r.states[-1].text == "contenu 3 : slide ajouté en live"


def test_nothing_live_then_songs_with_negative_ephemeral_ids():
    r = replay("aucun_live_et_chants_anonymisee")
    assert r.states[0] == LiveState.hidden()
    assert r.states[2].text.startswith("Ligne 1 de la diapo -100280")
    assert r.states[3].text.startswith("Ligne 1 de la diapo -100378")
    assert any(m.get("slide_rowid", 0) < 0 for m in r.sent if m["action"] == "getSlideInfo")


def test_control_mode_toggle_does_not_republish():
    r = replay("controle_revocation_anonymisee")
    assert len(r.states) == 1  # permissions 0 → 1 → 0 : aucun nouvel état


def test_not_paired_session_stays_silent():
    r = replay("sans_appairage_anonymisee")
    assert r.session.pairing is Pairing.NOT_PAIRED
    assert r.states == [] and r.sent == []


def test_media_only_slides_give_empty_text_and_text_slides_keep_theirs():
    texts = [s.text for s in replay("medias_anonymisee").states]
    assert "" in texts
    assert any(t.startswith("slide précédente : vidéo") for t in texts)


def test_emojis_preserved_with_replacement_char_and_formatting_free_text():
    first = replay("emojis_relance_anonymisee").states[0].text
    assert "🙂‍↔️" in first and "❤️‍🔥" in first
    assert "�" in first
    assert "texte  en italique" in first  # espace double conservé


def test_each_reconnection_starts_a_fresh_session():
    r = replay("reconnexion_anonymisee")
    assert len(r.sessions) == 3
    assert all(s == LiveState.hidden() for s in r.states)


def test_150_slides_requested_at_once():
    r = replay("150_diapos")
    assert len([m for m in r.sent if m["action"] == "getSlideInfo"]) == 150
