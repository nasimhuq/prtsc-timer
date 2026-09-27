"""Effectful edge: talk to org.freedesktop.portal.Screenshot over D-Bus."""

from __future__ import annotations

import secrets
from collections.abc import Callable

from gi.repository import Gio, GLib

from .core import (
    CaptureResult,
    Failed,
    make_token,
    parse_response,
    request_handle,
    screenshot_options,
)

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"


def to_variant_dict(options: dict[str, tuple[str, object]]) -> dict[str, GLib.Variant]:
    """Pure conversion of (signature, value) pairs into GLib.Variants."""
    return {key: GLib.Variant(sig, value) for key, (sig, value) in options.items()}


def request_screenshot(
    bus: Gio.DBusConnection,
    on_result: Callable[[CaptureResult], None],
) -> None:
    """Ask the desktop for an interactive screenshot; call `on_result` exactly once."""
    token = make_token(secrets.token_hex(4))
    handle = request_handle(bus.get_unique_name(), token)
    subscription: list[int] = []  # filled right after subscribing

    def finish(result: CaptureResult) -> None:
        bus.signal_unsubscribe(subscription[0])
        on_result(result)

    def on_response(_conn, _sender, _path, _iface, _signal, params: GLib.Variant) -> None:
        code, results = params.unpack()
        finish(parse_response(code, results))

    def on_called(conn: Gio.DBusConnection, res: Gio.AsyncResult) -> None:
        try:
            conn.call_finish(res)
        except GLib.Error as err:
            finish(Failed(err.message))

    # Subscribe to the reply *before* sending the request, so it can't be missed.
    subscription.append(
        bus.signal_subscribe(
            PORTAL_BUS, "org.freedesktop.portal.Request", "Response", handle,
            None, Gio.DBusSignalFlags.NO_MATCH_RULE, on_response,
        )
    )
    bus.call(
        PORTAL_BUS, PORTAL_PATH, "org.freedesktop.portal.Screenshot", "Screenshot",
        GLib.Variant("(sa{sv})", ("", to_variant_dict(screenshot_options(token)))),
        GLib.VariantType("(o)"), Gio.DBusCallFlags.NONE, -1, None, on_called,
    )
