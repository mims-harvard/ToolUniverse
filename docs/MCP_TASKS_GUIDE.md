# MCP Tasks: Async Operations in ToolUniverse

**Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: 2026-02-09

---

## Overview

ToolUniverse now supports **MCP Tasks** ([Model Context Protocol Tasks](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)), enabling non-blocking execution of long-running scientific operations. This native protocol support allows tools like ProteinsPlus docking (5-60 minutes) and SwissDock simulations (10-30 minutes) to run in the background while you continue working.

### What is MCP Tasks?

MCP Tasks is the official Model Context Protocol feature for handling long-running operations. When a tool supports tasks, clients (like Claude Code, Claude Desktop, Cursor) automatically:

- ✅ Get an immediate task ID (no waiting!)
- ✅ Poll for status updates automatically
- ✅ Display progress messages to the user
- ✅ Retrieve results when complete
- ✅ Support cancellation

**No manual polling or ID tracking required!**

### Key Benefits

| Feature | Before (Blocking) | After (MCP Tasks) |
|---------|------------------|-------------------|
| **Response Time** | 5-60 minutes | < 1 second |
| **User Experience** | Frozen, no status | Progress updates |
| **Parallel Jobs** | ❌ One at a time | ✅ Run multiple concurrently |
| **Cancellation** | ❌ Not supported | ✅ Cancel anytime |
| **Client Integration** | Custom implementation | Native MCP support |

---

## Quick Start

### Using MCP Tasks (Recommended)

With MCP-aware clients (Claude Code, Claude Desktop, Cursor):

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Automatically runs as task if tool supports it
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# While this runs, you can:
# - Submit other tasks in parallel
# - Continue working
# - See progress updates
# - Cancel if needed

print(result["data"]["pockets"])  # Results when complete
```

**What you see:**
```
🔄 Running ProteinsPlus_predict_binding_sites...
   Status: Job SYxm7deaMSwvfjaReLmjT6VX submitted
   Status: Processing structure (45% complete)
   Status: Processing structure (70% complete)
✅ Complete! Found 3 binding pockets.
```

### Parallel Execution

Run multiple long-running jobs concurrently:

```python
import asyncio
from tooluniverse import ToolUniverse

async def parallel_docking():
    tu = ToolUniverse()
    tu.load_tools()

    # Submit 3 jobs in parallel
    results = await asyncio.gather(
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR"),
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="1ABC"),
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="3XYZ"),
    )

    return results  # All 3 run concurrently!

# Run the workflow
results = asyncio.run(parallel_docking())
```

**Performance:**
- Sequential: 15-180 minutes (5-60 min × 3 jobs)
- Parallel: 5-60 minutes (fastest of 3 jobs)
- **Speedup: 3x** (or more with more jobs!)

---

## Unified Async API

ToolUniverse now has a **context-aware** execution engine that automatically detects whether you're in a synchronous or asynchronous context.

### How It Works

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# In sync context (Jupyter, script, etc.)
result = tu.tools.some_tool(param="value")  # Blocks until complete

# In async context (async function)
async def research():
    result = await tu.tools.some_tool(param="value")  # Non-blocking!
    return result
```

**No separate `arun()` method needed!** The same `run()` API works everywhere.

### Context Detection

The system detects your execution context using `asyncio.get_running_loop()`:

```python
# Sync context detection
try:
    asyncio.get_running_loop()
    # Async context - use await
except RuntimeError:
    # Sync context - blocking execution
```

### Execution Modes

| Your Context | Tool Type | Behavior |
|--------------|-----------|----------|
| Sync | Sync tool | Direct execution |
| Sync | Async tool | Wrapped with `asyncio.run()` |
| Async | Sync tool | Executed with `asyncio.to_thread()` |
| Async | Async tool | Direct await execution |

**Result:** Any tool works in any context, automatically!

---

## Task Management

### Task Lifecycle

```
[*] → working → completed → [*]
          ↓
       failed → [*]
          ↓
      cancelled → [*]
```

- **working**: Task is processing
- **completed**: Task finished successfully
- **failed**: Task failed with error
- **cancelled**: Task was cancelled by user

### Checking Task Status

When using MCP clients, this is automatic. For programmatic access:

```python
from tooluniverse.task_manager import TaskManager

# Create TaskManager
manager = TaskManager(tool_universe=tu)

# Create task
task_id = await manager.create_task(
    tool_name="ProteinsPlus_predict_binding_sites",
    arguments={"pdb_id": "2OZR"},
    ttl=3600000  # 1 hour lifetime
)

# Get status
status = await manager.get_status(task_id)
print(status)
# {
#   "taskId": "786512e2-9e0d-44bd-8f29-789f320fe840",
#   "status": "working",
#   "statusMessage": "Processing structure (45% complete)",
#   "pollInterval": 5000
# }

# Wait for result (blocks until complete)
result = await manager.get_result(task_id)

# Cancel task
await manager.cancel_task(task_id)

# List all tasks
tasks = await manager.list_tasks()
```

### Task Time-to-Live (TTL)

Tasks have a configurable lifetime to prevent memory leaks:

```python
# Default: 1 hour
task_id = await manager.create_task(
    tool_name="...",
    arguments={...},
    ttl=3600000  # milliseconds
)

# For longer jobs
task_id = await manager.create_task(
    tool_name="...",
    arguments={...},
    ttl=7200000  # 2 hours
)
```

After TTL expires, completed task results are cleaned up automatically.

---

## Creating Async Tools

### Basic Async Tool

Convert a blocking tool to async:

```python
import asyncio
from typing import Dict, Any, Optional
from tooluniverse.task_progress import TaskProgress

class MyAsyncTool:
    def __init__(self):
        self.name = "My_Async_Tool"
        self.description = "Example async tool"
        self.parameter = {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        }
        self.fields = {"type": "REST"}

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional[TaskProgress] = None
    ) -> Dict[str, Any]:
        """Execute tool asynchronously with progress reporting."""

        # Step 1: Initial work
        if progress:
            await progress.set_message("Starting analysis...")

        # Do some work
        await asyncio.sleep(2)

        # Step 2: More work
        if progress:
            await progress.set_message("Processing data (50% complete)...")

        await asyncio.sleep(2)

        # Step 3: Final work
        if progress:
            await progress.set_message("Finalizing results...")

        await asyncio.sleep(1)

        # Return result
        return {
            "data": {
                "result": "Analysis complete",
                "input": arguments["input"]
            }
        }

    def get_batch_concurrency_limit(self):
        return 0  # No limit (tools run fully in parallel)

    def handle_error(self, exception):
        from tooluniverse.exceptions import ToolError
        return ToolError(
            message=str(exception),
            error_type="execution_error",
            details={"exception_type": type(exception).__name__}
        )
```

### Progress Reporting

The `TaskProgress` object provides methods to update task status:

```python
async def run(self, arguments, progress=None):
    if progress:
        # Simple message
        await progress.set_message("Processing structure...")

        # Message with percentage
        await progress.set_progress(
            current=45,
            total=100,
            message="Processing structure"
        )
        # Displays: "Processing structure (45%)"
```

### Tool Configuration

Register the async tool with task support:

```json
{
  "type": "MyAsyncTool",
  "name": "My_Async_Tool",
  "description": "Example async tool that runs in background",
  "execution": {
    "taskSupport": "required"
  },
  "parameter": {
    "type": "object",
    "properties": {
      "input": {"type": "string"}
    },
    "required": ["input"]
  }
}
```

**Task Support Modes:**
- `"required"`: Clients MUST use task mode (for long operations)
- `"optional"`: Clients MAY use task mode (for variable-time operations)
- `"forbidden"`: Tool cannot be used as task (for instant operations)

---

## Real-World Examples

### Example 1: Protein Docking Pipeline

```python
import asyncio
from tooluniverse import ToolUniverse

async def docking_pipeline(protein_id, ligand_smiles):
    """Run complete docking workflow with multiple async tools."""
    tu = ToolUniverse()
    tu.load_tools()

    # Step 1: Get protein structure
    structure = await tu.tools.RCSB_PDB_get_structure_by_id(
        pdb_id=protein_id
    )

    # Step 2: Predict binding sites (5-15 minutes, runs as task)
    binding_sites = await tu.tools.ProteinsPlus_predict_binding_sites(
        pdb_id=protein_id
    )

    # Step 3: Run docking (10-30 minutes, runs as task)
    docking_results = await tu.tools.SwissDock_dock_ligand(
        target_pdb_id=protein_id,
        ligand_smiles=ligand_smiles
    )

    return {
        "structure": structure,
        "binding_sites": binding_sites,
        "docking": docking_results
    }

# Run pipeline
results = asyncio.run(docking_pipeline("2OZR", "CC(C)Cc1ccc(cc1)C(C)C(O)=O"))
```

### Example 2: Multi-Target Screening

```python
async def screen_multiple_targets(ligand_smiles, target_ids):
    """Screen a ligand against multiple protein targets in parallel."""
    tu = ToolUniverse()
    tu.load_tools()

    # Submit all docking jobs in parallel
    tasks = [
        tu.tools.SwissDock_dock_ligand(
            target_pdb_id=target_id,
            ligand_smiles=ligand_smiles
        )
        for target_id in target_ids
    ]

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    successful = []
    failed = []
    for target_id, result in zip(target_ids, results):
        if isinstance(result, Exception):
            failed.append({"target": target_id, "error": str(result)})
        else:
            successful.append({"target": target_id, "result": result})

    return {"successful": successful, "failed": failed}

# Screen ligand against 5 targets
results = asyncio.run(screen_multiple_targets(
    ligand_smiles="CC(C)Cc1ccc(cc1)C(C)C(O)=O",
    target_ids=["2OZR", "1ABC", "3XYZ", "4DEF", "5GHI"]
))

print(f"Successful: {len(results['successful'])}")
print(f"Failed: {len(results['failed'])}")
```

### Example 3: Batch Processing with Progress

```python
async def batch_process_proteins(pdb_ids):
    """Process multiple proteins with progress tracking."""
    tu = ToolUniverse()
    tu.load_tools()

    total = len(pdb_ids)
    results = []

    for idx, pdb_id in enumerate(pdb_ids, 1):
        print(f"Processing {idx}/{total}: {pdb_id}")

        try:
            # This runs as task with progress
            result = await tu.tools.ProteinsPlus_predict_binding_sites(
                pdb_id=pdb_id
            )
            results.append({"pdb_id": pdb_id, "status": "success", "data": result})
        except Exception as e:
            results.append({"pdb_id": pdb_id, "status": "failed", "error": str(e)})

    return results

# Process 10 proteins
results = asyncio.run(batch_process_proteins([
    "2OZR", "1ABC", "3XYZ", "4DEF", "5GHI",
    "6JKL", "7MNO", "8PQR", "9STU", "1VWX"
]))

# Summary
successful = sum(1 for r in results if r["status"] == "success")
print(f"Completed: {successful}/{len(results)}")
```

---

## Error Handling

### Handling Task Failures

```python
from tooluniverse.exceptions import ToolError, ToolUnavailableError

async def safe_docking(pdb_id):
    tu = ToolUniverse()
    tu.load_tools()

    try:
        result = await tu.tools.ProteinsPlus_predict_binding_sites(
            pdb_id=pdb_id
        )
        return {"status": "success", "data": result}
    except ToolError as e:
        # Tool execution error
        return {"status": "failed", "error": str(e)}
    except ToolUnavailableError as e:
        # Tool not available
        return {"status": "unavailable", "error": str(e)}
    except TimeoutError:
        # Task exceeded TTL
        return {"status": "timeout", "error": "Task timed out"}
    except RuntimeError as e:
        # Task was cancelled
        if "cancelled" in str(e).lower():
            return {"status": "cancelled", "error": "Task was cancelled"}
        raise
```

### Batch Error Isolation

When running multiple tasks, one failure doesn't abort others:

```python
async def robust_batch():
    tu = ToolUniverse()
    tu.load_tools()

    calls = [
        {"name": "ProteinsPlus_predict_binding_sites", "arguments": {"pdb_id": "2OZR"}},
        {"name": "ProteinsPlus_predict_binding_sites", "arguments": {"pdb_id": "INVALID"}},
        {"name": "ProteinsPlus_predict_binding_sites", "arguments": {"pdb_id": "1ABC"}},
    ]

    # All tasks execute, failures return error dicts
    results = await tu.run(calls)

    # Process results
    for i, result in enumerate(results):
        if "error" in result:
            print(f"Call {i} failed: {result['error']}")
        else:
            print(f"Call {i} succeeded: {result['data']}")
```

---

## Performance Optimization

### Concurrency Limits

Tools can specify concurrency limits to prevent overloading APIs:

```python
def get_batch_concurrency_limit(self):
    return 5  # Max 5 concurrent requests to this API
```

- `return 0`: No limit (fully parallel)
- `return N`: Max N concurrent requests

### Caching Long Operations

Enable caching for expensive async operations:

```python
tu = ToolUniverse(use_cache=True)
tu.load_tools()

# First call: 15 minutes (runs job)
result1 = await tu.tools.ProteinsPlus_predict_binding_sites(
    pdb_id="2OZR",
    use_cache=True
)

# Second call: < 1 second (from cache!)
result2 = await tu.tools.ProteinsPlus_predict_binding_sites(
    pdb_id="2OZR",
    use_cache=True
)
```

### Connection Pooling

For tools making HTTP requests, use connection pooling:

```python
import aiohttp

class OptimizedAsyncTool:
    def __init__(self):
        self._session = None

    async def _get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def run(self, arguments, progress=None):
        session = await self._get_session()
        async with session.get(url) as response:
            data = await response.json()
            return {"data": data}

    async def close(self):
        if self._session:
            await self._session.close()
```

---

## Testing Async Tools

### Unit Tests

```python
import pytest
import pytest_asyncio
from tooluniverse import ToolUniverse

@pytest_asyncio.fixture
async def tu():
    """ToolUniverse fixture with cleanup."""
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    try:
        tu.close()
    except Exception:
        pass

@pytest.mark.asyncio
async def test_async_tool_execution(tu):
    """Test async tool executes correctly."""
    result = await tu.tools.ProteinsPlus_predict_binding_sites(
        pdb_id="2OZR"
    )

    assert "data" in result
    assert "pockets" in result["data"]
    assert len(result["data"]["pockets"]) > 0

@pytest.mark.asyncio
async def test_parallel_execution(tu):
    """Test multiple tasks run in parallel."""
    import time

    start = time.time()
    results = await asyncio.gather(
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR"),
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="1ABC"),
        tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="3XYZ"),
    )
    elapsed = time.time() - start

    # Should complete in ~time_per_job, not 3x time_per_job
    assert len(results) == 3
    for result in results:
        assert "data" in result
```

### Integration Tests with TaskManager

```python
@pytest.mark.asyncio
async def test_task_manager_lifecycle():
    """Test task creation, status, and result retrieval."""
    from tooluniverse.task_manager import TaskManager

    tu = ToolUniverse()
    tu.load_tools()
    manager = TaskManager(tool_universe=tu)

    try:
        # Create task
        task_id = await manager.create_task(
            tool_name="ProteinsPlus_predict_binding_sites",
            arguments={"pdb_id": "2OZR"},
            ttl=3600000
        )

        assert task_id is not None

        # Check status immediately (should be working)
        status = await manager.get_status(task_id)
        assert status["status"] == "working"

        # Wait for result (this blocks until complete)
        result = await manager.get_result(task_id, timeout=1800)

        assert "data" in result
        assert "pockets" in result["data"]

        # Status should now be completed
        status = await manager.get_status(task_id)
        assert status["status"] == "completed"

    finally:
        await manager.stop()
        tu.close()
```

---

## Troubleshooting

### Task Hangs or Doesn't Complete

**Symptoms:**
- Task stuck in "working" status
- No progress updates
- Eventually times out

**Solutions:**

1. **Check API availability:**
   ```python
   # Test if API is reachable
   import requests
   response = requests.get("https://proteins.plus/api/status")
   print(response.status_code)
   ```

2. **Verify polling logic:**
   - Ensure tool checks both HTTP 200 and 202 status codes
   - Check `response.json().get("status_code")` for ProteinsPlus

3. **Increase timeout:**
   ```python
   task_id = await manager.create_task(
       tool_name="...",
       arguments={...},
       ttl=7200000  # 2 hours instead of 1
   )
   ```

### Progress Not Updating

**Symptoms:**
- Task completes but no progress messages shown
- Status always shows generic message

**Solutions:**

1. **Ensure tool accepts progress parameter:**
   ```python
   async def run(self, arguments, progress=None):  # ✅ Correct
       if progress:
           await progress.set_message("...")
   ```

2. **Call set_message() regularly:**
   ```python
   # In polling loop
   while True:
       if progress:
           await progress.set_message(f"Status: {status}")
       await asyncio.sleep(10)
   ```

### Memory Leaks with Long-Running Server

**Symptoms:**
- Memory usage grows over time
- Many old completed tasks in memory

**Solutions:**

1. **Set appropriate TTL:**
   ```python
   task_id = await manager.create_task(
       tool_name="...",
       arguments={...},
       ttl=1800000  # 30 minutes (shorter for frequent jobs)
   )
   ```

2. **Manually clean up old tasks:**
   ```python
   # In TaskManager, call cleanup periodically
   await manager._cleanup_expired_tasks()
   ```

---

## Best Practices

### ✅ Do

1. **Use MCP Tasks for long operations** (> 5 seconds)
2. **Report progress regularly** (every 5-10 seconds)
3. **Set realistic TTL** (2x expected runtime)
4. **Handle errors gracefully** (use try/except)
5. **Test with real APIs** before production
6. **Cache expensive operations** when deterministic
7. **Use connection pooling** for HTTP-heavy tools

### ❌ Don't

1. **Don't use tasks for instant operations** (< 1 second)
2. **Don't block event loop** (use `await asyncio.sleep()`, not `time.sleep()`)
3. **Don't ignore HTTP 202** status (ProteinsPlus uses it!)
4. **Don't swallow exceptions** (log and return error dicts)
5. **Don't create infinite loops** without timeout
6. **Don't poll too frequently** (< 5 seconds causes API load)

---

## Migration Guide

### From Blocking to Async

**Before:**
```python
def run(self, arguments):
    result = self._submit_job(...)
    job_id = extract_id(result)

    while True:
        status = requests.get(f"{url}/{job_id}")
        if status.status_code == 200:
            return parse_results(status.json())
        time.sleep(10)  # ❌ Blocks thread!
```

**After:**
```python
async def run(self, arguments, progress=None):
    result = self._submit_job(...)
    job_id = extract_id(result)

    if progress:
        await progress.set_message(f"Job {job_id} submitted")

    while True:
        status = requests.get(f"{url}/{job_id}")
        if status.status_code == 200:
            return parse_results(status.json())

        if progress:
            await progress.set_message("Processing...")

        await asyncio.sleep(10)  # ✅ Non-blocking!
```

**Configuration:**
```json
{
  "name": "My_Tool",
  "execution": {
    "taskSupport": "required"  // ✅ Add this
  },
  ...
}
```

---

## Reference

### MCP Tasks Specification

- [MCP Tasks Protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [MCP Tasks SEP-1686](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1686)
- [MCP Async Tasks Guide](https://workos.com/blog/mcp-async-tasks-ai-agent-workflows)

### ToolUniverse Components

- **TaskManager**: `src/tooluniverse/task_manager.py`
- **TaskProgress**: `src/tooluniverse/task_progress.py`
- **Unified Async API**: `src/tooluniverse/execute_function.py`
- **MCP Server**: `src/tooluniverse/smcp_server.py`

### Tests

- **MCP Tasks Integration**: `tests/test_mcp_tasks_integration.py` (13 tests)
- **Edge Cases**: `tests/test_edge_cases.py` (12 tests)
- **Unified Async API**: `tests/test_unified_async_api.py` (16 tests)

**Total Test Coverage**: 28/28 tests passing (100%)

---

## Support

Need help with MCP Tasks or async operations?

- **Slack**: [ToolUniverse Community](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ)
- **GitHub Issues**: [Report Issues](https://github.com/mims-harvard/ToolUniverse/issues)
- **Email**: [Shanghua Gao](mailto:shanghuagao@gmail.com)

---

**Ready to use MCP Tasks!** All tools marked with `"taskSupport": "required"` will automatically run as background tasks when called from MCP clients. 🚀
