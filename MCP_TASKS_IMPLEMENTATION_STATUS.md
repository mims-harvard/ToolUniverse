# MCP Tasks Implementation Status

## Overview
Implementation of native MCP Tasks support for ProteinsPlus and SwissDock async operations in ToolUniverse.

**Date**: 2026-02-08
**Branch**: auto
**Status**: 4/7 tasks completed ✓

---

## ✅ COMPLETED Tasks

### Task #1: TaskManager Infrastructure ✓
**Files Created:**
- `src/tooluniverse/task_manager.py` - Task state management, background execution
- `src/tooluniverse/task_progress.py` - Progress reporting helper

**Features Implemented:**
- Task dataclass with status tracking (working, completed, failed, cancelled)
- TaskManager with background asyncio execution
- Progress reporting via TaskProgress
- TTL cleanup loop
- Authorization context support for multi-user isolation
- Cryptographically secure task IDs (UUID)

**Key Methods:**
- `create_task()` - Creates task and starts background execution
- `get_status()` - Returns current task status
- `get_result()` - Blocks until completion, returns result
- `list_tasks()` - Lists all tasks (filtered by auth context)
- `cancel_task()` - Cancels running task

---

### Task #2: MCP Server with Tasks Capability ✓
**File Modified:**
- `src/tooluniverse/smcp.py`

**Changes Made:**
1. **TaskManager Integration (line ~370)**
   ```python
   from .task_manager import TaskManager
   self.task_manager = TaskManager(tool_universe=self.tooluniverse)
   self._task_manager_started = False
   ```

2. **MCP Tasks Handlers Added (line ~715)**
   - `handle_tasks_get(task_id, auth_context)` - Get task status
   - `handle_tasks_list(auth_context, cursor)` - List all tasks
   - `handle_tasks_cancel(task_id, auth_context)` - Cancel task
   - `handle_tasks_result(task_id, auth_context, timeout)` - Get result

3. **Tool Execution Modified (line ~2457)**
   - Added `_task` parameter extraction from kwargs
   - Check tool's `execution.taskSupport` configuration
   - If task requested and supported: create task and return task metadata
   - If task requested but forbidden: return error

4. **Cleanup (line ~2036)**
   - Added TaskManager stop in `close()` method

---

### Task #3: ProteinsPlus Tools Async Conversion ✓
**File Modified:**
- `src/tooluniverse/proteinsplus_tool.py`
- `src/tooluniverse/data/proteinsplus_tools.json`

**Code Changes:**
1. **Imports Updated:**
   ```python
   import asyncio
   import httpx
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from .task_progress import TaskProgress
   ```

2. **All Methods Converted to Async:**
   - `async def _submit_job()` - Uses httpx.AsyncClient
   - `async def _poll_job_status(job_id, status_url, progress)` - Non-blocking polling
   - `async def _make_sync_request()` - Uses httpx.AsyncClient
   - `async def run(arguments, progress)` - Main entry point

3. **Key Improvements:**
   - Replaced `requests` with `httpx` for async HTTP
   - Replaced `time.sleep()` with `await asyncio.sleep()`
   - Added `progress` parameter throughout
   - Progress reporting: "Job submitted", "Processing (poll #N)", "Completed"
   - Removed `max_wait_time` limit (MCP Tasks handles timeout via TTL)

**Configuration Changes:**
Added to all 5 ProteinsPlus tools in `proteinsplus_tools.json`:
```json
"execution": {
  "taskSupport": "required"
}
```

**Tools Updated:**
1. ProteinsPlus_predict_binding_sites (DoGSite)
2. ProteinsPlus_predict_binding_sites_v3 (DoGSite3)
3. ProteinsPlus_generate_interaction_diagram (PoseView)
4. ProteinsPlus_analyze_binding_site_similarity (SIENA)
5. ProteinsPlus_profile_structure_quality (StructureProfiler)

---

## ✅ COMPLETED Task #4: SwissDock Async Conversion + Schema Fixes

### Task #4: SwissDock Async Conversion + Schema Fixes ✓
**Files Modified:**
- `src/tooluniverse/swissdock_tool.py`
- `src/tooluniverse/data/swissdock_tools.json`

**Progress:**
✓ Imports updated (httpx, asyncio, TYPE_CHECKING)
✓ All methods converted to async
✓ Schema violations fixed (removed session_id from error responses)
✓ Progress reporting added throughout
✓ Configuration updated with taskSupport annotations

**Changes Completed:**

1. **Imports Updated:**
   ```python
   import asyncio
   import httpx
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from .task_progress import TaskProgress
   ```

2. **All Methods Converted to Async:**
   - `async def run(arguments, progress)` - Main entry point
   - `async def _check_server_status()` - Uses httpx.AsyncClient
   - `async def _prepare_ligand()` - Uses httpx.AsyncClient
   - `async def _prepare_target()` - Uses httpx.AsyncClient
   - `async def _set_docking_parameters()` - Uses httpx.AsyncClient
   - `async def _start_docking()` - Uses httpx.AsyncClient
   - `async def _check_status()` - Uses httpx.AsyncClient
   - `async def _retrieve_session()` - Uses httpx.AsyncClient
   - `async def _dock_ligand(arguments, progress)` - Main workflow with progress
   - `async def _check_job_status()` - Instant operation
   - `async def _retrieve_results()` - Instant operation

3. **Schema Violations Fixed (CRITICAL):**
   ```python
   # ❌ BEFORE (violates oneOf schema):
   return {
       "status": "error",
       "error": f"Docking job failed: {error_msg}",
       "session_id": session_id  # ❌ Extra field!
   }

   # ✅ AFTER (compliant):
   return {
       "error": f"Docking job failed: {error_msg}"
   }
   ```

4. **Progress Reporting Added:**
   - "Checking SwissDock server status"
   - "Preparing ligand from SMILES"
   - "Preparing target protein {pdb_id}"
   - "Setting docking parameters"
   - "Starting docking job (session: {session_id})"
   - "Polling docking status (attempt {N}/{MAX})"
   - "Docking complete, retrieving results"

5. **Configuration Updates:**
   - **dock_ligand**: `"execution": {"taskSupport": "required"}` ✓
   - **check_job_status**: `"execution": {"taskSupport": "forbidden"}` ✓
   - **retrieve_results**: `"execution": {"taskSupport": "forbidden"}` ✓

6. **Replaced Blocking Calls:**
   - `requests` → `httpx.AsyncClient`
   - `time.sleep()` → `await asyncio.sleep()`

**Required Changes (REMOVED - now completed):**

1. **Schema Violation Fixes (CRITICAL):**
   ```python
   # ❌ WRONG (current):
   return {
       "status": "error",
       "error": f"Docking job failed: {error_msg}",
       "session_id": session_id  # ❌ Violates oneOf schema!
   }

   # ✅ CORRECT:
   return {
       "error": f"Docking job failed: {error_msg}"
   }
   # session_id only in success data, NOT in error responses
   ```

2. **Async Conversion Needed:**
   - `async def _check_server_status()`
   - `async def _prepare_ligand()`
   - `async def _prepare_target()`
   - `async def _set_docking_parameters()`
   - `async def _start_docking()`
   - `async def _check_status()`
   - `async def _retrieve_session()`
   - `async def _dock_ligand(arguments, progress)`
   - `async def _check_job_status()`
   - `async def _retrieve_results()`
   - `async def run(arguments, progress)`

3. **Progress Reporting:**
   ```python
   if progress:
       await progress.set_message("Preparing ligand...")
       await progress.set_message("Starting docking...")
       await progress.set_message(f"Polling status (attempt {attempt}/{MAX_POLL_ATTEMPTS})")
   ```

4. **Configuration Updates:**
   In `swissdock_tools.json`:
   - **dock_ligand**: Add `"execution": {"taskSupport": "required"}`
   - **check_job_status**: Add `"execution": {"taskSupport": "forbidden"}` (instant)
   - **retrieve_results**: Add `"execution": {"taskSupport": "forbidden"}` (instant)

---

## ⏳ PENDING Tasks

### Task #5: Unit Tests for TaskManager
**Files to Create:**
- `tests/test_task_manager.py`

**Test Coverage Needed:**
- Task creation and ID generation
- Status polling
- Result retrieval
- Task cancellation
- TTL cleanup
- Progress reporting
- Auth context isolation

---

### Task #6: Integration Testing
**Test Scenarios:**
1. **ProteinsPlus with MCP Client:**
   - Submit job with `_task` parameter
   - Verify immediate task ID return
   - Poll status via `tasks/get`
   - Retrieve results via `tasks/result`

2. **SwissDock with MCP Client:**
   - Test dock_ligand as task
   - Test check_job_status as instant (forbidden)
   - Test retrieve_results as instant (forbidden)

3. **Multi-User Testing (if HTTP API):**
   - Verify task isolation by auth context
   - Test unauthorized access attempts

---

## 📝 TODO: Documentation Updates

### Task #7: Update Documentation
**Files to Update:**
- `README.md` - Add MCP Tasks section
- Tool descriptions - Mention background task operation
- Examples - Show task usage

**Documentation Needed:**
```markdown
# MCP Tasks Support

ToolUniverse now supports MCP Tasks for long-running operations!

## What are MCP Tasks?

MCP Tasks allow tools to return immediately with a task ID, then execute in the background.
Clients can poll for status and retrieve results when ready.

## Usage

Tools that support tasks (ProteinsPlus, SwissDock) will automatically:
- Return task ID immediately (< 1 second)
- Execute in background
- Report progress updates
- Provide results when complete

## Example

```python
# Start analysis (returns immediately)
task = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Claude Code/Desktop handles:
# - Polling task status
# - Showing progress updates
# - Retrieving results
# - Displaying final output
```

## Which Tools Support Tasks?

**Required (long-running):**
- All 5 ProteinsPlus tools (5-30 min jobs)
- SwissDock dock_ligand (5-60 min jobs)

**Forbidden (instant):**
- SwissDock check_job_status
- SwissDock retrieve_results
```

---

## Key Design Decisions

### 1. Why MCP Tasks Instead of Custom Split-Tool Approach?

**Original Plan (rejected):**
- Split each tool into 3: Submit/CheckStatus/GetResults
- 15 new tools total (5 endpoints × 3)
- Custom cache-based job tracking
- Manual user ID management

**MCP Tasks Approach (chosen):**
- Keep existing 8 tools
- Native MCP protocol support
- Client handles polling automatically
- Built-in auth context binding
- Works with all MCP clients

**Benefits:**
- ✅ Standardized protocol
- ✅ Less code (leverage native MCP)
- ✅ Better UX (progress bars, cancellation)
- ✅ More secure (auth context)
- ✅ Easier maintenance

### 2. Task Support Modes

- **`"required"`**: Tool MUST be called as task (ProteinsPlus - long jobs)
- **`"optional"`**: Tool MAY be task (for variable-time operations)
- **`"forbidden"`**: Tool cannot be task (status/results - instant)

### 3. No Timeout in Tool Code

ProteinsPlus previously had `max_wait_time: 1800` (30 min).
With MCP Tasks:
- Removed max_wait_time from polling logic
- TTL handled by TaskManager (default: 1 hour)
- Allows very long jobs without artificial limits

### 4. Progress Reporting Strategy

Non-blocking updates during polling:
```python
await progress.set_message(f"Processing job {job_id} (poll #{iteration})")
```

Clients see:
```
🔄 ProteinsPlus_predict_binding_sites (Processing... poll #3)
```

---

## Testing Checklist

- [ ] Unit tests: TaskManager create/get/cancel/cleanup
- [ ] Unit tests: TaskProgress message updates
- [ ] Integration: ProteinsPlus tools load correctly
- [ ] Integration: ProteinsPlus task creation returns immediately
- [ ] Integration: Progress updates visible in client
- [ ] Integration: Results retrieved successfully
- [ ] Live API: Test with real ProteinsPlus job (2OZR)
- [ ] Integration: SwissDock dock_ligand as task
- [ ] Integration: SwissDock status/results as instant
- [ ] Multi-user: Auth context isolation (if HTTP API)

---

## Known Issues / Future Work

1. **FastMCP Integration**
   - Currently using manual task handlers
   - Future: Check if FastMCP has built-in MCP Tasks support
   - May need to register handlers via FastMCP's middleware system

2. **Task Persistence**
   - Tasks currently only in memory
   - Lost on server restart
   - Future: Optional persistence to Redis/database

3. **Notification Push**
   - Currently client polls via tasks/get
   - MCP supports notifications/tasks/status
   - Future: Implement push notifications for status changes

4. **SwissDock Completion**
   - All async conversion needs finishing
   - Schema violations need fixing
   - Testing needed

---

## Files Modified Summary

**New Files:**
- `src/tooluniverse/task_manager.py`
- `src/tooluniverse/task_progress.py`

**Modified Files:**
- `src/tooluniverse/smcp.py`
- `src/tooluniverse/proteinsplus_tool.py`
- `src/tooluniverse/data/proteinsplus_tools.json`
- `src/tooluniverse/swissdock_tool.py` (partial)
- `src/tooluniverse/data/swissdock_tools.json` (pending)

**Test Files (pending):**
- `tests/test_task_manager.py`

---

## Next Steps

1. **Complete SwissDock async conversion** (Task #4)
   - Convert all methods to async with httpx
   - Fix schema violations (remove session_id from errors)
   - Add progress reporting
   - Update tool configurations

2. **Create unit tests** (Task #5)
   - Test TaskManager functionality
   - Test progress reporting
   - Test error handling

3. **Integration testing** (Task #6)
   - Test with MCP client (Claude Code/Desktop)
   - Verify task creation, polling, results
   - Test live API calls

4. **Update documentation** (Task #7)
   - Add MCP Tasks section to README
   - Update tool descriptions
   - Add usage examples

---

## References

- [MCP Tasks Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [MCP Tasks SEP-1686](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1686)
- [MCP Async Tasks: Building long-running workflows](https://workos.com/blog/mcp-async-tasks-ai-agent-workflows)
- [FastMCP Background Tasks](https://gofastmcp.com/servers/tasks)
- [Long Running Tasks in MCP](https://agnost.ai/blog/long-running-tasks-mcp/)
