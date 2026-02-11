# CRITICAL: Async Tool Architecture Issue

## Date: 2026-02-09
## Severity: 🔴 **BLOCKING** - Breaks Python SDK

---

## Problem Discovery

The user identified a **fundamental architectural flaw** in the async tool implementation:

> "This async is only supported by mcp now, what would happen if the call on tooluniverse.run or use the python api under the tools folder?"

## The Critical Issue

### What I Did (WRONG ❌)

1. **Made tools async**: Converted `run()` methods to `async def run()`
2. **Only fixed MCP layer**: Updated `smcp.py` to handle async execution
3. **Ignored Python SDK**: Forgot that ToolUniverse core is synchronous!

### The Actual Code Flow

**File**: `src/tooluniverse/execute_function.py:2434`

```python
def _execute_tool_with_stream(self, tool_instance, arguments, ...):
    # ... inspection logic ...

    # ❌ SYNCHRONOUS CALL to potentially ASYNC function!
    return tool_instance.run(tool_arguments, **kwargs), tool_arguments
```

**File**: `src/tooluniverse/proteinsplus_tool.py:XX`

```python
# ❌ Now returns a coroutine, not a result!
async def run(self, arguments, progress=None):
    result = await self._submit_job(...)
    return result
```

## What Breaks

### Python SDK Usage (BROKEN 💥)

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# ❌ THIS WILL FAIL!
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Error:
# RuntimeError: coroutine 'ProteinsPlusRESTTool.run' was never awaited
```

### Direct run() calls (BROKEN 💥)

```python
result = tu.run({
    "name": "ProteinsPlus_predict_binding_sites",
    "arguments": {"pdb_id": "2OZR"}
})

# ❌ Returns: <coroutine object ProteinsPlusRESTTool.run at 0x...>
# ❌ Not the actual result!
```

### run_batch() (BROKEN 💥)

```python
results = tu.run_batch([...])  # ❌ All results are coroutine objects!
```

### Only MCP Works (✅)

```python
# ✅ MCP server works because smcp.py properly awaits:
async def dynamic_tool_function(...):
    result = await tool.run(arguments, progress=progress)
    return result
```

---

## Architectural Root Cause

### Layer Mismatch

```
┌─────────────────────────────────────────┐
│  User APIs                              │
│  - tu.run() ................. SYNC ❌   │
│  - tu.tools.X() ............. SYNC ❌   │
│  - tu.run_batch() ........... SYNC ❌   │
└─────────────┬───────────────────────────┘
              │
              ├─ MCP Server Layer (smcp.py)
              │  - ASYNC ✅ (works correctly)
              │
              ├─ Python SDK Layer (execute_function.py)
              │  - SYNC ❌ (broken!)
              │
┌─────────────▼───────────────────────────┐
│  ToolUniverse Core                      │
│  - _execute_tool_with_stream() .. SYNC ❌│
│  - run_one_function() ........... SYNC ❌│
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  Tool Implementations                   │
│  - ProteinsPlus ............... ASYNC ❌ │  ← MISMATCH!
│  - SwissDock .................. ASYNC ❌ │  ← MISMATCH!
│  - Other tools ................ SYNC ✅  │
└─────────────────────────────────────────┘
```

### The Problem

**ToolUniverse core is synchronous, but I made tools async!**

- Core calls: `tool_instance.run(arguments)` (synchronous call)
- Tool returns: `<coroutine object>` (async function)
- Result: **Broken!**

---

## Impact Assessment

### Production Systems

| Component | Status | Impact |
|-----------|--------|--------|
| MCP Clients (Claude Code, Desktop) | ✅ Works | Zero impact |
| Python SDK (`tu.run()`) | ❌ **BROKEN** | **Cannot use async tools** |
| Python SDK (`tu.tools.X()`) | ❌ **BROKEN** | **Cannot use async tools** |
| HTTP API Server | ❓ **Unknown** | Likely broken |
| Batch execution | ❌ **BROKEN** | Returns coroutines |
| Hooks/caching | ❌ **BROKEN** | Can't cache coroutines |

### Tools Affected

- ✅ All synchronous tools: **Still work**
- ❌ ProteinsPlus (5 tools): **BROKEN in Python SDK**
- ❌ SwissDock (3 tools): **BROKEN in Python SDK**

### Severity

🔴 **CRITICAL**: This is a **breaking change** that prevents Python SDK users from using 8 tools!

---

## Solution Options

### Option 1: ❌ Keep Tools Async, Make Core Async-Aware (Breaking)

**Approach**: Update ToolUniverse core to detect and handle async tools

```python
def _execute_tool_with_stream(self, tool_instance, arguments, ...):
    if inspect.iscoroutinefunction(tool_instance.run):
        # Async tool - need to run it in event loop
        result = asyncio.run(tool_instance.run(tool_arguments, **kwargs))
    else:
        # Sync tool - run normally
        result = tool_instance.run(tool_arguments, **kwargs)

    return result, tool_arguments
```

**Problems**:
- ❌ `asyncio.run()` creates new event loop (can't be called from existing async context)
- ❌ Breaks if user is already in async context
- ❌ Can't use `await` because `_execute_tool_with_stream()` itself is sync
- ❌ Complex edge cases and race conditions

### Option 2: ✅ REVERT Tools to Sync, Handle Async in MCP Layer (RECOMMENDED)

**Approach**: Keep tools synchronous (blocking), let MCP layer handle async via thread pool

**Tools remain sync**:
```python
# proteinsplus_tool.py - REVERT TO SYNC
def run(self, arguments):
    result = self._submit_job(...)
    job_id = self._extract_job_id(result)

    # Blocking poll (as before)
    while True:
        response = requests.get(status_url)
        if response.status_code == 200:
            return self._parse_results(response.json())
        time.sleep(self.poll_interval)  # Blocking
```

**MCP layer handles async**:
```python
# smcp.py - ALREADY ASYNC
async def execute_tool_in_task(tool, arguments, progress):
    # Run blocking tool in thread pool (non-blocking for async context)
    result = await asyncio.to_thread(tool.run, arguments)
    return result
```

**Benefits**:
- ✅ **Zero breaking changes** for Python SDK
- ✅ `tu.run()` works exactly as before
- ✅ `tu.tools.X()` works exactly as before
- ✅ MCP still gets non-blocking execution (via thread pool)
- ✅ No event loop conflicts
- ✅ Clean separation of concerns

**Tradeoffs**:
- ⚠️ Tools use thread pool instead of native async (slightly less efficient)
- ⚠️ Each long-running tool blocks a thread (but MCP TaskManager manages this)

### Option 3: ❌ Dual API (Sync + Async) (Complex)

**Approach**: Maintain both sync and async versions

```python
class ToolUniverse:
    def run(self, tool_call):
        # Sync API - for backwards compatibility
        ...

    async def arun(self, tool_call):
        # Async API - for async contexts
        ...
```

**Problems**:
- ❌ Doubles API surface
- ❌ Users must choose correct API
- ❌ Still doesn't solve coroutine issue in sync API
- ❌ Maintenance burden

---

## Recommended Solution

### ✅ **Option 2: Revert Tools to Sync**

**Rationale**:
1. **Backwards compatibility**: Python SDK continues to work unchanged
2. **MCP benefits preserved**: TaskManager + thread pool = non-blocking execution
3. **Simplicity**: Clean layer separation
4. **No breaking changes**: Zero impact on existing users
5. **Production ready**: No architectural risks

### Implementation Plan

#### Step 1: Revert Tool Implementations

**Files to revert**:
1. `src/tooluniverse/proteinsplus_tool.py` - Change `async def run()` back to `def run()`
2. `src/tooluniverse/swissdock_tool.py` - Change `async def run()` back to `def run()`

**Changes**:
- Remove `async`/`await` keywords
- Change `httpx.AsyncClient` back to `requests`
- Change `await asyncio.sleep()` back to `time.sleep()`
- Keep progress reporting (but make it sync-safe)

#### Step 2: Update TaskManager Execution

**File**: `src/tooluniverse/task_manager.py:_execute_task()`

```python
async def _execute_task(self, task: Task):
    try:
        # Get tool
        tool = self.tool_universe.all_tool_dict.get(task.tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {task.tool_name}")

        # Execute SYNC tool in thread pool (non-blocking for async context)
        result = await asyncio.to_thread(
            tool.run,
            task.arguments,
            # Can't pass TaskProgress to sync tool directly
            # Need to handle progress differently
        )

        # Mark complete
        async with self.lock:
            task.status = "completed"
            task.result = result
            task.last_updated_at = datetime.now()

    except asyncio.CancelledError:
        logger.info(f"Task {task.task_id} was cancelled")
        raise
    except Exception as e:
        async with self.lock:
            task.status = "failed"
            task.error = str(e)
            task.last_updated_at = datetime.now()
```

#### Step 3: Handle Progress Reporting

**Challenge**: Sync tools can't call `await progress.set_message()`

**Solution**: Make TaskProgress thread-safe with callback pattern

```python
class TaskProgress:
    def __init__(self, task: Task):
        self.task = task
        self._loop = asyncio.get_event_loop()

    def set_message(self, message: str):
        """Sync method that schedules async update"""
        self.task.status_message = message
        self.task.last_updated_at = datetime.now()
        # Don't await - just update task in-place
```

Or simpler: Don't pass progress to sync tools, handle at TaskManager level.

#### Step 4: Update Tool Configurations

Keep `execution.taskSupport` but remove async-specific configs:
```json
{
  "name": "ProteinsPlus_predict_binding_sites",
  "execution": {
    "taskSupport": "required"
  }
}
```

---

## Alternative: If We Must Keep Async Tools

### Option 2B: Async-Aware Core (More Complex)

If there's a strong reason to keep tools async, update ToolUniverse core:

```python
# execute_function.py
def _execute_tool_with_stream(self, tool_instance, arguments, ...):
    if inspect.iscoroutinefunction(tool_instance.run):
        # Async tool - check if we're in async context
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - can't use asyncio.run()
            raise RuntimeError(
                f"Tool '{tool_instance.name}' is async and requires MCP Task execution. "
                "Use MCP client or call via HTTP API."
            )
        except RuntimeError:
            # Not in async context - safe to use asyncio.run()
            result = asyncio.run(tool_instance.run(tool_arguments, **kwargs))
            return result, tool_arguments
    else:
        # Sync tool - run normally
        return tool_instance.run(tool_arguments, **kwargs), tool_arguments
```

**Problems**:
- Still breaks Python SDK for async tools (error message instead of result)
- User experience: "Why can't I use this tool directly?"
- Fragmentation: Some tools work in SDK, some require MCP

---

## Decision Matrix

| Criterion | Option 1: Keep Async | Option 2: Revert to Sync | Option 3: Dual API |
|-----------|---------------------|--------------------------|-------------------|
| Python SDK Compatibility | ❌ Broken | ✅ Works | ⚠️ Complex |
| MCP Non-Blocking | ✅ Native | ✅ Thread pool | ✅ Native |
| Breaking Changes | 🔴 YES | ✅ NO | ⚠️ Partial |
| Maintenance | ⚠️ Medium | ✅ Simple | ❌ High |
| User Experience | ❌ Confusing | ✅ Consistent | ⚠️ Dual APIs |
| Event Loop Issues | ❌ Many | ✅ None | ⚠️ Some |
| **RECOMMENDATION** | ❌ | ✅ **BEST** | ❌ |

---

## Conclusion

### ✅ Recommended Action: **REVERT TO SYNC TOOLS**

**Why**:
1. Preserves backwards compatibility (Python SDK works)
2. MCP still gets non-blocking benefits (via `asyncio.to_thread()`)
3. Clean architecture (sync tools, async orchestration)
4. No breaking changes
5. Production ready

### Implementation Effort

- **Revert tool code**: ~1-2 hours
- **Update TaskManager**: ~30 minutes
- **Test verification**: ~30 minutes
- **Documentation**: ~30 minutes
- **Total**: ~3 hours

### Timeline

**Immediate** - This blocks Python SDK users from using 8 tools!

---

## Architectural Principle Learned

**"Keep the tools synchronous, make the orchestration async."**

- **Tools**: Synchronous, blocking operations (simple, testable)
- **MCP Layer**: Async orchestration, task management, non-blocking
- **Core SDK**: Synchronous API, runs tools directly
- **Result**: Both work, clean separation, no breaking changes

---

**Status**: 🔴 **BLOCKING ISSUE** - Requires immediate fix
**Priority**: **P0 - Critical**
**Assigned**: Architecture review and implementation
**ETA**: 3 hours

