"""`tu serve` is the one command for sharing, whatever you are sharing.

Three things can be put behind the platform: your own decorated functions, an MCP server
you already run, and reviewed GPU models. Each used to need a different command -- the last
one lived behind `tu remote pool` -- so the single question that decides everything, what
am I sharing, was answered by choosing a command instead of a flag. `tu serve --help` is
now the whole map.

These tests pin the dispatch and the two defaults that cannot be unified. No subprocesses,
no network.
"""

from __future__ import annotations

import argparse

import pytest

from tooluniverse.cli import (
    DEFAULT_FILE_MODE_PORT,
    DEFAULT_POOL_MODE_PORT,
    SERVE_INPUTS,
    build_parser,
    cmd_serve,
)
from tooluniverse.remote_runtime import REMOTE_BY_SLUG


def serve_args(**overrides) -> argparse.Namespace:
    base = {"files": [], "forward": None, "allow": None, "share": False, "port": None}
    base.update(overrides)
    return argparse.Namespace(**base)


def run(monkeypatch, **overrides) -> dict:
    """Run cmd_serve with every real destination replaced, and report which one fired."""
    fired: dict = {}
    for name in (
        "_forward_remote_tool_server",
        "_start_remote_tool_server",
        "cmd_remote_pool",
    ):
        monkeypatch.setattr(
            f"tooluniverse.cli.{name}",
            lambda args, _name=name: fired.update(target=_name, port=args.port),
        )
    monkeypatch.setattr(
        "tooluniverse.smcp_server.run_default_stdio_server",
        lambda: fired.update(target="stdio"),
    )
    cmd_serve(serve_args(**overrides))
    return fired


# ── one flag per thing you can share ────────────────────────────────────────────


def test_decorated_functions_start_the_file_server(monkeypatch):
    assert (
        run(monkeypatch, files=["my_tool.py"])["target"] == "_start_remote_tool_server"
    )


def test_an_existing_mcp_server_is_forwarded(monkeypatch):
    assert (
        run(monkeypatch, forward="http://127.0.0.1:9/mcp")["target"]
        == "_forward_remote_tool_server"
    )


def test_reviewed_models_go_to_the_pool(monkeypatch):
    """The case that used to need `tu remote pool`."""
    assert run(monkeypatch, allow="boltz,esm")["target"] == "cmd_remote_pool"


def test_with_nothing_to_share_it_is_an_ordinary_local_server(monkeypatch):
    assert run(monkeypatch)["target"] == "stdio"


# ── the two defaults that cannot be unified ─────────────────────────────────────


def test_each_mode_gets_the_port_that_does_not_collide(monkeypatch):
    """8080 is the reviewed boltz provider's own port.

    A single default would put the model pool's endpoint on top of boltz on any host that
    shares it, so the two modes resolve differently and this records why.
    """
    assert run(monkeypatch, files=["t.py"])["port"] == DEFAULT_FILE_MODE_PORT
    assert run(monkeypatch, allow="boltz")["port"] == DEFAULT_POOL_MODE_PORT
    assert REMOTE_BY_SLUG["boltz"].port == DEFAULT_FILE_MODE_PORT


def test_the_pool_port_collides_with_no_reviewed_provider():
    taken = {deployment.port for deployment in REMOTE_BY_SLUG.values()}

    assert DEFAULT_POOL_MODE_PORT not in taken


def test_an_explicit_port_is_respected_in_either_mode(monkeypatch):
    assert run(monkeypatch, files=["t.py"], port=9100)["port"] == 9100
    assert run(monkeypatch, allow="boltz", port=9100)["port"] == 9100


# ── saying no clearly ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"files": ["t.py"], "forward": "http://a/mcp"}, "not 2"),
        ({"files": ["t.py"], "allow": "boltz"}, "not 2"),
        ({"forward": "http://a/mcp", "allow": "boltz"}, "not 2"),
        ({"files": ["t.py"], "forward": "http://a/mcp", "allow": "boltz"}, "not 3"),
    ],
)
def test_two_things_to_share_is_refused_and_says_which(
    monkeypatch, overrides, expected
):
    """The message names what it found, so the fix does not require re-reading --help."""
    with pytest.raises(SystemExit):
        run(monkeypatch, **overrides)


def test_sharing_nothing_names_all_three_options(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        run(monkeypatch, share=True)

    message = capsys.readouterr().err
    for fragment in ("TOOL.py", "--forward", "--allow"):
        assert fragment in message, message


# ── the old spelling keeps working ──────────────────────────────────────────────


def test_tu_remote_pool_still_parses(monkeypatch):
    """An existing script or systemd unit must not break on an upgrade."""
    parser = build_parser()

    args = parser.parse_args(["remote", "pool", "--allow", "boltz", "--share"])

    assert args.allow == "boltz"
    assert args.func.__name__ == "cmd_remote_pool"


def test_both_spellings_reach_the_same_implementation():
    parser = build_parser()

    through_serve = parser.parse_args(["serve", "--allow", "boltz"])
    through_remote = parser.parse_args(["remote", "pool", "--allow", "boltz"])

    # cmd_serve forwards to cmd_remote_pool, so the two differ only in entry point.
    assert through_serve.func.__name__ == "cmd_serve"
    assert through_remote.func.__name__ == "cmd_remote_pool"


def test_serve_exposes_every_input_in_one_help(capsys):
    """If an input is missing from this parser, a user has to find another command."""
    parser = build_parser()

    args = parser.parse_args(["serve", "--allow", "boltz,esm", "--max-active", "2"])

    assert args.allow == "boltz,esm"
    assert args.max_active == 2
    assert {name for name, _ in SERVE_INPUTS} == {"files", "forward", "allow"}


# ── a flag that parses but does nothing is worse than no flag ────────────────────


def test_pass_env_is_wired_through_both_entry_points(monkeypatch):
    """--pass-env is a security control, so accepting it and ignoring it would be a lie.

    The two spellings were built on separate branches, and for a while `tu serve` accepted
    this flag while only `tu remote pool` acted on it. Nothing failed: argparse took the
    value and the pool never read it. This asserts the value actually reaches the pool.
    """
    seen: dict = {}

    class StopAfterConstruction(Exception):
        """Raised to end the command once the pool has been built with its kwargs."""

    class Recorder:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def __getattr__(self, name):
            # The kwargs are the whole assertion; stop before the command does real work.
            raise StopAfterConstruction(name)

    parser = build_parser()
    for argv in (
        ["serve", "--allow", "boltz", "--pass-env", "SITE_LICENCE"],
        ["remote", "pool", "--allow", "boltz", "--pass-env", "SITE_LICENCE"],
    ):
        seen.clear()
        args = parser.parse_args(argv)
        assert args.pass_env == ["SITE_LICENCE"], argv
        monkeypatch.setattr("tooluniverse.remote_pool.ProviderPool", Recorder)
        monkeypatch.setattr(
            "tooluniverse.remote_runtime.check_environment",
            lambda *a, **k: {"ok": True, "checks": []},
        )
        monkeypatch.setattr(
            "tooluniverse.remote_runtime.resolve_python",
            lambda *a, **k: "/usr/bin/python3",
        )
        # Construction records the kwargs; Recorder then stops the command.
        with pytest.raises((StopAfterConstruction, SystemExit)):
            args.func(args)
        assert seen.get("extra_env") == ("SITE_LICENCE",), (
            f"{argv} -> {seen.get('extra_env')}"
        )
