"""
Integration tests for MCP Tasks with unified async API.

Tests TaskManager, async tools, progress reporting, and MCP protocol integration.
"""

import asyncio
import pytest
import pytest_asyncio
import time
from datetime import datetime
from tooluniverse.task_manager import TaskManager, Task


def _make_mock_tool(name, description, parameter, run_fn):
    """Create a minimal mock tool object with the given run function."""
    class _Tool:
        pass

    tool = _Tool()
    tool.name = name
    tool.description = description
    tool.parameter = parameter
    tool.fields = {"type": "REST"}
    tool.run = run_fn
    tool.get_batch_concurrency_limit = lambda: 0
    return tool


def _register_tool(tu, tool):
    """Register a mock tool into a ToolUniverse instance."""
    tu.all_tool_dict[tool.name] = {
        "name": tool.name,
        "description": tool.description,
        "parameter": tool.parameter,
        "type": "REST",
    }
    tu.callable_functions[tool.name] = tool


async def _long_running_run(arguments, progress=None):
    """Simulates a 5-second job with progress updates."""
    job_id = arguments.get("job_id", "test_job")
    if progress:
        await progress.set_message(f"Job {job_id} submitted")
    for i in range(5):
        await asyncio.sleep(1)
        if progress:
            await progress.set_message(f"Processing... {(i + 1) * 20}% complete")
    return {
        "data": {
            "job_id": job_id,
            "status": "completed",
            "results": ["result1", "result2", "result3"],
        }
    }


async def _fast_run(arguments, progress=None):
    """Completes instantly."""
    return {"data": {"result": f"Fast: {arguments.get('param', 'default')}"}}


async def _failing_run(arguments, progress=None):
    """Raises ValueError when should_fail is True (default)."""
    if arguments.get("should_fail", True):
        raise ValueError("Simulated tool failure")
    return {"data": {"result": "success"}}


def MOCK_LONG_TOOL():
    return _make_mock_tool(
        "MockLongRunningTool",
        "Mock long-running tool",
        {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
        _long_running_run,
    )

def MOCK_FAST_TOOL():
    return _make_mock_tool(
        "MockFastTool",
        "Mock fast tool",
        {"type": "object", "properties": {"param": {"type": "string"}}, "required": ["param"]},
        _fast_run,
    )

def MOCK_FAILING_TOOL():
    return _make_mock_tool(
        "MockFailingTool",
        "Mock failing tool",
        {"type": "object", "properties": {"should_fail": {"type": "boolean"}}, "required": []},
        _failing_run,
)


@pytest_asyncio.fixture
async def task_manager():
    """TaskManager instance with ToolUniverse and mock tools."""
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    for factory in [MOCK_LONG_TOOL, MOCK_FAST_TOOL, MOCK_FAILING_TOOL]:
        _register_tool(tu, factory())

    manager = TaskManager(tool_universe=tu)
    yield manager

    await manager.stop()
    try:
        tu.close()
    except Exception:
        pass


@pytest.mark.asyncio
async def test_task_creation_returns_immediately(task_manager):
    """Task creation returns immediately with a valid task_id."""
    start_time = time.time()

    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "test123"},
        ttl=60000,
    )

    assert time.time() - start_time < 0.5
    assert task_id is not None
    assert isinstance(task_id, str)
    assert len(task_id) > 0


@pytest.mark.asyncio
async def test_task_status_polling(task_manager):
    """Task status can be polled while running."""
    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "test_status"},
        ttl=60000,
    )

    status = await task_manager.get_status(task_id)
    assert status["taskId"] == task_id
    assert status["status"] in ["working", "completed"]
    assert "statusMessage" in status
    assert "createdAt" in status
    assert "lastUpdatedAt" in status

    await asyncio.sleep(2)

    status2 = await task_manager.get_status(task_id)
    assert status2["taskId"] == task_id
    if status2["status"] == "working":
        assert "Processing" in status2["statusMessage"]


@pytest.mark.asyncio
async def test_task_completion_and_result(task_manager):
    """Task completes and result can be retrieved."""
    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "test_result"},
        ttl=60000,
    )

    result = await task_manager.get_result(task_id)

    assert result is not None
    assert result["data"]["job_id"] == "test_result"
    assert result["data"]["status"] == "completed"
    assert len(result["data"]["results"]) == 3

    status = await task_manager.get_status(task_id)
    assert status["status"] == "completed"


@pytest.mark.asyncio
async def test_task_cancellation(task_manager):
    """Running task can be cancelled."""
    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "test_cancel"},
        ttl=60000,
    )

    await asyncio.sleep(1)

    cancel_result = await task_manager.cancel_task(task_id)
    assert cancel_result["taskId"] == task_id
    assert cancel_result["status"] == "cancelled"

    status = await task_manager.get_status(task_id)
    assert status["status"] == "cancelled"

    with pytest.raises(RuntimeError, match="cancelled"):
        await task_manager.get_result(task_id)


@pytest.mark.asyncio
async def test_progress_reporting(task_manager):
    """Progress messages are updated correctly during execution."""
    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "test_progress"},
        ttl=60000,
    )

    messages_seen = []
    for _ in range(6):
        await asyncio.sleep(1)
        status = await task_manager.get_status(task_id)
        message = status.get("statusMessage", "")
        if message and message not in messages_seen:
            messages_seen.append(message)
        if status["status"] == "completed":
            break

    assert len(messages_seen) >= 3
    assert any("submitted" in msg.lower() for msg in messages_seen)
    assert any("processing" in msg.lower() for msg in messages_seen)


@pytest.mark.asyncio
async def test_task_listing(task_manager):
    """All tasks can be listed."""
    task_ids = []
    for i in range(3):
        task_id = await task_manager.create_task(
            tool_name="MockFastTool",
            arguments={"param": f"test{i}"},
            ttl=60000,
        )
        task_ids.append(task_id)

    await asyncio.sleep(0.5)

    task_list = await task_manager.list_tasks()
    assert "tasks" in task_list
    assert len(task_list["tasks"]) >= 3

    listed_ids = [t["taskId"] for t in task_list["tasks"]]
    for task_id in task_ids:
        assert task_id in listed_ids


@pytest.mark.asyncio
async def test_task_failure_handling(task_manager):
    """Task failures are handled correctly."""
    task_id = await task_manager.create_task(
        tool_name="MockFailingTool",
        arguments={"should_fail": True},
        ttl=60000,
    )

    await asyncio.sleep(0.5)

    status = await task_manager.get_status(task_id)
    assert status["status"] == "failed"

    with pytest.raises(RuntimeError, match="Simulated tool failure"):
        await task_manager.get_result(task_id)


@pytest.mark.asyncio
async def test_task_ttl_cleanup(task_manager):
    """Expired tasks are cleaned up by the cleanup routine."""
    task_id = await task_manager.create_task(
        tool_name="MockFastTool",
        arguments={"param": "ttl_test"},
        ttl=1000,
    )

    result = await task_manager.get_result(task_id)
    assert result is not None

    await asyncio.sleep(2)
    await task_manager._cleanup_expired_tasks()

    with pytest.raises(ValueError, match="Task not found"):
        await task_manager.get_status(task_id)


@pytest.mark.asyncio
async def test_parallel_task_execution(task_manager):
    """Multiple tasks run in parallel, not sequentially."""
    start_time = time.time()

    task_ids = []
    for i in range(3):
        task_id = await task_manager.create_task(
            tool_name="MockLongRunningTool",
            arguments={"job_id": f"parallel_{i}"},
            ttl=60000,
        )
        task_ids.append(task_id)

    results = await asyncio.gather(*[
        task_manager.get_result(task_id) for task_id in task_ids
    ])

    elapsed = time.time() - start_time
    assert elapsed < 8  # ~5s parallel, not 15s sequential
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result["data"]["job_id"] == f"parallel_{i}"


@pytest.mark.asyncio
async def test_task_manager_stop(task_manager):
    """TaskManager can be stopped gracefully, cancelling running tasks."""
    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "stop_test"},
        ttl=60000,
    )

    await asyncio.sleep(1)
    await task_manager.stop()

    status = await task_manager.get_status(task_id)
    assert status["status"] == "cancelled"


@pytest.mark.asyncio
async def test_multiple_progress_updates(task_manager):
    """Multiple progress updates are tracked correctly over time."""
    task_id = await task_manager.create_task(
        tool_name="MockLongRunningTool",
        arguments={"job_id": "multi_progress"},
        ttl=60000,
    )

    messages = []
    for _ in range(10):
        await asyncio.sleep(0.5)
        status = await task_manager.get_status(task_id)
        msg = status.get("statusMessage", "")
        if msg and (not messages or msg != messages[-1]):
            messages.append(msg)
        if status["status"] == "completed":
            break

    assert len(messages) >= 3
    assert any("submitted" in msg.lower() for msg in messages)
    assert any("20%" in msg for msg in messages)
    assert any("40%" in msg for msg in messages)


@pytest.mark.asyncio
async def test_task_status_after_completion(task_manager):
    """Task status remains available after completion; result is idempotent."""
    task_id = await task_manager.create_task(
        tool_name="MockFastTool",
        arguments={"param": "completion_test"},
        ttl=60000,
    )

    result = await task_manager.get_result(task_id)
    assert result is not None

    status = await task_manager.get_status(task_id)
    assert status["taskId"] == task_id
    assert status["status"] == "completed"

    result2 = await task_manager.get_result(task_id)
    assert result2 == result


@pytest.mark.asyncio
async def test_concurrent_task_creation(task_manager):
    """Many tasks can be created concurrently without collisions."""
    create_tasks = [
        task_manager.create_task(
            tool_name="MockFastTool",
            arguments={"param": f"concurrent_{i}"},
            ttl=60000,
        )
        for i in range(10)
    ]

    task_ids = await asyncio.gather(*create_tasks)

    assert len(task_ids) == 10
    assert len(set(task_ids)) == 10

    await asyncio.sleep(0.5)

    statuses = await asyncio.gather(*[
        task_manager.get_status(task_id) for task_id in task_ids
    ])
    for status in statuses:
        assert status["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
