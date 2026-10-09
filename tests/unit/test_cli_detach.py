"""`tu remote login --detach` / `tu serve --share --detach` outlive the command that started them.

An AI assistant runs `tu` for a user, and its command runner ends what it started when its turn
ends. In a real Codex session `nohup tu remote login &` printed the approval link and the sign-in
was gone before anyone clicked it. `_run_detached` starts the same command in a new session,
waits until it is ready, and returns.
"""

import os
import signal
import sys
import time

import pytest

from tooluniverse import cli


@pytest.fixture(autouse=True)
def _log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DETACHED_LOG_DIR", tmp_path / "logs")
    return tmp_path / "logs"


def _stop(pid):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


@pytest.mark.skipif(os.name == "nt", reason="sessions are a POSIX notion")
def test_returns_when_ready_and_the_child_lives_in_its_own_session(_log_dir, capsys):
    child = "print('Authorize this computer', flush=True); print('Code: ABCD-EFGH', flush=True); import time; time.sleep(30)"
    cli._run_detached("login", ("Code:",), wait_seconds=20, command=[sys.executable, "-c", child])
    out = capsys.readouterr().out
    pid = int((_log_dir / "login.pid").read_text())
    try:
        assert "Code: ABCD-EFGH" in out
        assert "Running in the background" in out and str(_log_dir / "login.log") in out
        os.kill(pid, 0)  # still running after we returned
        assert os.getsid(pid) != os.getsid(0)  # outside our session, so outside its cleanup
    finally:
        _stop(pid)


def test_a_command_that_fails_early_exits_with_its_status(capsys):
    child = "print('Error: this computer is not signed in to ToolUniverse yet.'); raise SystemExit(2)"
    with pytest.raises(SystemExit) as raised:
        cli._run_detached("share-x", ("Sharing",), wait_seconds=20, command=[sys.executable, "-c", child])
    assert raised.value.code == 2
    assert "not signed in" in capsys.readouterr().out


def test_a_slow_start_returns_with_where_to_follow_it(_log_dir, capsys):
    started = time.monotonic()
    cli._run_detached("share-slow", ("Sharing",), wait_seconds=1, command=[sys.executable, "-c", "import time; time.sleep(30)"])
    pid = int((_log_dir / "share-slow.pid").read_text())
    try:
        assert time.monotonic() - started < 10
        assert "Still starting in the background" in capsys.readouterr().out
    finally:
        _stop(pid)


def test_the_flag_is_on_both_commands_and_refused_without_share():
    parser = cli.build_parser()
    assert parser.parse_args(["remote", "login", "--detach"]).detach is True
    args = parser.parse_args(["serve", "x.py", "--detach"])
    with pytest.raises(SystemExit) as raised:
        cli.cmd_serve(args)
    assert raised.value.code == 2


def test_slug_names_one_log_per_shared_computer():
    assert cli._detached_slug("Smith Lab GPU") == "smith-lab-gpu"
    assert cli._detached_slug("Share Test (Claude)") == "share-test-claude"
    assert cli._detached_slug("***") == "server"
