# Architecture Revision Plan: Sync Tools with Async Orchestration

**Date**: 2026-02-09
**Objective**: Revise architecture to support synchronous tools properly while maintaining MCP Tasks benefits
**Status**: Planning

---

## Executive Summary

### Current Problem
- Tools were made async (`async def run()`)
- ToolUniverse core is synchronous
- Result: Python SDK broken, only MCP clients work

### Solution
- **Keep tools synchronous** (blocking operations)
- **MCP layer handles async** via thread pool (`asyncio.to_thread()`)
- **Both Python SDK and MCP work** correctly
- **Clean architectural separation** of concerns

---

## Architecture Overview

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Python SDK (Synchronous)        MCP Clients (Async)       │
│  ├─ tu.run()                     ├─ tasks/call             │
│  ├─ tu.tools.X()                 ├─ tasks/get              │
│  └─ tu.run_batch()               └─ tasks/result           │
│                                                             │
└────────────┬──────────────────────────────┬────────────────┘
             │                              │
             │                              │
┌────────────▼────────────┐    ┌───────────▼────────────────┐
│  ToolUniverse Core      │    │  MCP Server (smcp.py)      │
│  (execute_function.py)  │    │                            │
│  - Synchronous          │    │  ┌──────────────────────┐  │
│  - Direct tool calls    │    │  │  TaskManager         │  │
│  - Caching              │    │  │  - Async coordinator │  │
│  - Hooks                │    │  │  - Thread pool exec  │  │
│  - Validation           │    │  │  - Progress tracking │  │
└────────────┬────────────┘    │  └──────────────────────┘  │
             │                 └───────────┬────────────────┘
             │                             │
             │                             │ asyncio.to_thread()
             │                             │ (non-blocking)
             │                             │
┌────────────▼─────────────────────────────▼────────────────┐
│                     TOOL LAYER                             │
│                   (All Synchronous)                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ProteinsPlusRESTTool      SwissDockSOAPTool              │
│  ├─ def run(args)          ├─ def run(args)               │
│  ├─ time.sleep(10)         ├─ time.sleep(30)              │
│  └─ return result          └─ return result               │
│                                                            │
│  All other tools (sync)                                    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Tools are always synchronous** - Simple, testable, predictable
2. **Orchestration layer handles async** - MCP TaskManager wraps sync tools
3. **Clean separation of concerns** - Each layer has clear responsibility
4. **No breaking changes** - Python SDK continues to work
5. **Performance maintained** - Thread pool provides non-blocking execution

---

## Implementation Plan

### Phase 1: Revert Tools to Synchronous ⏱️ 2 hours

#### Task 1.1: Revert ProteinsPlus Tools (5 tools)

**File**: `src/tooluniverse/proteinsplus_tool.py`

**Changes Required**:

1. **Remove async/await keywords**:
```python
# BEFORE (current - wrong):
async def run(self, arguments: Dict[str, Any], progress=None) -> Dict[str, Any]:
    result = await self._submit_job(...)
    await asyncio.sleep(self.poll_interval)

# AFTER (correct):
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = self._submit_job(...)
    time.sleep(self.poll_interval)
```

2. **Revert httpx back to requests**:
```python
# BEFORE:
async def _submit_job(self, ...):
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=data)

# AFTER:
def _submit_job(self, ...):
    resp = requests.post(url, json=data, timeout=60.0)
```

3. **Remove progress parameter** (handle differently):
```python
# BEFORE:
def run(self, arguments, progress=None):
    if progress:
        await progress.set_message("Processing...")

# AFTER:
def run(self, arguments):
    # No progress in sync tools
    # TaskManager will track progress externally
```

4. **Keep blocking behavior**:
```python
# Polling logic stays blocking (as it was originally)
def _poll_job_status(self, job_id: str, status_url: str):
    start_time = time.time()
    while True:
        if time.time() - start_time > self.max_wait_time:
            return {"error": "Job timeout"}

        response = requests.get(status_url)

        if response.status_code == 200:
            return self._parse_results(response.json())
        elif response.status_code == 202:
            time.sleep(self.poll_interval)  # Blocking sleep
        else:
            return {"error": f"HTTP {response.status_code}"}
```

**Files to modify**:
- `src/tooluniverse/proteinsplus_tool.py`

**Verification**:
```python
# Should work synchronously:
tool = ProteinsPlusRESTTool({...})
result = tool.run({"pdb_id": "2OZR"})  # Blocks, then returns result
assert isinstance(result, dict)
assert "data" in result or "error" in result
```

#### Task 1.2: Revert SwissDock Tools (3 tools)

**File**: `src/tooluniverse/swissdock_tool.py`

**Changes Required**:

Same pattern as ProteinsPlus:
1. Remove `async`/`await`
2. Revert `httpx` to `requests`
3. Remove `progress` parameter
4. Keep blocking behavior

**Specific method signatures**:
```python
# All become synchronous:
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
def _submit_docking(self, ...):
def _check_status(self, session_id: str):
def _retrieve_results(self, session_id: str):
```

**Files to modify**:
- `src/tooluniverse/swissdock_tool.py`

#### Task 1.3: Update Tool Configurations

**Files**:
- `src/tooluniverse/data/proteinsplus_tools.json`
- `src/tooluniverse/data/swissdock_tools.json`

**Changes**:
Keep `execution.taskSupport` but no async-specific fields:

```json
{
  "name": "ProteinsPlus_predict_binding_sites",
  "execution": {
    "taskSupport": "required"
  },
  "description": "Predict binding sites in protein structures. This operation may take 5-15 minutes.",
  "...": "..."
}
```

**No changes needed to**:
- `parameter` schema (stays the same)
- `return_schema` (stays the same)
- Tool descriptions (maybe add timing info)

---

### Phase 2: Update TaskManager for Sync Tools ⏱️ 1.5 hours

#### Task 2.1: Modify _execute_task() Method

**File**: `src/tooluniverse/task_manager.py`

**Current code** (wrong - expects async tools):
```python
async def _execute_task(self, task: Task):
    try:
        tool = self.tool_universe.all_tool_dict.get(task.tool_name)

        # ❌ Assumes tool.run is async:
        result = await tool.run(task.arguments, progress=task.progress)

        async with self.lock:
            task.status = "completed"
            task.result = result
```

**New code** (correct - handles sync tools):
```python
async def _execute_task(self, task: Task):
    try:
        logger.info(f"Executing task {task.task_id}: {task.tool_name}")

        # Get tool instance (not just config)
        tool_instance = self.tool_universe._get_tool_instance(task.tool_name)
        if not tool_instance:
            raise ValueError(f"Tool not found: {task.tool_name}")

        # Update progress: Starting
        async with self.lock:
            task.status_message = f"Starting {task.tool_name}"
            task.last_updated_at = datetime.now()

        # Execute SYNC tool in thread pool (non-blocking for async context)
        # This is the key: asyncio.to_thread() runs sync function in thread pool
        result = await asyncio.to_thread(
            tool_instance.run,
            task.arguments
        )

        # Mark complete
        async with self.lock:
            task.status = "completed"
            task.result = result
            task.status_message = "Task completed successfully"
            task.last_updated_at = datetime.now()

        logger.info(f"Task {task.task_id} completed successfully")

    except asyncio.CancelledError:
        # Task was cancelled
        logger.info(f"Task {task.task_id} was cancelled")
        raise

    except Exception as e:
        # Mark failed
        async with self.lock:
            task.status = "failed"
            task.error = str(e)
            task.status_message = f"Task failed: {str(e)}"
            task.last_updated_at = datetime.now()

        logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)
```

**Key changes**:
- ✅ Use `asyncio.to_thread()` to run sync tool in thread pool
- ✅ Remove `progress` parameter passing (handle externally)
- ✅ Update task status manually in TaskManager
- ✅ Non-blocking for MCP server (thread pool handles concurrency)

#### Task 2.2: Implement Progress Tracking for Sync Tools

**Challenge**: Sync tools can't report progress directly

**Solution**: Timer-based progress estimation

**File**: `src/tooluniverse/task_manager.py`

**Add new method**:
```python
async def _progress_tracker(self, task: Task, estimated_duration: int = 300):
    """
    Track progress for long-running sync tools.

    Args:
        task: Task to track
        estimated_duration: Estimated completion time in seconds (default: 5 min)
    """
    start_time = datetime.now()

    while task.status == "working":
        elapsed = (datetime.now() - start_time).total_seconds()
        progress_pct = min(int((elapsed / estimated_duration) * 100), 95)

        async with self.lock:
            if task.status == "working":  # Double-check still running
                task.status_message = f"Processing ({progress_pct}% estimated)"
                task.last_updated_at = datetime.now()

        await asyncio.sleep(5)  # Update every 5 seconds
```

**Update _execute_task**:
```python
async def _execute_task(self, task: Task):
    try:
        # ... setup code ...

        # Start progress tracker in background
        progress_task = asyncio.create_task(
            self._progress_tracker(task, estimated_duration=900)  # 15 min
        )

        try:
            # Execute tool
            result = await asyncio.to_thread(tool_instance.run, task.arguments)

            # Cancel progress tracker
            progress_task.cancel()

            # Mark complete
            async with self.lock:
                task.status = "completed"
                task.result = result

        finally:
            # Ensure progress tracker is cancelled
            if not progress_task.done():
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

    except asyncio.CancelledError:
        raise
    except Exception as e:
        # ... error handling ...
```

#### Task 2.3: Handle Task Cancellation

**Challenge**: How to cancel a sync tool running in thread pool?

**Solution**: Use threading.Event for cooperative cancellation

**File**: `src/tooluniverse/task_manager.py`

**Add cancellation event to Task**:
```python
@dataclass
class Task:
    task_id: str
    tool_name: str
    arguments: Dict[str, Any]
    status: str
    # ... other fields ...

    # Add cancellation event
    _cancel_event: threading.Event = field(default_factory=threading.Event)

    def request_cancellation(self):
        """Request cancellation of this task."""
        self._cancel_event.set()

    def is_cancellation_requested(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_event.is_set()
```

**Update cancel_task method**:
```python
async def cancel_task(self, task_id: str, auth_context: Optional[str] = None):
    async with self.lock:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Check auth
        if task.auth_context != auth_context:
            raise ValueError(f"Task not found: {task_id}")

        if task.status not in ["working"]:
            raise ValueError("Cannot cancel terminal task")

        # Request cancellation
        task.request_cancellation()
        task.status = "cancelled"
        task.status_message = "Cancellation requested"
        task.last_updated_at = datetime.now()

        # Cancel the task handle
        if hasattr(task, '_task_handle') and task._task_handle:
            task._task_handle.cancel()

        logger.info(f"Cancelled task {task_id}")
        return await self.get_status(task_id, auth_context)
```

**Note**: Full cancellation support requires tools to periodically check cancellation event. This can be added later as an enhancement.

---

### Phase 3: Update MCP Server Integration ⏱️ 30 minutes

#### Task 3.1: Verify SMCP Integration

**File**: `src/tooluniverse/smcp.py`

**Current code** (already correct for new approach):
```python
async def dynamic_tool_function(**kwargs):
    # ... setup ...

    if task_request and task_support != "forbidden":
        # Create task (TaskManager handles execution)
        task_id = await self.task_manager.create_task(
            tool_name=name,
            arguments=tool_arguments,
            ttl=task_request.get("ttl", 3600000),
            auth_context=auth_context
        )
        return json.dumps({"_meta": {"task": {...}}})
    else:
        # Direct execution
        result = self.tooluniverse.run_one_function(
            {"name": name, "arguments": tool_arguments},
            stream_callback=stream_callback,
            use_cache=use_cache
        )
        return json.dumps(result)
```

**Changes needed**: ✅ **NONE** - Already correct!

The MCP server already:
- ✅ Uses TaskManager for task-based execution
- ✅ TaskManager will use `asyncio.to_thread()` (we're updating this)
- ✅ Direct execution goes through ToolUniverse core (stays sync)

#### Task 3.2: Verify TaskManager.create_task()

**File**: `src/tooluniverse/task_manager.py`

**Current code**:
```python
async def create_task(self, tool_name, arguments, ttl, auth_context):
    task_id = str(uuid.uuid4())
    task = Task(...)

    async with self.lock:
        self.tasks[task_id] = task

    # Start execution in background
    task._task_handle = asyncio.create_task(self._execute_task(task))

    return task_id
```

**Changes needed**: ✅ **NONE** - Already correct!

---

### Phase 4: Remove Async Dependencies ⏱️ 30 minutes

#### Task 4.1: Update requirements.txt / pyproject.toml

**File**: `pyproject.toml` (or `requirements.txt`)

**Remove**:
```toml
# No longer needed:
# httpx = "^0.27.0"  # Remove if only used for async tools
```

**Keep**:
```toml
requests = "^2.31.0"  # Continue using
asyncio = "built-in"  # For TaskManager
```

#### Task 4.2: Remove Unused Imports

**Files to check**:
- `src/tooluniverse/proteinsplus_tool.py`
- `src/tooluniverse/swissdock_tool.py`

**Remove**:
```python
import asyncio  # Not needed in tools anymore
import httpx    # Not needed in tools anymore
```

**Keep**:
```python
import requests
import time
```

---

### Phase 5: Testing Strategy ⏱️ 2 hours

#### Task 5.1: Unit Tests for Sync Tools

**File**: `tests/test_proteinsplus_tool.py`

**Update tests**:
```python
# BEFORE (async tests):
@pytest.mark.asyncio
async def test_proteinsplus_predict_binding_sites():
    tool = ProteinsPlusRESTTool({...})
    result = await tool.run({"pdb_id": "2OZR"})

# AFTER (sync tests):
def test_proteinsplus_predict_binding_sites():
    tool = ProteinsPlusRESTTool({...})
    result = tool.run({"pdb_id": "2OZR"})  # Synchronous call
    assert isinstance(result, dict)
```

#### Task 5.2: Python SDK Integration Tests

**Create**: `tests/integration/test_python_sdk.py`

```python
def test_python_sdk_direct_call():
    """Test that Python SDK can call tools directly."""
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools()

    # Direct function call (should work now)
    result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

    assert isinstance(result, dict)
    assert "data" in result or "error" in result
    # Should NOT be a coroutine
    assert not inspect.iscoroutine(result)

def test_python_sdk_run_method():
    """Test that tu.run() works."""
    tu = ToolUniverse()
    tu.load_tools()

    result = tu.run({
        "name": "ProteinsPlus_predict_binding_sites",
        "arguments": {"pdb_id": "2OZR"}
    })

    assert isinstance(result, dict)
    assert not inspect.iscoroutine(result)

def test_python_sdk_batch():
    """Test that batch execution works."""
    tu = ToolUniverse()
    tu.load_tools()

    results = tu.run_batch([
        {"name": "ProteinsPlus_predict_binding_sites",
         "arguments": {"pdb_id": "2OZR"}},
        {"name": "UniProt_get_entry_by_accession",
         "arguments": {"accession": "P05067"}}
    ])

    assert len(results) == 2
    for result in results:
        assert not inspect.iscoroutine(result)
```

#### Task 5.3: MCP Tasks Integration Tests

**Update**: `tests/test_task_manager.py`

```python
@pytest_asyncio.fixture
async def task_manager_fixture(mock_tool_universe):
    """Create a TaskManager with sync tools."""
    # Mock sync tool
    mock_tool = Mock()

    def sync_run(arguments):
        time.sleep(0.1)  # Simulate work
        return {"data": {"result": "success"}}

    mock_tool.run = sync_run  # Sync function
    mock_tool_universe.all_tool_dict = {"TestTool": mock_tool}
    mock_tool_universe._get_tool_instance = lambda name: mock_tool

    manager = TaskManager(tool_universe=mock_tool_universe)
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_task_manager_executes_sync_tool(task_manager_fixture):
    """Test that TaskManager can execute sync tools."""
    task_id = await task_manager_fixture.create_task(
        tool_name="TestTool",
        arguments={"arg1": "value1"},
        ttl=3600000
    )

    # Wait for completion
    result = await task_manager_fixture.get_result(task_id, timeout=5)

    assert result["data"]["result"] == "success"
```

#### Task 5.4: End-to-End Test

**Create**: `tests/e2e/test_mcp_with_sync_tools.py`

```python
@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("RUN_E2E_TESTS"), reason="E2E tests require API keys")
async def test_proteinsplus_via_mcp_tasks():
    """Test ProteinsPlus tool via MCP Tasks (sync tool, async orchestration)."""
    from tooluniverse import ToolUniverse, SMCP

    tu = ToolUniverse()
    tu.load_tools()

    smcp = SMCP(tool_universe=tu)
    await smcp.task_manager.start()

    try:
        # Create task
        task_id = await smcp.task_manager.create_task(
            tool_name="ProteinsPlus_predict_binding_sites",
            arguments={"pdb_id": "2OZR"},
            ttl=3600000
        )

        # Should return immediately
        assert task_id is not None

        # Poll for completion (may take 5-15 minutes)
        timeout = time.time() + 1800  # 30 minute timeout
        while time.time() < timeout:
            status = await smcp.task_manager.get_status(task_id)
            if status["status"] == "completed":
                break
            elif status["status"] == "failed":
                pytest.fail(f"Task failed: {status}")
            await asyncio.sleep(5)

        # Get result
        result = await smcp.task_manager.get_result(task_id)
        assert "data" in result
        assert "pockets" in result["data"]

    finally:
        await smcp.task_manager.stop()
```

---

### Phase 6: Documentation Updates ⏱️ 1 hour

#### Task 6.1: Update Architecture Documentation

**File**: `MCP_TASKS_ARCHITECTURE.md`

**Add section**:
```markdown
## Tool Synchronicity

### Design Decision: Sync Tools, Async Orchestration

ToolUniverse uses **synchronous tools** with **asynchronous orchestration**:

#### Tools Are Synchronous
- All tool implementations use `def run()` (not `async def`)
- Tools can use blocking operations (`time.sleep()`, `requests.get()`)
- Tools are simple, testable, and work in any context
- No event loop required

#### MCP Layer Is Asynchronous
- TaskManager uses `asyncio.to_thread()` to run sync tools
- Tools execute in thread pool (non-blocking for async context)
- MCP clients get non-blocking execution
- Progress tracking handled by TaskManager

#### Benefits
- ✅ Python SDK works directly: `tu.tools.X()` calls tool synchronously
- ✅ MCP clients work: TaskManager runs tool in thread pool
- ✅ No breaking changes
- ✅ Clean architecture
- ✅ Simple tool development

### Example

```python
# Tool implementation (sync):
class ProteinsPlusRESTTool:
    def run(self, arguments):
        # Blocking operation
        result = requests.post(...)
        while not_complete:
            time.sleep(10)  # Blocks thread (OK!)
        return result

# Python SDK usage (sync):
tu = ToolUniverse()
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
# Works! Returns result after blocking

# MCP usage (async):
task_id = await task_manager.create_task(
    tool_name="ProteinsPlus_predict_binding_sites",
    arguments={"pdb_id": "2OZR"}
)
# Returns immediately! Tool runs in thread pool
```
```

#### Task 6.2: Update Tool Creation Guide

**File**: `GUIDE_CREATING_ASYNC_TOOLS.md` → Rename to `GUIDE_CREATING_LONG_RUNNING_TOOLS.md`

**Update content**:
```markdown
# Guide: Creating Long-Running Tools for ToolUniverse

## Tool Design Philosophy

All tools in ToolUniverse are **synchronous**. Even long-running operations use blocking code. The MCP layer handles async orchestration via thread pools.

## Creating a Long-Running Tool

### Step 1: Implement Synchronous Run Method

```python
class MyLongRunningTool(BaseTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Submit job
        job_id = self._submit_job(arguments)

        # Poll for completion (blocking)
        while True:
            status = self._check_status(job_id)
            if status == "completed":
                return self._get_results(job_id)
            elif status == "failed":
                return {"error": "Job failed"}

            time.sleep(10)  # Blocking sleep is OK!
```

### Step 2: Configure Tool for MCP Tasks

In your JSON config:
```json
{
  "name": "MyLongRunningTool_process_data",
  "execution": {
    "taskSupport": "required"
  }
}
```

### Step 3: Test Both Contexts

```python
# Test synchronous (Python SDK)
tool = MyLongRunningTool({...})
result = tool.run({"input": "data"})  # Blocks until complete

# Test asynchronous (MCP)
task_id = await task_manager.create_task(
    tool_name="MyLongRunningTool_process_data",
    arguments={"input": "data"}
)
# Returns immediately, tool runs in background
```

## Why Not Async Tools?

**Q**: Why not make the tool async?

**A**: Synchronous tools are:
- ✅ Simpler to implement
- ✅ Work in both Python SDK and MCP contexts
- ✅ No event loop complications
- ✅ Easier to test
- ✅ MCP layer handles non-blocking via thread pool

## Performance Considerations

**Q**: Isn't threading less efficient than native async?

**A**: For I/O-bound operations (API calls, database queries):
- Thread pool efficiency: ~95% of native async
- Simplicity gain: Massive
- Maintainability: Much better

For CPU-bound operations:
- Use ProcessPoolExecutor (future enhancement)
- Or offload to external service

## Best Practices

1. **Keep tools synchronous** - Don't use `async def`
2. **Use blocking operations** - `time.sleep()`, `requests.get()` are fine
3. **Set taskSupport** - Mark long-running tools with `"taskSupport": "required"`
4. **Provide timing info** - Document expected completion time in description
5. **Handle errors** - Return `{"error": "..."}` for failures
```

#### Task 6.3: Update Implementation Complete Document

**File**: `IMPLEMENTATION_COMPLETE.md`

**Add section**:
```markdown
## Architecture Update (2026-02-09)

### Revised Approach: Sync Tools + Async Orchestration

After identifying a critical architectural issue, the implementation was revised to:

**Original (Wrong)**:
- ❌ Made tools async (`async def run()`)
- ❌ Broke Python SDK (returned coroutines)
- ✅ MCP worked (properly awaited)

**Revised (Correct)**:
- ✅ Tools remain synchronous (`def run()`)
- ✅ Python SDK works (`tu.run()` calls tools directly)
- ✅ MCP works (`asyncio.to_thread()` for non-blocking)
- ✅ Clean architecture
- ✅ Zero breaking changes

### Key Insight

**"Keep tools synchronous, make orchestration async."**

This architectural principle ensures:
- Tools work in any context (SDK, MCP, HTTP API)
- Simple tool development (no async complexity)
- MCP benefits maintained (thread pool provides non-blocking)
- No breaking changes to existing code
```

---

### Phase 7: Validation & Verification ⏱️ 1 hour

#### Task 7.1: Manual Testing Checklist

**Python SDK Tests**:
```bash
# Test 1: Direct tool call
python -c "
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
result = tu.tools.UniProt_get_entry_by_accession(accession='P05067')
print(f'Type: {type(result)}')
print(f'Has data: {"data" in result if isinstance(result, dict) else False}')
"

# Test 2: Run method
python -c "
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
result = tu.run({'name': 'UniProt_get_entry_by_accession', 'arguments': {'accession': 'P05067'}})
print(f'Type: {type(result)}')
"

# Test 3: Long-running tool (ProteinsPlus)
# Note: This will block for 5-15 minutes - that's expected!
python -c "
from tooluniverse import ToolUniverse
import time
tu = ToolUniverse()
tu.load_tools()
print('Starting ProteinsPlus job (will block 5-15 min)...')
start = time.time()
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id='2OZR')
elapsed = time.time() - start
print(f'Completed in {elapsed:.1f} seconds')
print(f'Result type: {type(result)}')
print(f'Has data: {"data" in result if isinstance(result, dict) else False}')
"
```

**MCP Tests**:
```bash
# Test 1: Start MCP server
python -c "
from tooluniverse import create_smcp_server
server = create_smcp_server()
print('MCP server started successfully')
"

# Test 2: Task creation (requires MCP client)
# Use Claude Code or test client to verify task creation works

# Test 3: Progress tracking
# Create task, verify status updates appear
```

#### Task 7.2: Automated Test Suite

```bash
# Run all unit tests
pytest tests/ -v

# Run integration tests
pytest tests/integration/ -v

# Run E2E tests (requires API keys)
RUN_E2E_TESTS=1 pytest tests/e2e/ -v

# Check coverage
pytest tests/ --cov=src/tooluniverse --cov-report=html
```

#### Task 7.3: Performance Validation

**Measure overhead of `asyncio.to_thread()`**:

```python
import asyncio
import time

def sync_tool(duration):
    time.sleep(duration)
    return {"result": "done"}

async def test_overhead():
    # Direct sync call
    start = time.time()
    result = sync_tool(1.0)
    sync_time = time.time() - start

    # Via asyncio.to_thread()
    start = time.time()
    result = await asyncio.to_thread(sync_tool, 1.0)
    async_time = time.time() - start

    overhead = async_time - sync_time
    print(f"Sync time: {sync_time:.4f}s")
    print(f"Async time: {async_time:.4f}s")
    print(f"Overhead: {overhead*1000:.2f}ms ({overhead/sync_time*100:.1f}%)")

asyncio.run(test_overhead())
# Expected: <1ms overhead (<0.1%)
```

---

## Migration Checklist

### Pre-Migration
- [ ] Review current code state
- [ ] Backup current implementation
- [ ] Create feature branch: `fix/sync-tools-architecture`
- [ ] Document current behavior

### Implementation
- [ ] **Phase 1**: Revert tools to sync (2h)
  - [ ] ProteinsPlus tool (5 tools)
  - [ ] SwissDock tool (3 tools)
  - [ ] Update tool configs
- [ ] **Phase 2**: Update TaskManager (1.5h)
  - [ ] Modify _execute_task()
  - [ ] Add progress tracking
  - [ ] Handle cancellation
- [ ] **Phase 3**: Verify MCP integration (30m)
  - [ ] Check SMCP code
  - [ ] Verify TaskManager.create_task()
- [ ] **Phase 4**: Remove async deps (30m)
  - [ ] Update requirements
  - [ ] Remove unused imports
- [ ] **Phase 5**: Testing (2h)
  - [ ] Unit tests
  - [ ] Integration tests
  - [ ] E2E tests
- [ ] **Phase 6**: Documentation (1h)
  - [ ] Update architecture docs
  - [ ] Update tool creation guide
  - [ ] Update implementation docs
- [ ] **Phase 7**: Validation (1h)
  - [ ] Manual testing
  - [ ] Automated tests
  - [ ] Performance validation

### Post-Migration
- [ ] Verify Python SDK works
- [ ] Verify MCP clients work
- [ ] Update IMPLEMENTATION_COMPLETE.md
- [ ] Create PR
- [ ] Code review
- [ ] Merge to main
- [ ] Tag release
- [ ] Update documentation site

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Revert tools | 2 hours | None |
| Phase 2: TaskManager | 1.5 hours | Phase 1 |
| Phase 3: MCP verify | 30 minutes | Phase 2 |
| Phase 4: Remove deps | 30 minutes | Phase 1 |
| Phase 5: Testing | 2 hours | Phase 1-4 |
| Phase 6: Documentation | 1 hour | Phase 1-5 |
| Phase 7: Validation | 1 hour | Phase 1-6 |
| **Total** | **8.5 hours** | - |

**Estimated completion**: 1-2 days (with breaks/reviews)

---

## Success Criteria

### Functional Requirements
- ✅ Python SDK can call all tools directly
- ✅ MCP clients can create tasks for all tools
- ✅ Tasks execute non-blocking in MCP context
- ✅ Progress tracking works for long-running tasks
- ✅ Task cancellation works
- ✅ Error handling works in both contexts

### Non-Functional Requirements
- ✅ Zero breaking changes to existing code
- ✅ Performance overhead < 1% for most operations
- ✅ All existing tests pass
- ✅ Documentation is accurate and complete
- ✅ Code is clean and maintainable

### Quality Gates
- ✅ 100% of unit tests pass
- ✅ 100% of integration tests pass
- ✅ Manual testing checklist complete
- ✅ Code review approved
- ✅ Documentation reviewed

---

## Risk Assessment

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Tools don't revert cleanly | Low | Medium | Comprehensive testing |
| asyncio.to_thread() issues | Low | High | Performance validation |
| Progress tracking complexity | Medium | Low | Simple estimation |
| Cancellation doesn't work | Medium | Low | Document limitation |
| Performance degradation | Low | Medium | Benchmark before/after |

### Rollback Plan

If critical issues found:
1. Revert commits on feature branch
2. Return to previous implementation
3. Re-analyze architectural approach
4. Consider alternative solutions

---

## Communication Plan

### Stakeholders
- ToolUniverse maintainers
- Python SDK users
- MCP client developers
- Documentation team

### Updates
- **Pre-migration**: Announce architectural change
- **During**: Daily status updates
- **Post-migration**: Release notes with migration guide

---

## Appendix: Technical Deep Dives

### A. asyncio.to_thread() Internals

```python
# How asyncio.to_thread() works:
async def to_thread(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    # Submit to thread pool executor
    return await loop.run_in_executor(None, func, *args, **kwargs)

# Why it's safe:
# 1. Doesn't block the event loop
# 2. Uses default ThreadPoolExecutor (max workers = CPU count * 5)
# 3. Exceptions propagate correctly
# 4. Cancellable (cancels future, but thread may continue)
```

### B. Thread Pool Sizing

Default ThreadPoolExecutor sizing:
```python
import os
max_workers = min(32, (os.cpu_count() or 1) + 4)

# Example on 8-core machine:
# max_workers = min(32, 8 + 4) = 12 threads
```

For ToolUniverse:
- Most operations are I/O-bound (waiting on external APIs)
- 12 concurrent long-running operations is reasonable
- Can be tuned via environment variable if needed

### C. Progress Estimation Algorithm

```python
def estimate_progress(elapsed_seconds, estimated_total):
    # Linear estimation up to 95%
    progress = min((elapsed_seconds / estimated_total) * 100, 95)

    # Last 5% reserved for "almost done" state
    # Never shows 100% until actually complete

    return int(progress)

# Example timeline for 15-minute job:
# 0 min: 0%
# 3 min: 20%
# 7 min: 47%
# 14 min: 93%
# 15 min: 95% (stays here until complete)
# Complete: 100%
```

---

**Status**: Ready for implementation
**Approval**: Pending
**Next Step**: Begin Phase 1 (Revert tools to sync)

