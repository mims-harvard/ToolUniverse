"""A connected machine that was offline at startup is tried again when its tool is wanted.

Measured through `tu serve` with a real MCP client: an assistant started while the lender's
machine was offline kept answering "not available" after the machine came back -- although the
message promised it "will load again once its owner brings it back online" -- until the
assistant was restarted. With this, the same session's next call ran on the machine.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tooluniverse.execute_function import ToolUniverse


@pytest.fixture
def universe(monkeypatch):
    attempts = []
    fake = SimpleNamespace(
        all_tool_dict={"local_tool": {}},
        _failed_remote_connections={"alice_gpu_": {"message": "offline"},
                                    "bob_box_": {"message": "offline"}},
        _REMOTE_RELOAD_INTERVAL=30.0,
        _process_mcp_auto_loaders=lambda only_prefix=None: attempts.append(only_prefix),
    )
    clock = [1000.0]
    import time

    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    def reload(name):
        ToolUniverse._reload_failed_remote_connection(fake, name)

    return reload, attempts, clock


def test_a_tool_from_a_failed_connection_retries_that_connection(universe):
    reload, attempts, _ = universe

    reload("alice_gpu_predict")

    assert attempts == ["alice_gpu_"]


def test_it_is_not_retried_on_every_call(universe):
    reload, attempts, clock = universe

    reload("alice_gpu_predict")
    clock[0] += 5
    reload("alice_gpu_predict")
    assert attempts == ["alice_gpu_"]

    clock[0] += 30
    reload("alice_gpu_predict")
    assert attempts == ["alice_gpu_", "alice_gpu_"]


@pytest.mark.parametrize("name", ["local_tool", "PubMed_search", ""])
def test_other_tools_never_trigger_a_reload(universe, name):
    reload, attempts, _ = universe

    reload(name)

    assert attempts == []


def test_reloading_one_connection_keeps_the_others_failures(monkeypatch):
    universe = ToolUniverse.__new__(ToolUniverse)
    universe._failed_remote_connections = {"alice_gpu_": {"message": "x"},
                                           "bob_box_": {"message": "y"}}
    universe.all_tools = []
    universe.all_tool_dict = {}
    import logging

    universe.logger = logging.getLogger("test")

    ToolUniverse._process_mcp_auto_loaders(universe, only_prefix="alice_gpu_")

    assert "bob_box_" in universe._failed_remote_connections
    assert "alice_gpu_" not in universe._failed_remote_connections


def test_running_a_tool_asks_for_the_reload_first(monkeypatch, tmp_path):
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_DIR", str(tmp_path / "cache"))
    universe = ToolUniverse(tool_files={}, keep_default_tools=False, load_workspace=False)
    asked = []
    monkeypatch.setattr(universe, "_reload_failed_remote_connection", asked.append)

    universe.run_one_function({"name": "alice_gpu_predict", "arguments": {}})

    assert asked == ["alice_gpu_predict"]
