"""Concurrent first use of a tool initialises it once.

The HTTP API server runs every call in a thread pool, and its client gives up
after 30 seconds. Tool_RAG loads a 1.5B encoder when it is first initialised; a
caller that retried while that load was still running started a second,
overlapping load. Both failed ("Cannot copy out of meta tensor"), and the failed
initialisation removed Tool_RAG from the server until restart. Every test below
starts several callers at once on a tool that has not been initialised yet.
"""

import os
import threading
import time

import pytest

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

from tooluniverse import ToolUniverse
from tooluniverse import tool_registry
from tooluniverse.base_tool import BaseTool

CALLERS = 8


class SlowInitTool(BaseTool):
    """A tool whose construction takes a while, like loading a model."""

    lock = threading.Lock()
    created = 0
    active = 0
    most_active = 0

    def __init__(self, tool_config):
        with SlowInitTool.lock:
            SlowInitTool.created += 1
            SlowInitTool.active += 1
            SlowInitTool.most_active = max(
                SlowInitTool.most_active, SlowInitTool.active
            )
        try:
            time.sleep(0.2)
            super().__init__(tool_config)
        finally:
            with SlowInitTool.lock:
                SlowInitTool.active -= 1

    def run(self, arguments=None, **kwargs):
        return {"ok": True}


class FailingInitTool(BaseTool):
    attempts = 0

    def __init__(self, tool_config):
        FailingInitTool.attempts += 1
        time.sleep(0.1)
        raise RuntimeError("model load failed")


def config(name, tool_type):
    return {
        "name": name,
        "type": tool_type,
        "description": "Tool for lazy initialisation tests",
        "cacheable": False,
        "parameter": {"type": "object", "properties": {}, "required": []},
    }


def at_once(function):
    """Run ``function`` in CALLERS threads released together; return results."""
    barrier = threading.Barrier(CALLERS)
    results = [None] * CALLERS

    def call(index):
        barrier.wait()
        results[index] = function()

    threads = [threading.Thread(target=call, args=(i,)) for i in range(CALLERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    return results


@pytest.fixture
def tu():
    SlowInitTool.created = SlowInitTool.active = SlowInitTool.most_active = 0
    FailingInitTool.attempts = 0
    universe = ToolUniverse(tool_files={}, keep_default_tools=False)
    yield universe
    for name in ("FailingInitTool",):
        tool_registry._TOOL_ERRORS.pop(name, None)


@pytest.mark.unit
@pytest.mark.timeout(20)
def test_concurrent_first_lookups_build_one_instance(tu):
    """Eight simultaneous first lookups share one instance built once."""
    tu.register_custom_tool(
        SlowInitTool, tool_config=config("SlowInitTool", "SlowInitTool")
    )
    assert "SlowInitTool" not in tu.callable_functions

    instances = at_once(lambda: tu._get_tool_instance("SlowInitTool", cache=True))

    assert SlowInitTool.created == 1
    assert instances[0] is not None and all(i is instances[0] for i in instances)


@pytest.mark.unit
@pytest.mark.timeout(20)
def test_concurrent_first_calls_all_succeed(tu):
    """Simultaneous first calls all run, and the tool stays registered."""
    tu.register_custom_tool(
        SlowInitTool, tool_config=config("SlowInitTool", "SlowInitTool")
    )

    results = at_once(
        lambda: tu.run_one_function({"name": "SlowInitTool", "arguments": {}})
    )

    assert results == [{"ok": True}] * CALLERS
    assert SlowInitTool.created == 1
    assert "SlowInitTool" in tu.all_tool_dict


@pytest.mark.unit
@pytest.mark.timeout(20)
def test_initialisations_of_different_tools_do_not_overlap(tu):
    """Two tools' slow initialisations never run at the same time."""
    for name in ("SlowInitA", "SlowInitB"):
        tu.register_custom_tool(SlowInitTool, tool_config=config(name, "SlowInitTool"))

    at_once(
        lambda: [
            tu._get_tool_instance(n, cache=True) for n in ("SlowInitA", "SlowInitB")
        ]
    )

    assert SlowInitTool.created == 2
    assert SlowInitTool.most_active == 1


@pytest.mark.unit
@pytest.mark.timeout(20)
def test_a_failed_initialisation_is_attempted_once(tu):
    """Callers that waited on a failing initialisation do not repeat it."""
    tu.register_custom_tool(
        FailingInitTool, tool_config=config("FailingInitTool", "FailingInitTool")
    )

    instances = at_once(lambda: tu._get_tool_instance("FailingInitTool", cache=True))

    assert instances == [None] * CALLERS
    assert FailingInitTool.attempts == 1


@pytest.mark.unit
def test_uncached_lookups_still_build_fresh_instances(tu):
    """cache=False keeps building a new instance per lookup."""
    tu.register_custom_tool(
        SlowInitTool, tool_config=config("SlowInitTool", "SlowInitTool")
    )

    first = tu._get_tool_instance("SlowInitTool", cache=False)
    second = tu._get_tool_instance("SlowInitTool", cache=False)

    assert first is not second and SlowInitTool.created == 2
    assert "SlowInitTool" not in tu.callable_functions
