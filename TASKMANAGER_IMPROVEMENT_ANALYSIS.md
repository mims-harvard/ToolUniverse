# TaskManager Improvement Analysis

**Current Status**: ✅ Production Ready (314 lines, all tests passing)
**Last Updated**: 2026-02-09

---

## Current Implementation Assessment

### ✅ What's Working Well

1. **Thread Safety** ✅
   - Proper asyncio.Lock usage
   - No race conditions
   - Lock protection for all shared state

2. **Core Functionality** ✅
   - Task creation, status, result retrieval
   - Cancellation support
   - TTL-based cleanup
   - Progress reporting integration

3. **Code Quality** ✅
   - Clean, simplified structure (314 lines)
   - Helper methods extracted
   - No known bugs
   - Well-tested (13 tests passing)

4. **MCP Protocol Compliance** ✅
   - Follows MCP Tasks specification
   - Correct status dict format
   - Proper error handling

5. **Bug Fixes Applied** ✅
   - Deadlock in cancel_task() - FIXED
   - stop() not marking cancelled - FIXED

---

## Potential Improvements

### Priority 1: High Impact, Low Complexity

#### 1.1 Event-Based Waiting Instead of Polling

**Current Code** (line 258):
```python
async def get_result(self, task_id: str, ...) -> Dict[str, Any]:
    while True:
        async with self.lock:
            task = self._get_task(task_id, auth_context)
            if task.status == "completed":
                return task.result or {}
            # ... check other statuses

        await asyncio.sleep(0.5)  # ❌ Busy-wait polling!
```

**Problem**:
- Polls every 0.5 seconds even when nothing changes
- Wastes CPU cycles
- Not efficient for many concurrent tasks

**Solution**: Use asyncio.Event for efficient waiting

```python
@dataclass
class Task:
    # ... existing fields ...
    _completion_event: asyncio.Event = field(default_factory=asyncio.Event)

async def _execute_task(self, task: Task) -> None:
    try:
        # ... execute tool ...
        async with self.lock:
            task.status = "completed"
            task.result = result
            task._completion_event.set()  # ✅ Wake up waiters!
    except Exception as e:
        async with self.lock:
            task.status = "failed"
            task.error = str(e)
            task._completion_event.set()  # ✅ Wake up waiters!

async def get_result(self, task_id: str, ...) -> Dict[str, Any]:
    """Block until task completes - efficient event-based waiting."""
    task = None
    async with self.lock:
        task = self._get_task(task_id, auth_context)

    # Wait for completion event
    if timeout:
        await asyncio.wait_for(task._completion_event.wait(), timeout=timeout)
    else:
        await task._completion_event.wait()

    # Get final result
    async with self.lock:
        task = self._get_task(task_id, auth_context)
        if task.status == "completed":
            return task.result or {}
        if task.status == "failed":
            raise RuntimeError(task.error or "Task failed")
        if task.status == "cancelled":
            raise RuntimeError("Task was cancelled")
```

**Benefits**:
- ✅ Zero CPU usage while waiting
- ✅ Immediate notification when task completes
- ✅ More efficient for high concurrency

**Complexity**: Low (30 minutes to implement)

---

#### 1.2 Task Limit with Memory Protection

**Current Code**: No limit on tasks
```python
async def create_task(self, ...) -> str:
    task_id = str(uuid.uuid4())
    task = Task(...)
    async with self.lock:
        self.tasks[task_id] = task  # ❌ Unlimited growth!
```

**Problem**:
- Long-running server can accumulate thousands of tasks
- Memory leak risk
- No protection against abuse

**Solution**: Add configurable task limit

```python
class TaskManager:
    def __init__(self, tool_universe=None, max_tasks: int = 1000):
        self.tasks: Dict[str, Task] = {}
        self.max_tasks = max_tasks
        self.lock = asyncio.Lock()
        self.tool_universe = tool_universe
        self._cleanup_task: Optional[asyncio.Task] = None

    async def create_task(self, ...) -> str:
        async with self.lock:
            # Check limit
            if len(self.tasks) >= self.max_tasks:
                # Try to clean up expired tasks first
                await self._cleanup_expired_tasks()

                # If still at limit, remove oldest completed task
                if len(self.tasks) >= self.max_tasks:
                    self._evict_oldest_completed()

            task_id = str(uuid.uuid4())
            task = Task(...)
            self.tasks[task_id] = task

        task._task_handle = asyncio.create_task(self._execute_task(task))
        return task_id

    def _evict_oldest_completed(self) -> None:
        """Remove oldest completed task (LRU eviction)."""
        completed_tasks = [
            (tid, t) for tid, t in self.tasks.items()
            if t.status == "completed"
        ]
        if completed_tasks:
            # Remove oldest
            oldest_id = min(completed_tasks, key=lambda x: x[1].created_at)[0]
            del self.tasks[oldest_id]
            logger.info(f"Evicted oldest completed task {oldest_id}")
```

**Benefits**:
- ✅ Protects against memory leaks
- ✅ Configurable limit
- ✅ Automatic cleanup
- ✅ Production-safe

**Complexity**: Low (1 hour to implement)

---

#### 1.3 Configurable Cleanup Interval

**Current Code** (line 124):
```python
async def _cleanup_loop(self) -> None:
    while True:
        await asyncio.sleep(60)  # ❌ Hardcoded!
        await self._cleanup_expired_tasks()
```

**Problem**:
- 60 seconds might be too slow for some use cases
- Or too fast for others
- Not configurable

**Solution**: Make it configurable

```python
class TaskManager:
    def __init__(
        self,
        tool_universe=None,
        max_tasks: int = 1000,
        cleanup_interval: int = 60  # seconds
    ):
        self.tasks: Dict[str, Task] = {}
        self.max_tasks = max_tasks
        self.cleanup_interval = cleanup_interval
        # ...

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(self.cleanup_interval)  # ✅ Configurable!
            await self._cleanup_expired_tasks()
```

**Benefits**:
- ✅ Flexibility for different use cases
- ✅ Can optimize for high/low frequency

**Complexity**: Trivial (5 minutes)

---

### Priority 2: High Impact, Medium Complexity

#### 2.1 Metrics and Observability

**Current Code**: No metrics

**Problem**:
- Can't track task performance
- No visibility into success/failure rates
- Hard to diagnose issues in production

**Solution**: Add metrics tracking

```python
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class TaskMetrics:
    """Metrics for task execution."""
    total_created: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    total_duration_seconds: float = 0.0
    by_tool: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(dict))

class TaskManager:
    def __init__(self, ...):
        # ... existing fields ...
        self.metrics = TaskMetrics()

    async def create_task(self, ...) -> str:
        # ... existing code ...
        self.metrics.total_created += 1
        if tool_name not in self.metrics.by_tool:
            self.metrics.by_tool[tool_name] = {
                "created": 0, "completed": 0, "failed": 0
            }
        self.metrics.by_tool[tool_name]["created"] += 1
        # ...

    async def _execute_task(self, task: Task) -> None:
        start_time = datetime.now()
        try:
            # ... execute tool ...
            duration = (datetime.now() - start_time).total_seconds()
            async with self.lock:
                # ... update task ...
                self.metrics.total_completed += 1
                self.metrics.total_duration_seconds += duration
                self.metrics.by_tool[task.tool_name]["completed"] += 1
        except Exception as e:
            async with self.lock:
                # ... update task ...
                self.metrics.total_failed += 1
                self.metrics.by_tool[task.tool_name]["failed"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        total_tasks = self.metrics.total_created
        avg_duration = (
            self.metrics.total_duration_seconds / self.metrics.total_completed
            if self.metrics.total_completed > 0
            else 0
        )

        return {
            "total_created": total_tasks,
            "total_completed": self.metrics.total_completed,
            "total_failed": self.metrics.total_failed,
            "total_cancelled": self.metrics.total_cancelled,
            "success_rate": (
                self.metrics.total_completed / total_tasks
                if total_tasks > 0
                else 0
            ),
            "average_duration_seconds": avg_duration,
            "current_active": len([t for t in self.tasks.values() if t.status == "working"]),
            "by_tool": dict(self.metrics.by_tool)
        }
```

**Benefits**:
- ✅ Track performance over time
- ✅ Identify slow tools
- ✅ Monitor success rates
- ✅ Debug production issues

**Complexity**: Medium (2-3 hours)

---

#### 2.2 Batch Operations

**Current Code**: No batch support

**Problem**:
- Creating 10 tasks requires 10 separate calls
- Getting status of 10 tasks requires 10 calls
- Inefficient for parallel workflows

**Solution**: Add batch operations

```python
class TaskManager:
    async def create_batch_tasks(
        self,
        tasks: List[Dict[str, Any]],
        ttl: int = 3600000,
        auth_context: Optional[str] = None,
    ) -> List[str]:
        """
        Create multiple tasks in one call.

        Args:
            tasks: List of {"tool_name": str, "arguments": dict}

        Returns:
            List of task IDs
        """
        task_ids = []

        for task_spec in tasks:
            task_id = await self.create_task(
                tool_name=task_spec["tool_name"],
                arguments=task_spec["arguments"],
                ttl=ttl,
                auth_context=auth_context
            )
            task_ids.append(task_id)

        logger.info(f"Created batch of {len(task_ids)} tasks")
        return task_ids

    async def get_batch_status(
        self,
        task_ids: List[str],
        auth_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get status of multiple tasks in one call."""
        statuses = []

        async with self.lock:
            for task_id in task_ids:
                try:
                    task = self._get_task(task_id, auth_context)
                    statuses.append(self._task_to_status_dict(task))
                except ValueError:
                    statuses.append({
                        "taskId": task_id,
                        "error": "Task not found"
                    })

        return statuses

    async def wait_for_batch(
        self,
        task_ids: List[str],
        timeout: Optional[float] = None,
        auth_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Wait for all tasks to complete and return results."""
        # Wait for all tasks in parallel
        results = await asyncio.gather(
            *[
                self.get_result(task_id, auth_context, timeout)
                for task_id in task_ids
            ],
            return_exceptions=True
        )

        # Process results
        processed = []
        for task_id, result in zip(task_ids, results):
            if isinstance(result, Exception):
                processed.append({
                    "taskId": task_id,
                    "error": str(result)
                })
            else:
                processed.append({
                    "taskId": task_id,
                    "result": result
                })

        return processed
```

**Benefits**:
- ✅ Efficient parallel job submission
- ✅ Single call for multiple statuses
- ✅ Batch wait with timeout
- ✅ Better for workflows

**Complexity**: Medium (3-4 hours)

---

### Priority 3: Medium Impact, High Complexity

#### 3.1 Task Persistence (Optional)

**Problem**:
- Server restart loses all tasks
- Not suitable for critical long-running jobs

**Solution**: Optional SQLite persistence

```python
import sqlite3
import json

class TaskManager:
    def __init__(
        self,
        tool_universe=None,
        max_tasks: int = 1000,
        persist_path: Optional[str] = None  # Path to SQLite DB
    ):
        self.tasks: Dict[str, Task] = {}
        self.persist_path = persist_path
        self.db_conn = None

        if persist_path:
            self._init_persistence()
            self._load_tasks_from_db()
        # ...

    def _init_persistence(self) -> None:
        """Initialize SQLite database."""
        self.db_conn = sqlite3.connect(self.persist_path)
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                tool_name TEXT,
                arguments TEXT,
                status TEXT,
                created_at TEXT,
                ttl INTEGER,
                result TEXT,
                error TEXT
            )
        """)

    async def create_task(self, ...) -> str:
        task_id = await super().create_task(...)

        if self.db_conn:
            # Persist to database
            task = self.tasks[task_id]
            self.db_conn.execute("""
                INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
            """, (
                task_id, task.tool_name,
                json.dumps(task.arguments),
                task.status, task.created_at.isoformat(), task.ttl
            ))
            self.db_conn.commit()

        return task_id
```

**Benefits**:
- ✅ Survive server restarts
- ✅ Audit trail
- ✅ Task history

**Complexity**: High (1-2 days)

---

#### 3.2 Task Priority Queue

**Problem**:
- All tasks execute in order created
- Can't prioritize urgent tasks

**Solution**: Add priority field

```python
@dataclass
class Task:
    # ... existing fields ...
    priority: int = 0  # Higher = more urgent

class TaskManager:
    async def create_task(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        ttl: int = 3600000,
        priority: int = 0,  # New parameter
        auth_context: Optional[str] = None,
    ) -> str:
        task = Task(
            # ... existing fields ...
            priority=priority
        )
        # ...

    async def list_tasks(self, ...) -> Dict[str, Any]:
        async with self.lock:
            tasks_list = [...]
            # Sort by priority first, then creation time
            tasks_list.sort(
                key=lambda t: (-t.priority, t.created_at),
                reverse=False
            )
        # ...
```

**Benefits**:
- ✅ Prioritize urgent tasks
- ✅ Better resource allocation

**Complexity**: Medium-High (4-6 hours)

---

## Recommendations

### For Current Production Use: No Changes Needed ✅

The current TaskManager is **production-ready** for the current use cases:
- ✅ All tests passing
- ✅ No known bugs
- ✅ MCP protocol compliant
- ✅ Thread-safe
- ✅ TTL cleanup working

### If You Want Improvements:

**Immediate (Do Now):**
1. ✅ **Add configurable cleanup interval** (5 minutes)
   - Simple, no risk
   - More flexibility

**Short-term (Next Week):**
2. ✅ **Event-based waiting** (30 minutes)
   - Better CPU efficiency
   - Low risk, high benefit

3. ✅ **Task limit with memory protection** (1 hour)
   - Prevents memory leaks
   - Production safety

**Medium-term (Next Month):**
4. ✅ **Metrics and observability** (2-3 hours)
   - Better monitoring
   - Helps diagnose issues

5. ✅ **Batch operations** (3-4 hours)
   - Useful for parallel workflows
   - Nice to have

**Long-term (Optional):**
6. ⚠️ **Task persistence** (1-2 days)
   - Only if you need it
   - Adds complexity

7. ⚠️ **Priority queue** (4-6 hours)
   - Only if you have prioritization needs
   - Adds complexity

---

## Implementation Priority Matrix

| Improvement | Impact | Complexity | Priority | Time |
|-------------|--------|------------|----------|------|
| Configurable cleanup | Low | Low | P1 | 5 min |
| Event-based waiting | High | Low | P1 | 30 min |
| Task limit | High | Low | P1 | 1 hour |
| Metrics | High | Medium | P2 | 2-3 hours |
| Batch operations | Medium | Medium | P2 | 3-4 hours |
| Task persistence | Low | High | P3 | 1-2 days |
| Priority queue | Low | High | P3 | 4-6 hours |

---

## Proposed Next Steps

### Option A: Keep As-Is (Recommended for now)
- Current implementation is solid
- No blocking issues
- Wait for user feedback before adding complexity

### Option B: Implement P1 Improvements
- 2 hours total work
- Significant efficiency gains
- Low risk

### Option C: Implement P1 + P2 Improvements
- ~7 hours total work
- Full-featured task manager
- Production-grade observability

---

## Summary

**Current Status**: ✅ **Production Ready**

**Critical Issues**: None

**Nice-to-Have Improvements**:
1. Event-based waiting (efficiency)
2. Task limit (safety)
3. Metrics (observability)
4. Batch operations (convenience)

**Recommendation**: Current implementation is solid. Only add improvements if you have specific needs (high concurrency, observability requirements, batch workflows).

---

## Questions to Consider

1. **Do you need high concurrency?** → Implement event-based waiting
2. **Do you run long-lived servers?** → Add task limit
3. **Do you need production monitoring?** → Add metrics
4. **Do you run batch workflows?** → Add batch operations
5. **Do you need task history?** → Add persistence
6. **Do you need priority scheduling?** → Add priority queue

**Answer these to prioritize improvements!**
