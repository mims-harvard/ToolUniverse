"""`tu remote login` -- and a first `tu serve --share` -- over SSH on a box with a text browser.

Measured against a live platform with a stand-in www-browser on PATH and no DISPLAY: the person
approved the code in their laptop's browser, and the CLI still never finished. It only starts
polling for the approval after webbrowser.open returns, and GenericBrowser waits for a terminal
browser to exit. The login was never stored. tuplatform-connect had been fixed for this; this is
ToolUniverse's own copy of the same flow.
"""

from __future__ import annotations

import sys

import pytest

from tooluniverse import cli

KEY = "tu-sk-" + "e" * 60


@pytest.fixture
def no_display(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)


def test_no_display_means_no_browser(no_display):
    assert cli._graphical_session_available() is False


def test_a_blank_display_is_not_a_display(no_display, monkeypatch):
    monkeypatch.setenv("DISPLAY", "  ")

    assert cli._graphical_session_available() is False


@pytest.mark.parametrize("name, value", [("DISPLAY", ":0"), ("WAYLAND_DISPLAY", "wayland-0")])
def test_a_display_is_used(no_display, monkeypatch, name, value):
    monkeypatch.setenv(name, value)

    assert cli._graphical_session_available() is True


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_mac_and_windows_always_try(monkeypatch, platform):
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.delenv("DISPLAY", raising=False)

    assert cli._graphical_session_available() is True


def test_the_login_flow_never_launches_a_browser_without_a_display(no_display, monkeypatch, capsys):
    """Drives the real attempt function, so the wiring is covered and not only the helper."""
    import time
    import webbrowser

    launched = []
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: launched.append(a) or True)
    monkeypatch.setattr(time, "sleep", lambda *_: None)

    def platform_request(service, path, **kwargs):
        if path == "/auth/device/start":
            return {"device_code": "d" * 43, "user_code": "BCDF-GHJK",
                    "verification_uri": "https://connect.example/activate",
                    "verification_uri_complete": "https://connect.example/activate?user_code=BCDF-GHJK",
                    "expires_in": 600, "interval": 1}
        if path == "/auth/device/token":
            return {"access_token": KEY, "purpose": "relay"}
        raise AssertionError(path)

    monkeypatch.setattr(cli, "_platform_request", platform_request)
    monkeypatch.setattr(cli, "_validate_remote_connection_key", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_valid_device_code", lambda code: True)

    key = cli._device_authorization_attempt("https://connect.example")

    assert key == KEY
    assert launched == [], "a browser was launched with no display to show it"
    out = capsys.readouterr().out
    assert "normal over SSH" in out
    assert "BCDF-GHJK" in out, "the code must still be printed for the person to type"
