"""Unit tests for TaskManager and MCP Tasks functionality."""

import asyncio
import os
import sys

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tooluniverse.task_manager import TaskManager, Task
from tooluniverse.task_progress import TaskProgress


@pytest.fixture
def mock_tool_universe():
    """Create a mock ToolUniverse instance."""
    mock_tu = Mock()

    # Create separate mock tools to avoid shared state issues
    mock_tool1 = Mock()
    mock_tool1.run = AsyncMock(return_value={"data": {"result": "success"}})

    mock_tool2 = Mock()
    mock_tool2.run = AsyncMock(return_value={"data": {"result": "success"}})

    # Use a real dict to avoid "Mock object is not subscriptable" errors
    mock_tu.all_tool_dict = {"TestTool": mock_tool1, "TestTool_Slow": mock_tool2}

    # Mock the _get_tool_instance method that TaskManager uses
    def get_tool_instance(tool_name, cache=True):
        return mock_tu.all_tool_dict.get(tool_name)

    mock_tu._get_tool_instance = get_tool_instance

    return mock_tu


@pytest_asyncio.fixture
async def task_manager_fixture(mock_tool_universe):
    """Async TaskManager fixture for tests that need the real event loop."""
    manager = TaskManager(tool_universe=mock_tool_universe)
    await manager.start()
    yield manager
    await manager.stop()


@pytest_asyncio.fixture
async def task_manager(mock_tool_universe):
    """Default async TaskManager fixture used by most tests."""
    manager = TaskManager(tool_universe=mock_tool_universe)
    await manager.start()
    yield manager
    await manager.stop()


# ============================================================================
# Task Creation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_task_returns_task_id(task_manager):
    """Test that create_task returns a valid task ID."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    assert task_id is not None
    assert isinstance(task_id, str)
    assert len(task_id) > 0

    # Should be a valid UUID format
    parts = task_id.split('-')
    assert len(parts) == 5


@pytest.mark.asyncio
async def test_create_task_stores_in_registry(task_manager):
    """Test that created tasks are stored in the task registry."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Task should be in the registry
    assert task_id in task_manager.tasks

    task = task_manager.tasks[task_id]
    assert task.task_id == task_id
    assert task.tool_name == "TestTool"
    assert task.arguments == {"arg1": "value1"}
    assert task.ttl == 3600000


@pytest.mark.asyncio
async def test_create_task_with_auth_context(task_manager):
    """Test creating a task with authorization context."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000,
        auth_context="user123"
    )

    task = task_manager.tasks[task_id]
    assert task.auth_context == "user123"


@pytest.mark.asyncio
async def test_task_initial_status(task_manager):
    """Test that newly created tasks have 'working' status."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    task = task_manager.tasks[task_id]
    assert task.status == "working"
    assert task.result is None
    assert task.error is None


# ============================================================================
# Status Polling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_status_returns_correct_format(task_manager):
    """Test that get_status returns correct MCP-compliant format."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    status = await task_manager.get_status(task_id)

    assert "taskId" in status
    assert "status" in status
    assert "statusMessage" in status
    assert "createdAt" in status
    assert "lastUpdatedAt" in status
    assert "ttl" in status
    assert "pollInterval" in status

    assert status["taskId"] == task_id
    assert status["status"] == "working"
    assert status["pollInterval"] == 5000


@pytest.mark.asyncio
async def test_get_status_nonexistent_task(task_manager):
    """Test that get_status raises error for non-existent task."""
    with pytest.raises(ValueError, match="Task not found"):
        await task_manager.get_status("nonexistent-task-id")


@pytest.mark.asyncio
async def test_get_status_with_auth_context(task_manager):
    """Test that get_status respects authorization context."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000,
        auth_context="user123"
    )

    # Same auth context - should work
    status = await task_manager.get_status(task_id, auth_context="user123")
    assert status["taskId"] == task_id

    # Different auth context - should fail
    with pytest.raises(ValueError, match="Task not found"):
        await task_manager.get_status(task_id, auth_context="user456")


# ============================================================================
# Result Retrieval Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_result_waits_for_completion(task_manager, mock_tool_universe):
    """Test that get_result blocks until task completes."""
    # Create a slow async tool
    async def slow_tool_run(arguments, progress=None):
        await asyncio.sleep(0.1)
        return {"data": {"result": "slow_success"}}

    # Properly configure the mock to use our async function
    mock_tool = mock_tool_universe.all_tool_dict["TestTool"]
    mock_tool.run = AsyncMock(side_effect=slow_tool_run)

    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Get result should block until completion
    result = await task_manager.get_result(task_id, timeout=5)

    assert result is not None
    assert result["data"]["result"] == "slow_success"


@pytest.mark.asyncio
async def test_get_result_completed_task(task_manager):
    """Test get_result on already completed task."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait for task to complete
    await asyncio.sleep(0.2)

    # Should return result immediately
    result = await task_manager.get_result(task_id)
    assert result["data"]["result"] == "success"


@pytest.mark.asyncio
async def test_get_result_failed_task(task_manager, mock_tool_universe):
    """Test get_result on failed task raises RuntimeError."""
    # Make tool raise exception
    async def failing_tool_run(arguments, progress=None):
        raise ValueError("Tool execution failed")

    mock_tool_universe.all_tool_dict["TestTool"].run = failing_tool_run

    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait for task to fail
    await asyncio.sleep(0.2)

    # Should raise RuntimeError with error message
    with pytest.raises(RuntimeError, match="Tool execution failed"):
        await task_manager.get_result(task_id)


@pytest.mark.asyncio
async def test_get_result_timeout(task_manager, mock_tool_universe):
    """Test get_result timeout."""
    # Create a very slow tool
    async def very_slow_tool_run(arguments, progress=None):
        await asyncio.sleep(10)
        return {"data": {"result": "success"}}

    mock_tool_universe.all_tool_dict["TestTool"].run = very_slow_tool_run

    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Should timeout
    with pytest.raises(TimeoutError, match="did not complete within"):
        await task_manager.get_result(task_id, timeout=0.5)


# ============================================================================
# Task Cancellation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cancel_task(task_manager_fixture, mock_tool_universe):
    """Test cancelling a running task (uses async fixture to avoid event loop issues)."""
    # Create a slow tool that checks for cancellation
    async def slow_tool_run(arguments, progress=None):
        try:
            for i in range(50):  # 5 seconds total
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            raise

    mock_tool_universe.all_tool_dict["TestTool"].run = slow_tool_run

    task_id = await task_manager_fixture.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait a bit for task to start
    await asyncio.sleep(0.2)

    # Cancel the task
    status = await task_manager_fixture.cancel_task(task_id)

    assert status["status"] == "cancelled"

    # Task should be marked as cancelled
    task = task_manager_fixture.tasks[task_id]
    assert task.status == "cancelled"

    # Wait for the cancelled task to finish cleaning up
    if hasattr(task, '_task_handle') and task._task_handle and not task._task_handle.done():
        try:
            await asyncio.wait_for(task._task_handle, timeout=0.5)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


@pytest.mark.asyncio
async def test_cancel_completed_task_fails(task_manager):
    """Test that cancelling a completed task raises error."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait for completion
    await asyncio.sleep(0.2)

    # Try to cancel completed task
    with pytest.raises(ValueError, match="Cannot cancel terminal task"):
        await task_manager.cancel_task(task_id)


@pytest.mark.asyncio
async def test_cancel_with_auth_context(task_manager_fixture, mock_tool_universe):
    """Test cancellation respects authorization context (uses async fixture)."""
    async def slow_tool_run(arguments, progress=None):
        try:
            for i in range(50):
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise

    mock_tool_universe.all_tool_dict["TestTool"].run = slow_tool_run

    task_id = await task_manager_fixture.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000,
        auth_context="user123"
    )

    await asyncio.sleep(0.2)

    # Same auth - should work
    status = await task_manager_fixture.cancel_task(task_id, auth_context="user123")
    assert status["status"] == "cancelled"

    # Wait for cleanup
    task = task_manager_fixture.tasks[task_id]
    if hasattr(task, '_task_handle') and task._task_handle and not task._task_handle.done():
        try:
            await asyncio.wait_for(task._task_handle, timeout=0.5)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass


# ============================================================================
# Task Listing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_list_tasks_returns_all_tasks(task_manager):
    """Test that list_tasks returns all tasks."""
    # Create multiple tasks
    task_id1 = await task_manager.create_task("TestTool", {"arg": "1"}, 3600000)
    task_id2 = await task_manager.create_task("TestTool", {"arg": "2"}, 3600000)
    task_id3 = await task_manager.create_task("TestTool", {"arg": "3"}, 3600000)

    result = await task_manager.list_tasks()

    assert "tasks" in result
    assert len(result["tasks"]) == 3

    task_ids = [t["taskId"] for t in result["tasks"]]
    assert task_id1 in task_ids
    assert task_id2 in task_ids
    assert task_id3 in task_ids


@pytest.mark.asyncio
async def test_list_tasks_filters_by_auth_context(task_manager):
    """Test that list_tasks filters by authorization context."""
    # Create tasks with different auth contexts
    task_id1 = await task_manager.create_task("TestTool", {"arg": "1"}, 3600000, auth_context="user123")
    task_id2 = await task_manager.create_task("TestTool", {"arg": "2"}, 3600000, auth_context="user456")
    task_id3 = await task_manager.create_task("TestTool", {"arg": "3"}, 3600000, auth_context="user123")

    # List tasks for user123
    result = await task_manager.list_tasks(auth_context="user123")

    assert len(result["tasks"]) == 2
    task_ids = [t["taskId"] for t in result["tasks"]]
    assert task_id1 in task_ids
    assert task_id3 in task_ids
    assert task_id2 not in task_ids


@pytest.mark.asyncio
async def test_list_tasks_sorted_by_creation_time(task_manager):
    """Test that list_tasks returns tasks sorted by creation time (newest first)."""
    # Create tasks with small delays
    task_id1 = await task_manager.create_task("TestTool", {"arg": "1"}, 3600000)
    await asyncio.sleep(0.01)
    task_id2 = await task_manager.create_task("TestTool", {"arg": "2"}, 3600000)
    await asyncio.sleep(0.01)
    task_id3 = await task_manager.create_task("TestTool", {"arg": "3"}, 3600000)

    result = await task_manager.list_tasks()

    # Should be sorted newest first
    assert result["tasks"][0]["taskId"] == task_id3
    assert result["tasks"][1]["taskId"] == task_id2
    assert result["tasks"][2]["taskId"] == task_id1


# ============================================================================
# TTL Cleanup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_task_is_expired_after_ttl(task_manager):
    """Test that tasks expire after their TTL."""
    # Create task with very short TTL (100ms)
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=100  # 100 milliseconds
    )

    # Wait for completion
    await asyncio.sleep(0.2)

    task = task_manager.tasks[task_id]

    # Wait for TTL to expire
    await asyncio.sleep(0.2)

    # Task should be marked as expired
    assert task.is_expired() is True


@pytest.mark.asyncio
async def test_cleanup_removes_expired_tasks(task_manager):
    """Test that cleanup removes expired completed tasks."""
    # Create task with very short TTL
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=100
    )

    # Wait for completion and expiry
    await asyncio.sleep(0.3)

    # Task should exist before cleanup
    assert task_id in task_manager.tasks

    # Run cleanup
    await task_manager._cleanup_expired_tasks()

    # Task should be removed after cleanup
    assert task_id not in task_manager.tasks


@pytest.mark.asyncio
async def test_cleanup_preserves_non_expired_tasks(task_manager):
    """Test that cleanup preserves non-expired tasks."""
    # Create task with long TTL
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000  # 1 hour
    )

    # Wait for completion
    await asyncio.sleep(0.2)

    # Run cleanup
    await task_manager._cleanup_expired_tasks()

    # Task should still exist
    assert task_id in task_manager.tasks


# ============================================================================
# Progress Reporting Tests
# ============================================================================

@pytest.mark.asyncio
async def test_progress_updates_status_message(task_manager):
    """Test that progress updates modify task status message."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    task = task_manager.tasks[task_id]
    progress = TaskProgress(task)

    # Update progress
    await progress.set_message("Processing step 1")

    assert task.status_message == "Processing step 1"


@pytest.mark.asyncio
async def test_progress_updates_last_updated_time(task_manager):
    """Test that progress updates modify last_updated_at timestamp."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    task = task_manager.tasks[task_id]
    progress = TaskProgress(task)

    original_time = task.last_updated_at

    await asyncio.sleep(0.1)
    await progress.set_message("Processing")

    assert task.last_updated_at > original_time


@pytest.mark.asyncio
async def test_progress_with_percentage(task_manager):
    """Test progress reporting with percentage."""
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    task = task_manager.tasks[task_id]
    progress = TaskProgress(task)

    # Set progress with percentage
    await progress.set_progress(45, 100, "Processing items")

    assert "45%" in task.status_message
    assert "Processing items" in task.status_message


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_tool_not_found_error(task_manager, mock_tool_universe):
    """Test error handling when tool is not found."""
    # Remove tool from registry
    mock_tool_universe.all_tool_dict = {}

    task_id = await task_manager.create_task(
        tool_name="NonExistentTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait for execution attempt
    await asyncio.sleep(0.2)

    # Task should be marked as failed
    task = task_manager.tasks[task_id]
    assert task.status == "failed"
    assert "not found" in task.error.lower()


@pytest.mark.asyncio
async def test_tool_execution_error(task_manager, mock_tool_universe):
    """Test error handling when tool execution fails."""
    # Make tool raise exception
    async def failing_tool_run(arguments, progress=None):
        raise RuntimeError("Simulated tool failure")

    mock_tool_universe.all_tool_dict["TestTool"].run = failing_tool_run

    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait for execution
    await asyncio.sleep(0.2)

    # Task should be marked as failed
    task = task_manager.tasks[task_id]
    assert task.status == "failed"
    assert "Simulated tool failure" in task.error


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_full_task_lifecycle(task_manager, mock_tool_universe):
    """Test complete task lifecycle from creation to completion."""
    # Create a tool that reports progress
    async def progress_aware_tool(arguments, progress=None):
        if progress:
            await progress.set_message("Starting")
        await asyncio.sleep(0.05)

        if progress:
            await progress.set_message("Processing")
        await asyncio.sleep(0.05)

        if progress:
            await progress.set_message("Finalizing")

        return {"data": {"result": "complete", "value": arguments.get("value")}}

    mock_tool_universe.all_tool_dict["TestTool"].run = progress_aware_tool

    # 1. Create task
    task_id = await task_manager.create_task(
        tool_name="TestTool",
        arguments={"value": "test123"},
        ttl=3600000
    )

    # 2. Check initial status
    status = await task_manager.get_status(task_id)
    assert status["status"] == "working"

    # 3. Wait for completion
    result = await task_manager.get_result(task_id, timeout=5)

    # 4. Verify result
    assert result["data"]["result"] == "complete"
    assert result["data"]["value"] == "test123"

    # 5. Check final status
    final_status = await task_manager.get_status(task_id)
    assert final_status["status"] == "completed"


@pytest.mark.asyncio
async def test_concurrent_tasks(task_manager, mock_tool_universe):
    """Test running multiple tasks concurrently."""
    async def concurrent_tool(arguments, progress=None):
        await asyncio.sleep(0.1)
        return {"data": {"id": arguments.get("id")}}

    mock_tool_universe.all_tool_dict["TestTool"].run = concurrent_tool

    # Create multiple tasks
    task_ids = []
    for i in range(5):
        task_id = await task_manager.create_task(
            tool_name="TestTool",
            arguments={"id": i},
            ttl=3600000
        )
        task_ids.append(task_id)

    # Wait for all to complete
    results = await asyncio.gather(
        *[task_manager.get_result(tid, timeout=5) for tid in task_ids]
    )

    # All should complete successfully
    assert len(results) == 5
    assert all(r["data"]["id"] in range(5) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
