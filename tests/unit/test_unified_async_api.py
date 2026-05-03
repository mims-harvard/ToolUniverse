"""Tests for unified async API -- context-aware execution."""

import asyncio
import inspect
import pytest
from tooluniverse import ToolUniverse

_MOCK_PARAMETER = {
    "type": "object",
    "properties": {"param": {"type": "string"}},
    "required": ["param"],
}


class MockSyncTool:
    """Mock synchronous tool."""

    name = "MockSyncTool"
    description = "Mock sync tool"
    parameter = _MOCK_PARAMETER
    fields = {"type": "REST"}

    def run(self, arguments):
        return {"data": {"result": f"Sync: {arguments.get('param', 'default')}"}}

    def get_batch_concurrency_limit(self):
        return 0


class MockAsyncTool:
    """Mock asynchronous tool."""

    name = "MockAsyncTool"
    description = "Mock async tool"
    parameter = _MOCK_PARAMETER
    fields = {"type": "REST"}

    async def run(self, arguments):
        await asyncio.sleep(0.01)
        return {"data": {"result": f"Async: {arguments.get('param', 'default')}"}}

    def get_batch_concurrency_limit(self):
        return 0


def _register_mock(tu, tool):
    """Register a mock tool into a ToolUniverse instance."""
    tu.all_tool_dict[tool.name] = {
        "name": tool.name,
        "description": tool.description,
        "parameter": tool.parameter,
        "type": "REST",
    }
    tu.callable_functions[tool.name] = tool


@pytest.fixture
def tu_with_mock_tools():
    """ToolUniverse instance with mock tools."""
    tu = ToolUniverse()
    _register_mock(tu, MockSyncTool())
    _register_mock(tu, MockAsyncTool())
    return tu


# -- Sync context with sync tool --


def test_sync_context_sync_tool_via_run(tu_with_mock_tools):
    """Test: Sync context, sync tool, using tu.run()."""
    result = tu_with_mock_tools.run({
        "name": "MockSyncTool",
        "arguments": {"param": "test1"}
    })

    # Should return result directly (not coroutine)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Sync: test1"


def test_sync_context_sync_tool_via_tools(tu_with_mock_tools):
    """Test: Sync context, sync tool, using tu.tools.X()."""
    result = tu_with_mock_tools.tools.MockSyncTool(param="test2")

    # Should return result directly (not coroutine)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Sync: test2"


# -- Sync context with async tool --

def test_sync_context_async_tool_via_run(tu_with_mock_tools):
    """Test: Sync context, async tool, using tu.run() - blocks and returns result."""
    result = tu_with_mock_tools.run({
        "name": "MockAsyncTool",
        "arguments": {"param": "test3"}
    })

    # Should block and return result (not coroutine)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Async: test3"


def test_sync_context_async_tool_via_tools(tu_with_mock_tools):
    """Test: Sync context, async tool, using tu.tools.X() - blocks and returns result."""
    result = tu_with_mock_tools.tools.MockAsyncTool(param="test4")

    # Should block and return result (not coroutine)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Async: test4"


# -- Async context with sync tool --

@pytest.mark.asyncio
async def test_async_context_sync_tool_via_run(tu_with_mock_tools):
    """Test: Async context, sync tool, using tu.run() - runs in thread pool."""
    result = await tu_with_mock_tools.run({
        "name": "MockSyncTool",
        "arguments": {"param": "test5"}
    })

    # Should return result (not coroutine, since we awaited)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Sync: test5"


@pytest.mark.asyncio
async def test_async_context_sync_tool_via_tools(tu_with_mock_tools):
    """Test: Async context, sync tool, using tu.tools.X() - runs in thread pool."""
    result = await tu_with_mock_tools.tools.MockSyncTool(param="test6")

    # Should return result (not coroutine, since we awaited)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Sync: test6"


# -- Async context with async tool --

@pytest.mark.asyncio
async def test_async_context_async_tool_via_run(tu_with_mock_tools):
    """Test: Async context, async tool, using tu.run() - non-blocking."""
    result = await tu_with_mock_tools.run({
        "name": "MockAsyncTool",
        "arguments": {"param": "test7"}
    })

    # Should return result (not coroutine, since we awaited)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Async: test7"


@pytest.mark.asyncio
async def test_async_context_async_tool_via_tools(tu_with_mock_tools):
    """Test: Async context, async tool, using tu.tools.X() - non-blocking."""
    result = await tu_with_mock_tools.tools.MockAsyncTool(param="test8")

    # Should return result (not coroutine, since we awaited)
    assert not inspect.iscoroutine(result)
    assert result["data"]["result"] == "Async: test8"


# -- Parallel execution in async context --

@pytest.mark.asyncio
async def test_parallel_execution_async_context(tu_with_mock_tools):
    """Test: Run multiple tools in parallel in async context."""
    # Run 3 async tools in parallel
    results = await asyncio.gather(
        tu_with_mock_tools.run({"name": "MockAsyncTool", "arguments": {"param": "a"}}),
        tu_with_mock_tools.run({"name": "MockAsyncTool", "arguments": {"param": "b"}}),
        tu_with_mock_tools.run({"name": "MockAsyncTool", "arguments": {"param": "c"}}),
    )

    assert len(results) == 3
    assert results[0]["data"]["result"] == "Async: a"
    assert results[1]["data"]["result"] == "Async: b"
    assert results[2]["data"]["result"] == "Async: c"


@pytest.mark.asyncio
async def test_parallel_execution_via_tools_api(tu_with_mock_tools):
    """Test: Run multiple tools in parallel using tu.tools.X() API."""
    results = await asyncio.gather(
        tu_with_mock_tools.tools.MockAsyncTool(param="x"),
        tu_with_mock_tools.tools.MockAsyncTool(param="y"),
        tu_with_mock_tools.tools.MockAsyncTool(param="z"),
    )

    assert len(results) == 3
    assert results[0]["data"]["result"] == "Async: x"
    assert results[1]["data"]["result"] == "Async: y"
    assert results[2]["data"]["result"] == "Async: z"


# -- Batch execution --

@pytest.mark.asyncio
async def test_batch_execution_async_context(tu_with_mock_tools):
    """Test: Batch execution in async context (parallel)."""
    calls = [
        {"name": "MockAsyncTool", "arguments": {"param": "batch1"}},
        {"name": "MockAsyncTool", "arguments": {"param": "batch2"}},
        {"name": "MockSyncTool", "arguments": {"param": "batch3"}},
    ]

    # In async context, run() detects list and calls _run_async
    results = await tu_with_mock_tools.run(calls)

    assert len(results) == 3
    assert results[0]["data"]["result"] == "Async: batch1"
    assert results[1]["data"]["result"] == "Async: batch2"
    assert results[2]["data"]["result"] == "Sync: batch3"


def test_batch_execution_sync_context(tu_with_mock_tools):
    """Test: Batch execution in sync context (sequential)."""
    calls = [
        {"name": "MockAsyncTool", "arguments": {"param": "sync_batch1"}},
        {"name": "MockSyncTool", "arguments": {"param": "sync_batch2"}},
    ]

    # In sync context, blocks and returns results
    results = tu_with_mock_tools.run(calls)

    assert len(results) == 2
    assert results[0]["data"]["result"] == "Async: sync_batch1"
    assert results[1]["data"]["result"] == "Sync: sync_batch2"


# -- Context detection verification --

def test_context_detection_sync():
    """Verify context detection returns correct type in sync context."""
    # Should NOT detect async context
    try:
        asyncio.get_running_loop()
        pytest.fail("Should not detect async context in sync test")
    except RuntimeError:
        pass  # Expected


@pytest.mark.asyncio
async def test_context_detection_async():
    """Verify context detection returns correct type in async context."""
    # Should detect async context
    loop = asyncio.get_running_loop()
    assert loop is not None


# -- Error handling --

@pytest.mark.asyncio
async def test_error_handling_async_context(tu_with_mock_tools):
    """Test: Error handling in async context."""
    # Call with missing required parameter
    with pytest.raises(Exception):  # Will raise validation error
        await tu_with_mock_tools.run({
            "name": "MockAsyncTool",
            "arguments": {}  # Missing 'param'
        }, validate=True)


def test_error_handling_sync_context(tu_with_mock_tools):
    """Test: Error handling in sync context."""
    # Call with missing required parameter
    with pytest.raises(Exception):  # Will raise validation error
        tu_with_mock_tools.run({
            "name": "MockAsyncTool",
            "arguments": {}  # Missing 'param'
        }, validate=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
