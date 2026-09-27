from prt_sc_app.core import (
    Cancelled,
    Failed,
    Saved,
    delay_ms,
    make_token,
    parse_response,
    request_handle,
    screenshot_options,
    sender_path,
    status_text,
    uri_to_path,
)


def test_delay_ms_has_minimum():
    assert delay_ms(0) == 400
    assert delay_ms(5) == 5000
    assert delay_ms(10) == 10000


def test_sender_path_and_handle():
    assert sender_path(":1.42") == "1_42"
    assert request_handle(":1.42", "prtsc_ab12") == \
        "/org/freedesktop/portal/desktop/request/1_42/prtsc_ab12"


def test_options():
    assert screenshot_options(make_token("ab12")) == {
        "handle_token": ("s", "prtsc_ab12"),
        "interactive": ("b", True),
    }


def test_uri_to_path_decodes():
    assert uri_to_path("file:///home/n/My%20Shot.png") == "/home/n/My Shot.png"


def test_parse_response():
    assert parse_response(0, {"uri": "file:///tmp/a.png"}) == Saved("/tmp/a.png")
    assert parse_response(0, {}) == Failed("Portal returned no image")
    assert parse_response(1, {}) == Cancelled()
    assert parse_response(2, {}) == Failed("Portal error (code 2)")


def test_status_text():
    assert status_text(None) == "Choose a delay"
    assert status_text(Saved("/tmp/a.png")) == "Saved:\n/tmp/a.png"
    assert status_text(Cancelled()) == "Cancelled"
    assert status_text(Failed("x")) == "Failed: x"
