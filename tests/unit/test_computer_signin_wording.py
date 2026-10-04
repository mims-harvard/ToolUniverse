"""Messages about this computer's own key must not call it a "private connection".

The website's API keys page calls the account key a "private connection" ("New private
connection", "Private connections"). The CLI used the same name for the key `tu remote login`
stores -- a different, computer-only kind that can share this machine and nothing else. Someone
told "no private connection key is configured" can reasonably go and create one on that page.
"""

from __future__ import annotations

import sys

import pytest

from tooluniverse import cli

KEY = "tu-sk-" + "c" * 60


def test_not_signed_in_says_what_to_run_without_the_websites_name():
    assert "private connection" not in cli.NOT_SIGNED_IN
    assert "tu remote login" in cli.NOT_SIGNED_IN


@pytest.fixture
def revoked(monkeypatch):
    monkeypatch.setattr(cli, "_resolve_private_connection_key", lambda *a, **k: KEY)

    def refuse(*a, **k):
        raise RuntimeError("Invalid or expired API key")

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
    assert "private connection" not in capsys.readouterr().out
