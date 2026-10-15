"""The borrower's path: `tu connect TU-SHARE-...`, then using the tool in a later terminal.

Every other check of sharing called the join endpoint directly. Driving the command a borrower
is actually told to run found three dead ends in a row:

  - with nothing set, "joining a share code requires TU_API_KEY or TOOLUNIVERSE_SERVICE_KEY"
    and nothing about how to get either;
  - after `tu remote login`, which every other sign-in message points to, the identical error,
    because that key lives in a file this never read -- and is the computer-only kind, which
    the platform refuses for anything but registering that one machine;
  - after connecting in one terminal and opening another, a 401 buried in an httpx string,
    advice to "start the server" (it was running, and was not theirs), and finally "not found
    -- check the tool name spelling".

These pin the replacements. No network: the platform and the clipboard are both stubbed.
"""

from __future__ import annotations

import os
import stat
import sys
from types import SimpleNamespace

import pytest

from tooluniverse import cli
from tooluniverse.cli import (
    BORROWER_KEY_ENV,
    _api_keys_page,
    _borrower_api_key,
    _render_run,
    _save_global_env,
)
from tooluniverse.execute_function import explain_remote_load_failure

KEY = "tu-sk-" + "a" * 60
OTHER = "tu-sk-" + "b" * 60


@pytest.fixture
def home(tmp_path, monkeypatch):
    """An isolated home with no keys anywhere, and no terminal attached."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    for name in (BORROWER_KEY_ENV, "TOOLUNIVERSE_SERVICE_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(cli, "_read_stored_remote_key", lambda: "")
    yield tmp_path
    # load_dotenv and the paste path write os.environ directly, outside monkeypatch, so a key
    # loaded here would otherwise leak into every test that runs afterwards.
    for name in (BORROWER_KEY_ENV, "TOOLUNIVERSE_SERVICE_KEY"):
        os.environ.pop(name, None)


# ── finding the key ──────────────────────────────────────────────────────────────


def test_the_borrower_key_has_its_own_name():
    """TOOLUNIVERSE_SERVICE_KEY already means the computer-only sharing key.

    Saving a borrower's account key under the same name would make sharing and borrowing on
    one computer overwrite each other.
    """
    assert BORROWER_KEY_ENV == "TU_API_KEY"


def test_a_key_in_the_shell_is_used_and_reported_as_shell_only(home, monkeypatch):
    monkeypatch.setenv(BORROWER_KEY_ENV, KEY)

    key, name, where = _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert (key, name, where) == (KEY, BORROWER_KEY_ENV, "shell")


def test_a_key_saved_in_the_global_env_file_is_found(home):
    """What makes a later terminal work, measured: the saved file is read, the shell is not."""
    (home / ".tooluniverse").mkdir()
    (home / ".tooluniverse" / ".env").write_text(f"{BORROWER_KEY_ENV}={KEY}\n")

    key, name, where = _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert (key, name, where) == (KEY, BORROWER_KEY_ENV, "saved")


def test_a_saved_key_is_found_from_a_project_directory_too(home, monkeypatch):
    """Two places a terminal opens, and the saved key has to be found from both.

    The test above runs with the home directory as the working directory, where the
    workspace .env and the global one are the same file -- so it cannot tell whether the
    global file is loaded at all. Dropping it survived that test. From a project directory
    they differ, and only loading the global file finds the key.
    """
    (home / ".tooluniverse").mkdir()
    (home / ".tooluniverse" / ".env").write_text(f"{BORROWER_KEY_ENV}={KEY}\n")
    project = home / "projects" / "screen"
    project.mkdir(parents=True)
    monkeypatch.chdir(project)

    key, _, where = _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert (key, where) == (KEY, "saved")


def test_the_borrower_key_wins_over_the_sharing_key(home, monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", OTHER)
    monkeypatch.setenv(BORROWER_KEY_ENV, KEY)

    key, name, _ = _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert (key, name) == (KEY, BORROWER_KEY_ENV)


# ── when there is no key ────────────────────────────────────────────────────────


def test_with_no_key_the_message_says_what_kind_and_where_to_save_it(home):
    with pytest.raises(RuntimeError) as caught:
        _borrower_api_key("https://tooluniverse-backend.onrender.com")

    message = str(caught.value)
    assert "API key from your ToolUniverse account" in message
    assert "https://connect.aiscientist.tools/api-keys" in message
    assert f"{BORROWER_KEY_ENV}=<your key>" in message
    assert ".tooluniverse/.env" in message


def test_a_computer_login_is_explained_rather_than_ignored(home, monkeypatch):
    """`tu remote login` is what every other sign-in message suggests.

    Someone who did it, and then sees the same error again, needs to be told that sign-in was
    for sharing and is not the key this needs.
    """
    monkeypatch.setattr(cli, "_read_stored_remote_key", lambda: KEY)

    with pytest.raises(RuntimeError) as caught:
        _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert "`tu remote login` is for sharing this computer" in str(caught.value)


def test_a_self_hosted_service_is_not_sent_to_the_public_site(home):
    """Naming the wrong site would send someone to an account they do not have."""
    with pytest.raises(RuntimeError) as caught:
        _borrower_api_key("http://127.0.0.1:8000")

    assert "aiscientist.tools" not in str(caught.value)
    assert _api_keys_page("http://127.0.0.1:8000") == (
        "the API keys page of your ToolUniverse account"
    )


# ── in a terminal: paste once, saved for every later terminal ────────────────────


def test_a_pasted_key_is_saved_privately_and_used(home, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": KEY)

    key, name, where = _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert (key, name, where) == (KEY, BORROWER_KEY_ENV, "entered")
    saved = home / ".tooluniverse" / ".env"
    assert saved.read_text() == f"{BORROWER_KEY_ENV}={KEY}\n"
    # A key on disk, so nobody else on the machine may read it.
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600


def test_something_that_is_not_a_key_is_refused_and_nothing_is_written(home, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    import getpass

    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "my password")

    with pytest.raises(RuntimeError) as caught:
        _borrower_api_key("https://tooluniverse-backend.onrender.com")

    assert "tu-sk-" in str(caught.value)
    assert not (home / ".tooluniverse" / ".env").exists()


def test_saving_replaces_an_old_value_and_keeps_other_lines(home):
    target = home / ".tooluniverse" / ".env"
    target.parent.mkdir()
    target.write_text(f"NCBI_API_KEY=keep-me\n{BORROWER_KEY_ENV}={OTHER}\n")

    _save_global_env(BORROWER_KEY_ENV, KEY)

    lines = target.read_text().splitlines()
    assert "NCBI_API_KEY=keep-me" in lines
    assert f"{BORROWER_KEY_ENV}={KEY}" in lines
    assert f"{BORROWER_KEY_ENV}={OTHER}" not in lines


# ── using the tool later ─────────────────────────────────────────────────────────

RELAY = {
    "connection_name": "alice-gpu",
    "server_url": "http://localhost:8000/relay/x/mcp",
    "auth_env": BORROWER_KEY_ENV,
    "tool_prefix": "alice_gpu_",
}
HTTPX_503 = (
    "Server error '503 Service Unavailable' for url 'http://localhost:8000/relay/x/mcp'\n"
    "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503"
)


def test_a_missing_key_names_the_variable_and_the_file():
    message, missing = explain_remote_load_failure(RELAY, "Client error '401'", {})

    assert missing is True
    assert BORROWER_KEY_ENV in message and ".tooluniverse/.env" in message
    assert "start the server" not in message


def test_a_rejected_key_is_not_reported_as_missing():
    message, missing = explain_remote_load_failure(
        RELAY, "Client error '401 Unauthorized' for url ...", {BORROWER_KEY_ENV: KEY}
    )

    assert missing is False
    assert "rejected the key" in message


def test_a_shared_machine_that_is_offline_is_the_owners_to_fix():
    message, _ = explain_remote_load_failure(RELAY, HTTPX_503, {BORROWER_KEY_ENV: KEY})

    assert "owner brings it back online" in message
    assert "start the server" not in message
    # The httpx text is noise to the person reading this: one status code is enough.
    assert "mozilla" not in message and "503" in message


def test_a_local_server_keeps_the_advice_that_is_right_for_it():
    message, _ = explain_remote_load_failure(
        {"name": "connected_mcp_0", "server_url": "http://127.0.0.1:9000/mcp"},
        "connection refused",
        {},
    )

    assert "start the server" in message


def _universe_with(failures):
    """The method only reads _failed_remote_connections, so a bare namespace stands in."""
    from tooluniverse.execute_function import ToolUniverse

    return ToolUniverse._missing_tool_error(
        SimpleNamespace(_failed_remote_connections=failures), "alice_gpu_predict"
    )


def test_a_tool_from_a_connection_without_its_key_says_so_in_the_cli_wording():
    message, steps = _universe_with({
        "alice_gpu_": {"message": "x", "missing_env": BORROWER_KEY_ENV, "label": "alice-gpu"}
    })

    # The CLI recognises this exact phrasing and answers it with the .env tip.
    assert "requires API key(s) not set: TU_API_KEY" in message
    assert "alice-gpu" in message
    assert all("spelling" not in step for step in steps)


def test_a_tool_from_an_offline_connection_does_not_suggest_a_typo():
    message, steps = _universe_with({
        "alice_gpu_": {"message": "the machine is offline", "missing_env": "",
                       "label": "alice-gpu"}
    })

    assert "not available" in message and "offline" in message
    assert all("spelling" not in step for step in steps)


def test_an_unrelated_unknown_name_still_gets_the_spelling_advice():
    message, steps = _universe_with({
        "other_": {"message": "x", "missing_env": "", "label": "other"}
    })

    assert "not found" in message
    assert any("spelling" in step for step in steps)


@pytest.mark.parametrize(
    "error, spelling_expected",
    [
        ("Tool 'alice_gpu_predict' not found even after loading tools", True),
        ("Tool 'alice_gpu_predict' is not available. The machine is offline.", False),
    ],
)
def test_the_cli_reserves_spelling_tips_for_names_that_are_unknown(error, spelling_expected):
    rendered = _render_run({
        "status": "error",
        "error": error,
        "error_details": {"type": "ToolUnavailableError",
                          "next_steps": [("Run `tu connections` to see what this "
                                          "terminal is connected to")]},
    })

    assert ("Check tool name spelling" in rendered) is spelling_expected, rendered


# ── when the owner withdraws access ──────────────────────────────────────────────

HTTPX_403 = (
    "Client error '403 Forbidden' for url 'http://localhost:8000/relay/x/mcp'\n"
    "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403"
)


def test_withdrawn_access_points_to_the_owner_not_a_new_key():
    """Measured: after the owner removed the borrower, and after the owner stopped sharing.

    Both used to say the key "may have expired or been revoked -- create a new API key". A new
    key gets the same 403; only the owner can change it.
    """
    message, missing = explain_remote_load_failure(RELAY, HTTPX_403, {BORROWER_KEY_ENV: KEY})

    assert missing is False
    assert "create a new API key" not in message
    assert "owner" in message and "new share code" in message
    assert "tu disconnect alice-gpu" in message


def test_a_401_from_the_relay_is_still_about_the_key():
    message, _ = explain_remote_load_failure(
        RELAY, "Client error '401 Unauthorized' for url ...", {BORROWER_KEY_ENV: KEY})

    assert "rejected the key" in message


def test_a_dead_share_code_message(home, monkeypatch, capsys):
    monkeypatch.setenv(BORROWER_KEY_ENV, KEY)
    monkeypatch.setattr(cli, "_platform_request",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("invalid share code")))
    args = SimpleNamespace(target="TU-SHARE-ABCD1234", service="http://127.0.0.1:8000",
                           name=None, platform=False)

    with pytest.raises(SystemExit):
        cli.cmd_connect(args)

    err = capsys.readouterr().err
    assert "copied whole" in err and "ask them for a fresh code" in err
    # The owner can limit a code's uses and set an end date; the platform refuses those
    # exactly like an unknown code, so the message has to name them.
    assert "number of uses" in err and "end date" in err


def test_disconnect_explains_what_changes_without_python_jargon(home, monkeypatch, capsys):
    import tooluniverse.remote_connections as rc

    monkeypatch.setattr(rc, "remove_connection", lambda target: {"name": "alice-gpu"})

    cli.cmd_disconnect(SimpleNamespace(target="alice-gpu"))

    out = capsys.readouterr().out
    assert "load_tools" not in out
    assert "restart" in out


def test_no_connections_lists_what_people_actually_hold(home, monkeypatch, capsys):
    import tooluniverse.remote_connections as rc

    monkeypatch.setattr(rc, "read_connections", list)

    cli.cmd_connections(SimpleNamespace(json=False))

    out = capsys.readouterr().out
    assert "TU-SHARE-" in out and "tool page link" in out
