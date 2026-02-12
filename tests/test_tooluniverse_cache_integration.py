import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class CountingTool(BaseTool):
    call_count = 0
    STATIC_CACHE_VERSION = "1"

    def run(self, arguments, **kwargs):
        CountingTool.call_count += 1
        value = arguments.get("value", 0)
        return {"value": value, "calls": CountingTool.call_count}


@pytest.fixture
def tool_config():
    return {
        "name": "CountingToolTest",
        "type": "CountingTool",
        "description": "Simple counting tool for cache tests",
        "parameter": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    }


def _register_tool(engine: ToolUniverse, tool_config):
    engine.register_custom_tool(CountingTool, tool_config=tool_config)


def _call(engine: ToolUniverse, value: int):
    return engine.run_one_function(
        {"name": "CountingToolTest", "arguments": {"value": value}},
        use_cache=True,
    )

def _with_env(**overrides):
    env_vars = {
        "TOOLUNIVERSE_CACHE_ENABLED": "true",
        "TOOLUNIVERSE_CACHE_PERSIST": "true",
        "TOOLUNIVERSE_CACHE_MEMORY_SIZE": "4",
    }
    env_vars.update(overrides)
    old_env = {k: os.environ.get(k) for k in env_vars}
    os.environ.update(env_vars)
    return env_vars, old_env

def _restore_env(old_env):
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_tooluniverse_cache_roundtrip(tool_config):
    with TemporaryDirectory() as tmpdir:
        env_vars, old_env = _with_env(
            TOOLUNIVERSE_CACHE_PATH=str(Path(tmpdir) / "cache.sqlite")
        )
        try:
            CountingTool.call_count = 0
            tu1 = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu1, tool_config)

            result1 = _call(tu1, 7)
            assert result1["value"] == 7
            assert CountingTool.call_count == 1

            result2 = _call(tu1, 7)
            assert result2 == result1
            assert CountingTool.call_count == 1  # cache hit

            tu1.close()

            CountingTool.call_count = 0
            tu2 = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu2, tool_config)

            result3 = _call(tu2, 7)
            assert result3 == result1  # loaded from persistent cache
            assert CountingTool.call_count == 0  # run() not invoked

            tu2.close()
        finally:
            _restore_env(old_env)


def test_cache_invalidation_on_version_change(tool_config):
    with TemporaryDirectory() as tmpdir:
        env_vars, old_env = _with_env(
            TOOLUNIVERSE_CACHE_PATH=str(Path(tmpdir) / "cache.sqlite")
        )
        try:
            CountingTool.call_count = 0
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu, tool_config)

            first = _call(tu, 1)
            assert CountingTool.call_count == 1

            second = _call(tu, 1)
            assert second == first
            assert CountingTool.call_count == 1

            CountingTool.STATIC_CACHE_VERSION = "2"
            CountingTool.call_count = 0

            third = _call(tu, 1)
            assert third["calls"] == 1  # rerun due to version bump

            tu.close()
        finally:
            CountingTool.STATIC_CACHE_VERSION = "1"
            _restore_env(old_env)


def test_cache_stats_and_clear(tool_config):
    with TemporaryDirectory() as tmpdir:
        env_vars, old_env = _with_env(
            TOOLUNIVERSE_CACHE_PATH=str(Path(tmpdir) / "cache.sqlite")
        )
        try:
            CountingTool.call_count = 0
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu, tool_config)

            _call(tu, 5)
            stats_before = tu.get_cache_stats()
            assert stats_before["enabled"]

            tu.clear_cache()
            stats_after = tu.get_cache_stats()
            assert stats_after["memory"]["current_size"] == 0

            tu.close()
        finally:
            _restore_env(old_env)


def test_cache_ttl(tool_config):
    with TemporaryDirectory() as tmpdir:
        env_vars, old_env = _with_env(
            TOOLUNIVERSE_CACHE_PATH=str(Path(tmpdir) / "cache.sqlite"),
            TOOLUNIVERSE_CACHE_DEFAULT_TTL="1",
        )
        try:
            CountingTool.call_count = 0
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu, tool_config)

            first = _call(tu, 9)
            assert CountingTool.call_count == 1

            result_hit = _call(tu, 9)
            assert result_hit == first
            assert CountingTool.call_count == 1

            import time

            time.sleep(1.1)
            result_after_ttl = _call(tu, 9)
            assert result_after_ttl["calls"] == 2  # rerun due to TTL expiry

            tu.close()
        finally:
            _restore_env(old_env)


def test_dump_cache(tool_config):
    with TemporaryDirectory() as tmpdir:
        env_vars, old_env = _with_env(
            TOOLUNIVERSE_CACHE_PATH=str(Path(tmpdir) / "cache.sqlite")
        )
        try:
            CountingTool.call_count = 0
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu, tool_config)

            _call(tu, 3)
            entries = list(tu.dump_cache())
            assert entries
            assert any(e["namespace"] == "CountingToolTest" for e in entries)

            tu.close()
        finally:
            _restore_env(old_env)


def test_batch_run_deduplicates_work(tool_config):
    with TemporaryDirectory() as tmpdir:
        env_vars, old_env = _with_env(
            TOOLUNIVERSE_CACHE_PATH=str(Path(tmpdir) / "cache.sqlite")
        )
        try:
            CountingTool.call_count = 0
            tu = ToolUniverse(tool_files={}, keep_default_tools=False)
            _register_tool(tu, tool_config)

            batch_calls = [
                {"name": "CountingToolTest", "arguments": {"value": 1}},
                {"name": "CountingToolTest", "arguments": {"value": 1}},
                {"name": "CountingToolTest", "arguments": {"value": 2}},
                {"name": "CountingToolTest", "arguments": {"value": 2}},
            ]

            messages = tu.run(batch_calls, use_cache=True, max_workers=4, return_message=True)

            assert CountingTool.call_count == 2  # one execution per unique arguments

            tool_payloads = [
                json.loads(msg["content"])["content"]
                for msg in messages[1:]
                if msg.get("role") == "tool"
            ]
            assert [payload["value"] for payload in tool_payloads] == [1, 1, 2, 2]

            tu.close()
        finally:
            _restore_env(old_env)
