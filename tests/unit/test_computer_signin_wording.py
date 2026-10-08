"""Messages about this computer's own key must not call it a "connection key".

The website's Connection keys page calls the account key a "connection key" ("Create a
connection key"). The CLI once used that page's name for the key `tu remote login` stores -- a
different, computer-only kind that can share this machine and nothing else. Someone told "no
connection key is configured" can reasonably go and create one on that page.
"""

from __future__ import annotations

import sys

import pytest

from tooluniverse import cli

KEY = "tu-sk-" + "c" * 60


def test_not_signed_in_says_what_to_run_without_the_websites_name():
    assert "connection key" not in cli.NOT_SIGNED_IN
    assert "tu remote login" in cli.NOT_SIGNED_IN


@pytest.fixture
def revoked(monkeypatch):
    monkeypatch.setattr(cli, "_resolve_private_connection_key", lambda *a, **k: KEY)

    def refuse(*a, **k):
        # What _platform_request raises when the platform refuses the key.
        raise cli._PlatformHTTPError("Invalid or expired API key", status=401)

    monkeypatch.setattr(cli, "_validate_remote_connection_key", refuse)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)


def test_a_revoked_sign_in_says_to_sign_in_again(revoked, monkeypatch):
    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY", raising=False)

    with pytest.raises(RuntimeError) as caught:
        cli._connection_key_for_share("https://api.example")

    message = str(caught.value)
    assert "sign-in is no longer accepted" in message
    assert "tu remote login" in message


def test_a_revoked_key_in_the_variable_is_not_fixed_by_logging_in(revoked, monkeypatch):
    """The variable overrides a stored sign-in, so `tu remote login` would change nothing."""
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY)

    with pytest.raises(RuntimeError) as caught:
        cli._connection_key_for_share("https://api.example")

    message = str(caught.value)
    assert "TOOLUNIVERSE_SERVICE_KEY" in message
    assert "tu remote login" not in message


def test_help_texts_do_not_reuse_the_websites_name(capsys):
    parser = cli.build_parser()
    # A subcommand's help= appears in its parent's listing, so `remote --help` shows logout's.
    for argv in (["remote", "--help"], ["remote", "run", "--help"]):
        with pytest.raises(SystemExit):
            parser.parse_args(argv)
    assert "connection key" not in capsys.readouterr().out


def test_forwarding_without_a_sign_in_gives_the_same_instruction(monkeypatch):
    """`tu serve --forward ... --share` said only "a computer-only connection key is required"."""
    import types

    relay = types.ModuleType("tuplatform_connect.relay")
    relay.RelayAgent = object
    relay.RelayError = RuntimeError
    monkeypatch.setitem(sys.modules, "tuplatform_connect", types.ModuleType("tuplatform_connect"))
    monkeypatch.setitem(sys.modules, "tuplatform_connect.relay", relay)
    monkeypatch.setattr(cli, "_connection_key_for_share", lambda *a, **k: "")
    args = types.SimpleNamespace(service="https://api.example", no_browser=True)

    with pytest.raises(RuntimeError) as caught:
        cli._forward_remote_tool_server(args)

    assert str(caught.value) == cli.NOT_SIGNED_IN_REASON


# ── when the platform cannot be reached ──────────────────────────────────────────


def unreachable(monkeypatch, error):
    import urllib.request

    class Opener:
        def open(self, *a, **k):
            raise error

    monkeypatch.setattr(urllib.request, "build_opener", lambda *a, **k: Opener())
    with pytest.raises(RuntimeError) as caught:
        cli._platform_request("https://api.example", "/auth/device/start", payload={})
    return str(caught.value)


def test_no_network_says_to_check_the_connection_not_urlopen(monkeypatch):
    import urllib.error

    message = unreachable(monkeypatch, urllib.error.URLError(ConnectionRefusedError(111, "x")))

    assert "urlopen error" not in message
    assert "internet connection" in message and "HTTPS_PROXY" in message


def test_a_slow_start_says_to_wait(monkeypatch):
    import urllib.error

    message = unreachable(monkeypatch, urllib.error.URLError(TimeoutError("timed out")))

    assert "wait a minute" in message


def test_a_bare_timeout_is_explained_too(monkeypatch):
    message = unreachable(monkeypatch, TimeoutError("The read operation timed out"))

    assert "wait a minute" in message


def test_an_inspected_network_is_told_about_certificates(monkeypatch):
    import ssl
    import urllib.error

    error = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    message = unreachable(monkeypatch, urllib.error.URLError(error))

    assert "SSL_CERT_FILE" in message


@pytest.mark.parametrize("error", [
    RuntimeError("could not reach https://api.example ([Errno 111] Connection refused). ..."),
    cli._PlatformHTTPError("internal error", status=503),
])
def test_a_platform_problem_is_not_blamed_on_the_key(monkeypatch, error):
    """Neither an unreachable platform nor a 5xx says anything about the key."""
    monkeypatch.setattr(cli, "_resolve_private_connection_key", lambda *a, **k: KEY)

    def fail(*a, **k):
        raise error

    monkeypatch.setattr(cli, "_validate_remote_connection_key", fail)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY)
    started = []
    monkeypatch.setattr(cli, "_device_authorization_login", lambda *a, **k: started.append(1))

    with pytest.raises(RuntimeError) as caught:
        cli._connection_key_for_share("https://api.example")

    assert caught.value is error
    assert "no longer accepted" not in str(caught.value)
    assert started == []


def test_a_refused_key_is_still_called_refused(revoked, monkeypatch):
    def refuse(*a, **k):
        raise cli._PlatformHTTPError("Invalid or expired API key", status=401)

    monkeypatch.setattr(cli, "_validate_remote_connection_key", refuse)
    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="no longer accepted"):
        cli._connection_key_for_share("https://api.example")
