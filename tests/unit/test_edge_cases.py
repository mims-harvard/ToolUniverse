"""
Edge case tests for unified async API and error handling.

Tests critical scenarios identified in code quality review.
"""

import asyncio
import pytest
import pytest_asyncio
from tooluniverse import ToolUniverse
from tooluniverse.exceptions import ToolError


def _handle_error(exception):
    """Shared error handler for mock tools."""
    return ToolError(
        message=str(exception),
        error_type="execution_error",
        details={"exception_type": type(exception).__name__},
    )


def _register_tool(tu, tool):
    """Register a mock tool into a ToolUniverse instance."""
    tu.all_tool_dict[tool.name] = {
        "name": tool.name,
        "description": tool.description,
        "parameter": tool.parameter,
        "type": "REST",
    }
    tu.callable_functions[tool.name] = tool


class RacyProgressTool:
    """Tool that generates many rapid progress updates to test race conditions."""

    name = "RacyProgressTool"
    description = "Tool with racy progress updates"
    parameter = {
        "type": "object",
        "properties": {"iterations": {"type": "integer"}},
        "required": [],
    }
    fields = {"type": "REST"}
    handle_error = staticmethod(_handle_error)

    def get_batch_concurrency_limit(self):
        return 0

    async def run(self, arguments, progress=None):
        iterations = arguments.get("iterations", 100)
        for i in range(iterations):
            if progress:
                await progress.set_message(f"Iteration {i}/{iterations}")
            await asyncio.sleep(0.001)
        return {"data": {"iterations_completed": iterations}}


class FailingSometimesTool:
    """Tool that fails based on input parameter."""

    name = "FailingSometimesTool"
    description = "Tool that can be made to fail"
    parameter = {
        "type": "object",
        "properties": {
            "should_fail": {"type": "boolean"},
            "error_message": {"type": "string"},
        },
        "required": [],
    }
    fields = {"type": "REST"}
    handle_error = staticmethod(_handle_error)

    def get_batch_concurrency_limit(self):
        return 0

    async def run(self, arguments):
        if arguments.get("should_fail", False):
            raise ValueError(arguments.get("error_message", "Intentional failure"))
        return {"data": {"status": "success"}}


class SlowTool:
    """Tool that takes a configurable time to complete."""

    name = "SlowTool"
    description = "Slow tool for timeout testing"
    parameter = {
        "type": "object",
        "properties": {"delay": {"type": "number"}},
        "required": [],
    }
    fields = {"type": "REST"}
    handle_error = staticmethod(_handle_error)

    def get_batch_concurrency_limit(self):
        return 0

    async def run(self, arguments):
        delay = arguments.get("delay", 1.0)
        await asyncio.sleep(delay)
        return {"data": {"delay": delay}}


EDGE_TOOL_CLASSES = [RacyProgressTool, FailingSometimesTool, SlowTool]


@pytest_asyncio.fixture
async def tu_with_edge_tools():
    """ToolUniverse with edge case testing tools."""
    tu = ToolUniverse()
    for cls in EDGE_TOOL_CLASSES:
        _register_tool(tu, cls())
    yield tu
    try:
        tu.close()
    except Exception:
        pass


# -- Batch execution with mixed success/failure --


@pytest.mark.asyncio
async def test_batch_execution_error_isolation(tu_with_edge_tools):
    """One failing tool should not abort other concurrent operations."""
    calls = [
        {"name": "FailingSometimesTool", "arguments": {"should_fail": False}},
        {"name": "FailingSometimesTool", "arguments": {"should_fail": True, "error_message": "Test error"}},
        {"name": "FailingSometimesTool", "arguments": {"should_fail": False}},
    ]

    results = await tu_with_edge_tools.run(calls)

    assert len(results) == 3
    assert "data" in results[0]
    assert results[0]["data"]["status"] == "success"
    assert "error" in results[1]
    assert "Test error" in results[1]["error"]
    assert "data" in results[2]
    assert results[2]["data"]["status"] == "success"


@pytest.mark.asyncio
async def test_batch_all_failures(tu_with_edge_tools):
    """Batch execution where all tools fail returns error dicts for each."""
    calls = [
        {"name": "FailingSometimesTool", "arguments": {"should_fail": True, "error_message": f"Error {i}"}}
        for i in range(3)
    ]

    results = await tu_with_edge_tools.run(calls)

    assert len(results) == 3
    for i, result in enumerate(results):
        assert "error" in result
        assert f"Error {i}" in result["error"]


def test_batch_sync_context_error_isolation():
    """Error isolation works in sync context too."""
    tu = ToolUniverse()
    _register_tool(tu, FailingSometimesTool())

    calls = [
        {"name": "FailingSometimesTool", "arguments": {"should_fail": False}},
        {"name": "FailingSometimesTool", "arguments": {"should_fail": True}},
        {"name": "FailingSometimesTool", "arguments": {"should_fail": False}},
    ]

    results = tu.run(calls)

    assert len(results) == 3
    assert "data" in results[0]
    assert "error" in results[1]
    assert "data" in results[2]

    try:
        tu.close()
    except Exception:
        pass


# -- Race condition testing (TaskProgress) --


@pytest.mark.asyncio
async def test_concurrent_progress_updates():
    """Concurrent progress updates don't cause race conditions."""
    from tooluniverse.task_manager import TaskManager

    tu = ToolUniverse()
    _register_tool(tu, RacyProgressTool())
    manager = TaskManager(tool_universe=tu)

    try:
        task_id = await manager.create_task(
            tool_name="RacyProgressTool",
            arguments={"iterations": 100},
            ttl=60000,
        )

        messages_seen = []
        for _ in range(50):
            await asyncio.sleep(0.01)
            try:
                status = await manager.get_status(task_id)
                msg = status.get("statusMessage", "")
                if msg and msg not in messages_seen:
                    messages_seen.append(msg)
                if status["status"] == "completed":
                    break
            except Exception as e:
                pytest.fail(f"Race condition detected: {e}")

        result = await manager.get_result(task_id)
        assert result["data"]["iterations_completed"] == 100
        assert len(messages_seen) > 0
    finally:
        await manager.stop()
        tu.close()


@pytest.mark.asyncio
async def test_parallel_tasks_with_progress():
    """Multiple tasks updating progress concurrently all complete successfully."""
    from tooluniverse.task_manager import TaskManager

    tu = ToolUniverse()
    _register_tool(tu, RacyProgressTool())
    manager = TaskManager(tool_universe=tu)

    try:
        task_ids = []
        for i in range(5):
            task_id = await manager.create_task(
                tool_name="RacyProgressTool",
                arguments={"iterations": 50},
                ttl=60000,
            )
            task_ids.append(task_id)

        results = await asyncio.gather(*[
            manager.get_result(task_id) for task_id in task_ids
        ])

        assert len(results) == 5
        for result in results:
            assert result["data"]["iterations_completed"] == 50
    finally:
        await manager.stop()
        tu.close()


# -- Error handling edge cases --


@pytest.mark.asyncio
async def test_empty_batch_execution(tu_with_edge_tools):
    """Batch execution with empty list returns empty list."""
    results = await tu_with_edge_tools.run([])
    assert results == []


@pytest.mark.asyncio
async def test_single_item_batch(tu_with_edge_tools):
    """Batch execution with single item works correctly."""
    calls = [{"name": "FailingSometimesTool", "arguments": {"should_fail": False}}]
    results = await tu_with_edge_tools.run(calls)
    assert len(results) == 1
    assert "data" in results[0]


@pytest.mark.asyncio
async def test_exception_types_in_batch(tu_with_edge_tools):
    """Different exception types are all properly handled in batch."""

    class MultiExceptionTool:
        name = "MultiExceptionTool"
        description = "Tool with different exceptions"
        parameter = {
            "type": "object",
            "properties": {"exception_type": {"type": "string"}},
            "required": [],
        }
        fields = {"type": "REST"}
        handle_error = staticmethod(_handle_error)

        def get_batch_concurrency_limit(self):
            return 0

        async def run(self, arguments):
            exc_type = arguments.get("exception_type", "value")
            exceptions = {
                "value": ValueError("Value error"),
                "type": TypeError("Type error"),
                "key": KeyError("Key error"),
                "runtime": RuntimeError("Runtime error"),
            }
            if exc_type in exceptions:
                raise exceptions[exc_type]
            return {"data": {"status": "success"}}

    _register_tool(tu_with_edge_tools, MultiExceptionTool())

    calls = [
        {"name": "MultiExceptionTool", "arguments": {"exception_type": t}}
        for t in ["value", "type", "key", "runtime"]
    ]

    results = await tu_with_edge_tools.run(calls)

    assert len(results) == 4
    for result in results:
        assert "error" in result


# -- Performance and resource tests --


@pytest.mark.asyncio
async def test_many_parallel_tasks(tu_with_edge_tools):
    """System handles many parallel tasks efficiently."""
    calls = [{"name": "SlowTool", "arguments": {"delay": 0.1}} for _ in range(20)]

    import time
    start = time.time()
    results = await tu_with_edge_tools.run(calls)
    elapsed = time.time() - start

    assert len(results) == 20
    for result in results:
        assert "data" in result
        assert result["data"]["delay"] == 0.1
    assert elapsed < 0.5  # Parallel, not sequential


@pytest.mark.asyncio
async def test_mixed_speed_batch(tu_with_edge_tools):
    """Batch with mixed fast and slow tools preserves result order."""
    calls = [
        {"name": "SlowTool", "arguments": {"delay": 0.01}},
        {"name": "SlowTool", "arguments": {"delay": 0.1}},
        {"name": "SlowTool", "arguments": {"delay": 0.01}},
    ]

    results = await tu_with_edge_tools.run(calls)

    assert len(results) == 3
    assert results[0]["data"]["delay"] == 0.01
    assert results[1]["data"]["delay"] == 0.1
    assert results[2]["data"]["delay"] == 0.01


# -- Context switching edge cases --


@pytest.mark.asyncio
async def test_nested_async_calls(tu_with_edge_tools):
    """Sequential async calls work correctly."""
    result1 = await tu_with_edge_tools.run({
        "name": "FailingSometimesTool",
        "arguments": {"should_fail": False},
    })
    result2 = await tu_with_edge_tools.run({
        "name": "FailingSometimesTool",
        "arguments": {"should_fail": False},
    })

    assert "data" in result1
    assert "data" in result2


def test_sync_to_async_to_sync_nesting():
    """Sync context calling async tool works correctly."""
    tu = ToolUniverse()
    _register_tool(tu, FailingSometimesTool())

    result = tu.run({
        "name": "FailingSometimesTool",
        "arguments": {"should_fail": False},
    })

    assert "data" in result
    assert result["data"]["status"] == "success"

    try:
        tu.close()
    except Exception:
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
