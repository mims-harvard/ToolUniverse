import json
import os
import time
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class CountingTool(BaseTool):
    """Simple tool that counts invocations for cache verification."""
    call_count = 0
    STATIC_CACHE_VERSION = "1"

    def run(self, arguments, **kwargs):
        CountingTool.call_count += 1
        value = arguments.get("value", 0)
        return {"value": value, "calls": CountingTool.call_count}


_TOOL_CONFIG = {
    "name": "CountingToolTest",
    "type": "CountingTool",
    "description": "Simple counting tool for cache tests",
    "parameter": {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    },
}


def _make_tu():
    """Create a lightweight ToolUniverse with CountingTool registered."""
    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tu.register_custom_tool(CountingTool, tool_config=_TOOL_CONFIG)
    return tu


def _call(engine: ToolUniverse, value: int):
    return engine.run_one_function(
        {"name": "CountingToolTest", "arguments": {"value": value}},
        use_cache=True,
    )


def test_tooluniverse_cache_roundtrip(cache_env):
    """Cache hit on repeated call, persistent across restarts."""
    CountingTool.call_count = 0
    tu1 = _make_tu()

    result1 = _call(tu1, 7)
    assert result1["value"] == 7
    assert CountingTool.call_count == 1

    result2 = _call(tu1, 7)
    assert result2 == result1
    assert CountingTool.call_count == 1  # cache hit
    tu1.close()

    CountingTool.call_count = 0
    tu2 = _make_tu()

    result3 = _call(tu2, 7)
    assert result3 == result1  # loaded from persistent cache
    assert CountingTool.call_count == 0
    tu2.close()


def test_cache_invalidation_on_version_change(cache_env):
    """Bumping STATIC_CACHE_VERSION invalidates cached results."""
    CountingTool.call_count = 0
    tu = _make_tu()

    first = _call(tu, 1)
    assert CountingTool.call_count == 1

    assert _call(tu, 1) == first
    assert CountingTool.call_count == 1

    CountingTool.STATIC_CACHE_VERSION = "2"
    CountingTool.call_count = 0

    third = _call(tu, 1)
    assert third["calls"] == 1  # rerun due to version bump

    tu.close()
    CountingTool.STATIC_CACHE_VERSION = "1"


def test_cache_stats_and_clear(cache_env):
    """Cache stats report enabled; clearing resets memory size to 0."""
    CountingTool.call_count = 0
    tu = _make_tu()

    _call(tu, 5)
    assert tu.get_cache_stats()["enabled"]

    tu.clear_cache()
    assert tu.get_cache_stats()["memory"]["current_size"] == 0
    tu.close()


def test_cache_ttl(cache_env, monkeypatch):
    """Entries expire after the configured TTL."""
    monkeypatch.setenv("TOOLUNIVERSE_CACHE_DEFAULT_TTL", "1")
    CountingTool.call_count = 0
    tu = _make_tu()

    first = _call(tu, 9)
    assert CountingTool.call_count == 1
    assert _call(tu, 9) == first
    assert CountingTool.call_count == 1

    time.sleep(1.1)
    assert _call(tu, 9)["calls"] == 2  # rerun due to TTL expiry
    tu.close()


def test_dump_cache(cache_env):
    """dump_cache returns persisted entries."""
    CountingTool.call_count = 0
    tu = _make_tu()

    _call(tu, 3)
    entries = list(tu.dump_cache())
    assert entries
    assert any(e["namespace"] == "CountingToolTest" for e in entries)
    tu.close()


def test_batch_run_deduplicates_work(cache_env):
    """Duplicate batch calls share a single execution."""
    CountingTool.call_count = 0
    tu = _make_tu()

    batch_calls = [
        {"name": "CountingToolTest", "arguments": {"value": 1}},
        {"name": "CountingToolTest", "arguments": {"value": 1}},
        {"name": "CountingToolTest", "arguments": {"value": 2}},
        {"name": "CountingToolTest", "arguments": {"value": 2}},
    ]

    messages = tu.run(batch_calls, use_cache=True, max_workers=4, return_message=True)
    assert CountingTool.call_count == 2

    tool_payloads = [
        json.loads(msg["content"])["content"]
        for msg in messages[1:]
        if msg.get("role") == "tool"
    ]
    assert [payload["value"] for payload in tool_payloads] == [1, 1, 2, 2]
    tu.close()
