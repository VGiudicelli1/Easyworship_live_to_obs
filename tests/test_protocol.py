import json

import pytest

from ew_to_obs.protocol import (
    FrameDecoder,
    ProtocolError,
    decode_live_data,
    encode,
    encode_live_data,
    get_slide_info_message,
)


def wire(message: dict, extra: bytes = b"") -> bytes:
    return encode(message) + extra


def test_encode_ends_with_crlf_and_is_compact():
    assert encode({"a": 1}) == b'{"a":1}\r\n'


def test_decoder_handles_any_split():
    live = encode_live_data(7, 99, [(11, 1), (12, 2)])
    stream = (
        wire({"action": "status", "slide_rowid": "11"})
        + wire({"action": "LiveData", "size": len(live)}, live)
        + wire({"action": "heartbeat"})
    )
    for step in (1, 2, 3, 7, 40, len(stream)):
        decoder = FrameDecoder()
        frames = []
        for i in range(0, len(stream), step):
            frames += decoder.feed(stream[i : i + step])
        assert [f.message["action"] for f in frames] == ["status", "LiveData", "heartbeat"], step
        assert frames[1].extra == live


def test_decoder_extra_bytes_may_contain_crlf():
    extra = b"ab\r\ncd" * 3
    frames = FrameDecoder().feed(
        wire({"action": "slideImage", "size": len(extra)}, extra) + b"\r\n"
    )
    assert frames[0].extra == extra


def test_decoder_invalid_json_does_not_block_next_message():
    frames = FrameDecoder().feed(b"pas du json\r\n" + wire({"action": "heartbeat"}))
    assert frames[0].message is None
    assert frames[0].raw == b"pas du json"
    assert frames[1].message == {"action": "heartbeat"}


def test_decoder_invalid_utf8_is_replaced_not_dropped():
    raw = b'{"action":"slideInfo","content":"a\xffb"}\r\n'
    frame = FrameDecoder().feed(raw)[0]
    assert frame.message["content"] == "a�b"


def test_decoder_replacement_char_from_ew_is_kept():
    frame = FrameDecoder().feed(wire({"content": "👉�"}))[0]
    assert frame.message["content"] == "👉�"


def test_decoder_rejects_absurd_size_and_runaway_line():
    with pytest.raises(ProtocolError):
        FrameDecoder().feed(wire({"action": "LiveData", "size": 10**12}))
    with pytest.raises(ProtocolError):
        FrameDecoder().feed(b"x" * (17 * 1024 * 1024))


def test_live_data_roundtrip():
    data = decode_live_data(encode_live_data(4189616175330316297, 1119, [(8759, 5), (8830, 6)]))
    assert data.liverev == "4189616175330316297"
    assert data.pres_rowid == 1119
    assert [(s.rowid, s.revision) for s in data.slides] == [(8759, 5), (8830, 6)]


def test_live_data_empty_and_negative_ids():
    assert decode_live_data(encode_live_data(5, 0, [])).slides == ()
    assert decode_live_data(encode_live_data(5, 0, [(-100280, 3)])).slides[0].rowid == -100280


def test_live_data_inconsistent_is_an_error():
    with pytest.raises(ProtocolError):
        decode_live_data(b"\0" * 10)
    truncated = encode_live_data(1, 0, [(1, 1), (2, 2)])[:-8]
    with pytest.raises(ProtocolError):
        decode_live_data(truncated)


def test_slide_info_request_never_targets_slide_zero_fields():
    message = get_slide_info_message(8759, 123, 1119)
    assert json.loads(encode(message)) == {
        "slide_rowid": 8759,
        "revision": 123,
        "action": "getSlideInfo",
        "requestrev": 0,
        "rectype": 1,
        "pres_rowid": 1119,
    }
