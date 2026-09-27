"""Pure core: data types and functions with no side effects and no GTK/D-Bus imports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

MIN_DELAY_MS = 400  # give the window time to disappear before capturing

# (button label, delay in seconds)
DELAYS: tuple[tuple[str, int], ...] = (
    ("Immediate", 0),
    ("5 s delay", 5),
    ("10 s delay", 10),
)


# ---- Result types -----------------------------------------------------------

@dataclass(frozen=True)
class Saved:
    path: str


@dataclass(frozen=True)
class Cancelled:
    pass


@dataclass(frozen=True)
class Failed:
    reason: str


CaptureResult = Saved | Cancelled | Failed


# ---- Pure functions ---------------------------------------------------------

def delay_ms(seconds: int, minimum: int = MIN_DELAY_MS) -> int:
    """Delay in milliseconds, never shorter than `minimum`."""
    return max(seconds * 1000, minimum)


def sender_path(unique_name: str) -> str:
    """D-Bus unique name ':1.42' -> portal path segment '1_42'."""
    return unique_name.lstrip(":").replace(".", "_")


def request_handle(unique_name: str, token: str) -> str:
    """Object path on which the portal will emit its Response signal."""
    return f"/org/freedesktop/portal/desktop/request/{sender_path(unique_name)}/{token}"


def make_token(entropy_hex: str) -> str:
    """Build a portal handle token from caller-supplied randomness."""
    return f"prtsc_{entropy_hex}"


def screenshot_options(token: str, interactive: bool = True) -> dict[str, tuple[str, object]]:
    """Portal options as plain (signature, value) pairs; converted to GLib.Variant at the edge."""
    return {
        "handle_token": ("s", token),
        "interactive": ("b", interactive),
    }


def uri_to_path(uri: str) -> str:
    """'file:///home/a/My%20Shot.png' -> '/home/a/My Shot.png'."""
    return unquote(urlparse(uri).path)


def document_id(path: str) -> str | None:
    """'/run/user/1000/doc/1a2b3c4d/Shot.png' -> '1a2b3c4d'; None for ordinary paths.

    Sandboxed apps receive files through the document portal's FUSE mount
    rather than their real location.
    """
    match = re.match(r"^/run/(?:user/\d+|flatpak)/doc/([^/]+)/", path)
    return match.group(1) if match else None


def parse_response(code: int, results: dict) -> CaptureResult:
    """Translate the portal's (response code, results) into a CaptureResult."""
    match code:
        case 0 if "uri" in results:
            return Saved(uri_to_path(results["uri"]))
        case 0:
            return Failed("Portal returned no image")
        case 1:
            return Cancelled()
        case _:
            return Failed(f"Portal error (code {code})")


def status_text(result: CaptureResult | None) -> str:
    """Text shown under the buttons."""
    match result:
        case None:
            return "Choose a delay"
        case Saved(path):
            return f"Saved:\n{path}"
        case Cancelled():
            return "Cancelled"
        case Failed(reason):
            return f"Failed: {reason}"
