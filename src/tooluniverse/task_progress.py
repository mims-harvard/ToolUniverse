"""
Task Progress Reporting for MCP Tasks

Provides thread-safe progress reporting for long-running tool operations
following the MCP Tasks protocol.
"""

import asyncio
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .task_manager import Task


class TaskProgress:
    """
    Progress reporter for MCP Tasks.

    Usage:
        async def run(arguments, progress: Optional[TaskProgress] = None):
            if progress:
                await progress.set_message("Starting analysis...")
                await progress.set_progress(45, 100, "Processing results")
    """

    def __init__(self, task: "Task", lock: Optional[asyncio.Lock] = None):
        self.task = task
        self.lock = lock

    async def _update_task(self, message: str) -> None:
        """Apply a status message update to the task, using the lock if available."""
        self.task.status_message = message
        self.task.last_updated_at = datetime.now()

    async def set_message(self, message: str) -> None:
        """Update task status message (thread-safe when lock is provided)."""
        if self.lock:
            async with self.lock:
                await self._update_task(message)
        else:
            await self._update_task(message)

    async def set_progress(self, current: int, total: int, message: Optional[str] = None) -> None:
        """Update progress with numeric values (e.g., 45 of 100)."""
        percentage = int((current / total) * 100) if total > 0 else 0
        full_message = f"{message} ({percentage}%)" if message else f"{percentage}% complete"
        await self.set_message(full_message)
