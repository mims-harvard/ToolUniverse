"""What `tu connect` says once it has connected.

It used to end with "Tool name: alice_gpu_<tool>" and "It will load on the next
ToolUniverse.load_tools() or `tu serve` start" -- a placeholder where the name should be, and a
Python call the person had never made. Nothing said how to try the tool, or how to reach it from
an AI assistant, which is where most people meant to use it.
"""

from __future__ import annotations

from tooluniverse.cli import _after_connect_lines


def test_a_named_tool_is_offered_to_try():
    out = "\n".join(_after_connect_lines({"prefix": "x_"}, ["x_predict"]))

    assert "tu info x_predict" in out


def test_a_machine_whose_tools_are_not_listed_says_how_to_list_them():
    out = "\n".join(_after_connect_lines({"prefix": "alice_gpu_"}, []))

    assert "tu grep alice_gpu_" in out
    assert "<tool>" not in out


def test_the_ai_assistant_route_is_given():
    out = "\n".join(_after_connect_lines({"prefix": "x_"}, ["x_predict"]))

    assert "claude mcp add" in out and "tu serve" in out
    assert "load_tools" not in out


def test_connecting_a_published_tool_names_it_and_says_what_next(tmp_path, monkeypatch, capsys):
    """Drives cmd_connect itself, so the wiring is covered and not only the helper."""
    import os
    import sys

    from tooluniverse import cli

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TU_API_KEY", raising=False)
    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY", raising=False)
    monkeypatch.setattr(cli, "_read_stored_remote_key", lambda: "")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(cli, "_platform_request", lambda *a, **k: {
        "tool_type": "remote-mcp", "name": "Shared Model", "description": "x",
        "input_schema": "{}"})

    cli.cmd_connect(type("A", (), {
        "target": "8faedc52-c800-4072-ab29-e0999cf29f74",
        "service": "https://tooluniverse-backend.onrender.com",
        "name": None, "auth_env": None, "platform": True})())

    out = capsys.readouterr().out
    assert "Tools:" in out
    assert "tu info " in out
    assert "<tool>" not in out and "load_tools" not in out
    os.environ.pop("TU_API_KEY", None)
