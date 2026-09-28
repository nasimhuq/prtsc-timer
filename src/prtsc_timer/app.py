"""GTK shell for PrtSc Timer - take a screenshot now, in 5 s or in 10 s, using the desktop's own tool.

Structure (functional core, imperative shell):
  core.py     pure data + functions (no GTK, fully unit-testable)
  portal.py   D-Bus side effects (Screenshot portal)
  here        GTK wiring: build widgets, connect events, run the app
"""

from __future__ import annotations

from functools import partial

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .core import DELAYS, CaptureResult, delay_ms, status_text  # noqa: E402
from .portal import request_screenshot  # noqa: E402

APP_ID = "io.github.nasimhuq.prtsc_timer"

# ---- Widget builders (return new widgets, no global state) -----------------


def build_button(label: str, on_click) -> Gtk.Button:
    """`on_click` receives the clicked button (its window is `button.get_root()`)."""
    button = Gtk.Button(label=label)
    button.add_css_class("pill")
    button.connect("clicked", on_click)
    return button


def build_status() -> Gtk.Label:
    label = Gtk.Label(label=status_text(None), wrap=True, selectable=True)
    label.add_css_class("dim-label")
    return label


def build_window(
    app: Adw.Application, buttons: list[Gtk.Button], status: Gtk.Label
) -> Adw.ApplicationWindow:
    box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=8,
        margin_top=16,
        margin_bottom=16,
        margin_start=16,
        margin_end=16,
    )
    for widget in (*buttons, status):
        box.append(widget)

    view = Adw.ToolbarView(content=box)
    view.add_top_bar(Adw.HeaderBar())

    window = Adw.ApplicationWindow(
        application=app, title="PrtSc Timer", resizable=False, content=view
    )
    window.set_default_size(280, -1)
    return window


# ---- Effects (event handlers) ----------------------------------------------


def show_result(
    app: Adw.Application, window: Gtk.Window, status: Gtk.Label, result: CaptureResult
) -> None:
    status.set_label(status_text(result))
    window.set_visible(True)
    window.present()
    app.release()


def start_capture(
    app: Adw.Application,
    window: Gtk.Window,
    status: Gtk.Label,
    bus: Gio.DBusConnection,
    seconds: int,
) -> None:
    app.hold()  # keep the app alive while its only window is hidden
    window.set_visible(False)
    on_result = partial(show_result, app, window, status)

    def fire() -> bool:
        request_screenshot(bus, on_result)
        return GLib.SOURCE_REMOVE  # run the timer once

    GLib.timeout_add(delay_ms(seconds), fire)


def on_activate(app: Adw.Application) -> None:
    if app.props.active_window:
        app.props.active_window.present()
        return

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    status = build_status()
    buttons = [
        build_button(
            label,
            lambda btn, s=seconds: start_capture(app, btn.get_root(), status, bus, s),
        )
        for label, seconds in DELAYS
    ]
    build_window(app, buttons, status).present()


def main() -> int:
    app = Adw.Application(application_id=APP_ID)
    app.connect("activate", on_activate)
    return app.run(None)
