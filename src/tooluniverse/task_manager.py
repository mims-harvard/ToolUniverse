"""
Task Manager for MCP Tasks

Implements task state management, background execution, and lifecycle handling
for long-running tool operations following the MCP Tasks protocol.

References:
- MCP Tasks Specification: https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks
"""

import asyncio
import inspect
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, List
from .task_progress import TaskProgress
from .logging_config import get_logger

logger = get_logger(__name__)


TERMINAL_STATUSES = frozenset(["completed", "failed", "cancelled"])


@dataclass
class Task:
    """Represents a long-running task in the MCP Tasks system."""

    task_id: str
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # working, completed, failed, cancelled
    created_at: datetime
    ttl: int  # milliseconds; 0 means no expiry
    status_message: Optional[str] = None
    last_updated_at: datetime = field(default_factory=datetime.now)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[TaskProgress] = None
    auth_context: Optional[str] = None
    _task_handle: Optional[asyncio.Task] = None

    def is_expired(self) -> bool:
        """Check if task has exceeded its TTL."""
        if self.ttl <= 0:
            return False
        elapsed_ms = (datetime.now() - self.created_at).total_seconds() * 1000
        return elapsed_ms > self.ttl

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in TERMINAL_STATUSES


class TaskManager:
    """Manages lifecycle of long-running tasks for the MCP Tasks protocol."""

    def __init__(self, tool_universe=None):
        self.tasks: Dict[str, Task] = {}
        self.lock = asyncio.Lock()
        self.tool_universe = tool_universe
        self._cleanup_task: Optional[asyncio.Task] = None

    # -- Lifecycle --------------------------------------------------------

    async def start(self) -> None:
        """Start the background cleanup loop."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("TaskManager cleanup loop started")

    async def stop(self) -> None:
        """Stop the cleanup loop and cancel all running tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("TaskManager cleanup loop stopped")

        async with self.lock:
            running_tasks = [
                task for task in self.tasks.values()
                if task.status == "working" and task._task_handle
            ]
            for task in running_tasks:
                task.status = "cancelled"
                task.status_message = "Task cancelled by shutdown"
                task.last_updated_at = datetime.now()

        if running_tasks:
            logger.info(f"Cancelling {len(running_tasks)} running tasks")
            for task in running_tasks:
                if task._task_handle and not task._task_handle.done():
                    task._task_handle.cancel()
            await asyncio.sleep(0.1)

    # -- Internal helpers -------------------------------------------------

    def _get_task(self, task_id: str, auth_context: Optional[str] = None) -> Task:
        """
        Look up a task by ID with authorization check.

        Must be called while holding self.lock.

        Raises:
            ValueError: If task not found or auth mismatch (message is
                        intentionally identical to avoid leaking existence).
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if auth_context and task.auth_context != auth_context:
            raise ValueError(f"Task not found: {task_id}")
        return task

    async def _cleanup_loop(self) -> None:
        """Periodically remove expired terminal tasks."""
        while True:
            try:
                await asyncio.sleep(60)
                await self._cleanup_expired_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired_tasks(self) -> None:
        """Remove terminal tasks that have exceeded their TTL."""
        async with self.lock:
            expired_ids = [
                task_id
                for task_id, task in self.tasks.items()
                if task.is_terminal() and task.is_expired()
            ]
            for task_id in expired_ids:
                del self.tasks[task_id]
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired tasks")

    async def _run_tool(self, tool, arguments: Dict[str, Any], progress: TaskProgress):
        """
        Invoke a tool's run method, passing progress if supported.

        Async tools are awaited directly; sync tools run in a thread pool.
        """
        sig = inspect.signature(tool.run)
        kwargs = {"progress": progress} if "progress" in sig.parameters else {}
        is_async = inspect.iscoroutinefunction(tool.run)

        if is_async:
            return await tool.run(arguments, **kwargs)
        return await asyncio.to_thread(tool.run, arguments, **kwargs)

    # -- Public API -------------------------------------------------------

    async def create_task(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        ttl: int = 3600000,
        auth_context: Optional[str] = None,
    ) -> str:
        """Create a new task and start background execution. Returns the task ID."""
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            tool_name=tool_name,
            arguments=arguments,
            status="working",
            status_message=f"Task submitted: {tool_name}",
            created_at=datetime.now(),
            ttl=ttl,
            auth_context=auth_context,
        )
        task.progress = TaskProgress(task, lock=self.lock)

        async with self.lock:
            self.tasks[task_id] = task

        task._task_handle = asyncio.create_task(self._execute_task(task))
        logger.info(f"Created task {task_id} for tool {tool_name}")
        return task_id

    async def _execute_task(self, task: Task) -> None:
        """Execute a task in the background, updating its status on completion or failure."""
        try:
            logger.info(f"Executing task {task.task_id}: {task.tool_name}")

            if not self.tool_universe:
                raise RuntimeError("ToolUniverse not configured")

            tool = self.tool_universe._get_tool_instance(task.tool_name, cache=True)
            if not tool:
                raise ValueError(f"Tool not found: {task.tool_name}")

            result = await self._run_tool(tool, task.arguments, task.progress)

            async with self.lock:
                task.status = "completed"
                task.result = result
                task.status_message = "Task completed successfully"
                task.last_updated_at = datetime.now()
            logger.info(f"Task {task.task_id} completed successfully")

        except asyncio.CancelledError:
            logger.info(f"Task {task.task_id} was cancelled")
            raise

        except Exception as e:
            async with self.lock:
                task.status = "failed"
                task.error = str(e)
                task.status_message = f"Task failed: {e}"
                task.last_updated_at = datetime.now()
            logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)

    async def get_status(
        self, task_id: str, auth_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return the current status of a task as an MCP-compatible dict."""
        async with self.lock:
            task = self._get_task(task_id, auth_context)
            return self._task_to_status_dict(task)

    async def get_result(
        self, task_id: str, auth_context: Optional[str] = None, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Block until the task reaches a terminal state and return its result.

        Raises:
            ValueError: If task not found
            RuntimeError: If task failed or was cancelled
            TimeoutError: If timeout exceeded
        """
        start_time = datetime.now()

        while True:
            async with self.lock:
                task = self._get_task(task_id, auth_context)

                if task.status == "completed":
                    return task.result or {}
                if task.status == "failed":
                    raise RuntimeError(task.error or "Task failed")
                if task.status == "cancelled":
                    raise RuntimeError("Task was cancelled")

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

            await asyncio.sleep(0.5)

    async def list_tasks(
        self, auth_context: Optional[str] = None, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """List tasks, optionally filtered by auth context. Newest first."""
        async with self.lock:
            tasks_list = [
                task for task in self.tasks.values()
                if not auth_context or task.auth_context == auth_context
            ]
            tasks_list.sort(key=lambda t: t.created_at, reverse=True)

            return {
                "tasks": [
                    {
                        "taskId": t.task_id,
                        "status": t.status,
                        "statusMessage": t.status_message,
                        "createdAt": t.created_at.isoformat(),
                        "lastUpdatedAt": t.last_updated_at.isoformat(),
                    }
                    for t in tasks_list
                ]
            }

    def _task_to_status_dict(self, task: Task) -> Dict[str, Any]:
        """Convert a Task to an MCP status dict. Must be called while holding self.lock."""
        return {
            "taskId": task.task_id,
            "status": task.status,
            "statusMessage": task.status_message,
            "createdAt": task.created_at.isoformat(),
            "lastUpdatedAt": task.last_updated_at.isoformat(),
            "ttl": task.ttl,
            "pollInterval": 5000,
        }

    async def cancel_task(
        self, task_id: str, auth_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a running task. Returns the updated task status."""
        async with self.lock:
            task = self._get_task(task_id, auth_context)

            if task.is_terminal():
                raise ValueError(f"Cannot cancel terminal task (status: {task.status})")

            if task._task_handle:
                task._task_handle.cancel()

            task.status = "cancelled"
            task.status_message = "Task cancelled by user"
            task.last_updated_at = datetime.now()
            logger.info(f"Cancelled task {task_id}")

            return self._task_to_status_dict(task)
