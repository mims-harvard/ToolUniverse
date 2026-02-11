# Guide: Writing Async Tools in ToolUniverse

**Last Updated**: 2026-02-09
**Difficulty**: Intermediate
**Prerequisites**: Basic Python, asyncio knowledge

---

## Quick Answer: Sync vs Async

**Use Sync when**: Operation completes in < 5 seconds
**Use Async when**: Operation takes > 5 seconds (API jobs, computations, file processing)

### Key Difference

```python
# Sync Tool (blocks until complete)
def run(self, arguments):
    result = requests.get(url)  # Blocks thread
    return {"data": result.json()}

# Async Tool (non-blocking)
async def run(self, arguments, progress=None):
    result = await self._submit_job()  # Doesn't block!
    return {"data": result}
```

---

## Side-by-Side Comparison

### Sync Tool Example

```python
"""Sync tool - for fast operations (< 5 seconds)."""
import requests
from typing import Dict, Any

class MyFastTool:
    def __init__(self):
        self.name = "My_Fast_Tool"
        self.description = "Fast API query that returns immediately"
        self.parameter = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
        self.return_schema = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "results": {"type": "array"},
                                "count": {"type": "integer"}
                            }
                        },
                        "metadata": {"type": "object"}
                    },
                    "required": ["data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "error": {"type": "object"}
                    },
                    "required": ["error"]
                }
            ]
        }
        self.fields = {"type": "REST"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously - completes quickly."""
        query = arguments.get("query")

        # Fast API call
        response = requests.get(
            "https://api.example.com/search",
            params={"q": query}
        )

        if response.status_code != 200:
            return {
                "error": {
                    "message": f"API error: {response.status_code}",
                    "error_type": "api_error"
                }
            }

        return {
            "data": {
                "results": response.json()["results"],
                "count": len(response.json()["results"])
            },
            "metadata": {
                "query": query,
                "source": "example_api"
            }
        }

    def get_batch_concurrency_limit(self):
        return 5  # Max 5 parallel requests

    def handle_error(self, exception):
        from tooluniverse.exceptions import ToolError
        return ToolError(
            message=str(exception),
            error_type="execution_error",
            details={"exception_type": type(exception).__name__}
        )
```

### Async Tool Example

```python
"""Async tool - for long operations (> 5 seconds)."""
import asyncio
import requests
from typing import Dict, Any, Optional
from tooluniverse.task_progress import TaskProgress

class MyLongRunningTool:
    def __init__(self):
        self.name = "My_Long_Running_Tool"
        self.description = "Long-running job that takes 5-30 minutes"
        self.parameter = {
            "type": "object",
            "properties": {
                "input_data": {"type": "string", "description": "Data to process"}
            },
            "required": ["input_data"]
        }
        self.return_schema = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "job_id": {"type": "string"},
                                "results": {"type": "object"},
                                "status": {"type": "string"}
                            }
                        },
                        "metadata": {"type": "object"}
                    },
                    "required": ["data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "error": {"type": "object"}
                    },
                    "required": ["error"]
                }
            ]
        }
        self.fields = {"type": "REST"}

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional[TaskProgress] = None
    ) -> Dict[str, Any]:
        """Execute asynchronously with progress reporting."""

        # Step 1: Submit job (fast)
        if progress:
            await progress.set_message("Submitting job...")

        job_data = self._submit_job(arguments)
        job_id = job_data["job_id"]

        if progress:
            await progress.set_message(f"Job {job_id} submitted, waiting for results...")

        # Step 2: Poll for completion (long)
        max_polls = 180  # 30 minutes max (if 10s polling)
        polls = 0

        while polls < max_polls:
            # Check job status
            status_response = requests.get(
                f"https://api.example.com/jobs/{job_id}/status"
            )

            if status_response.status_code != 200:
                return {
                    "error": {
                        "message": "Failed to check job status",
                        "error_type": "api_error"
                    }
                }

            status_data = status_response.json()

            # Check if complete
            if status_data["status"] == "completed":
                if progress:
                    await progress.set_message("Job complete, fetching results...")

                # Get results
                results = self._fetch_results(job_id)
                return {
                    "data": {
                        "job_id": job_id,
                        "results": results,
                        "status": "completed"
                    },
                    "metadata": {
                        "polls": polls,
                        "duration_seconds": polls * 10
                    }
                }

            elif status_data["status"] == "failed":
                return {
                    "error": {
                        "message": status_data.get("error", "Job failed"),
                        "error_type": "job_failed"
                    }
                }

            # Still processing - update progress
            if progress:
                percent = status_data.get("progress", 0)
                await progress.set_message(
                    f"Processing... ({percent}% complete)"
                )

            # Wait before next poll
            await asyncio.sleep(10)  # ✅ Non-blocking sleep!
            polls += 1

        # Timeout
        return {
            "error": {
                "message": f"Job {job_id} timed out after {polls * 10} seconds",
                "error_type": "timeout"
            }
        }

    def _submit_job(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Submit job to API (sync helper method)."""
        response = requests.post(
            "https://api.example.com/jobs",
            json={"input": arguments["input_data"]}
        )
        return response.json()

    def _fetch_results(self, job_id: str) -> Dict[str, Any]:
        """Fetch job results (sync helper method)."""
        response = requests.get(
            f"https://api.example.com/jobs/{job_id}/results"
        )
        return response.json()

    def get_batch_concurrency_limit(self):
        return 3  # Max 3 parallel long-running jobs

    def handle_error(self, exception):
        from tooluniverse.exceptions import ToolError
        return ToolError(
            message=str(exception),
            error_type="execution_error",
            details={"exception_type": type(exception).__name__}
        )
```

---

## Key Differences Explained

### 1. Method Signature

**Sync**:
```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # No async keyword
    # No progress parameter
    pass
```

**Async**:
```python
async def run(
    self,
    arguments: Dict[str, Any],
    progress: Optional[TaskProgress] = None  # ✅ Add progress!
) -> Dict[str, Any]:
    # ✅ async keyword
    # ✅ Optional progress parameter
    pass
```

### 2. Sleep/Wait

**Sync** (❌ Blocks entire thread):
```python
import time
time.sleep(10)  # Blocks everything!
```

**Async** (✅ Non-blocking):
```python
await asyncio.sleep(10)  # Other tasks can run!
```

### 3. Progress Reporting

**Sync** (❌ No progress updates):
```python
def run(self, arguments):
    # Long operation...
    # User sees nothing until complete
    return result
```

**Async** (✅ Real-time progress):
```python
async def run(self, arguments, progress=None):
    if progress:
        await progress.set_message("Starting...")

    # Do work

    if progress:
        await progress.set_message("50% complete...")

    # More work

    if progress:
        await progress.set_message("Almost done...")

    return result
```

### 4. API Calls

**Sync** (❌ Blocking):
```python
import requests

response = requests.get(url)  # Blocks until response
data = response.json()
```

**Async** (✅ Can use async HTTP):
```python
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()  # Non-blocking!
```

**Note**: You can still use `requests` in async tools for simplicity, but `aiohttp` is more efficient.

### 5. Configuration JSON

**Sync Tool Config**:
```json
{
  "type": "MyFastTool",
  "name": "My_Fast_Tool",
  "description": "Fast API query",
  "execution": {
    "taskSupport": "forbidden"
  },
  ...
}
```

**Async Tool Config**:
```json
{
  "type": "MyLongRunningTool",
  "name": "My_Long_Running_Tool",
  "description": "Long-running job (5-30 minutes)",
  "execution": {
    "taskSupport": "required"
  },
  ...
}
```

**Key Difference**: `"taskSupport": "required"` tells MCP clients to run as background task!

---

## Step-by-Step: Creating an Async Tool

### Step 1: Create Tool Class File

**File**: `src/tooluniverse/my_async_tool.py`

```python
"""My async tool for long-running operations."""
import asyncio
import requests
from typing import Dict, Any, Optional
from tooluniverse.task_progress import TaskProgress
from tooluniverse.exceptions import ToolError


class MyAsyncTool:
    """Example async tool with job polling."""

    def __init__(self):
        self.name = "My_Async_Tool"
        self.description = "Process data with long-running job"
        self.parameter = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data to process"
                }
            },
            "required": ["data"]
        }
        self.return_schema = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "result": {"type": "string"},
                                "job_id": {"type": "string"}
                            }
                        },
                        "metadata": {"type": "object"}
                    },
                    "required": ["data"]
                },
                {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"},
                                "error_type": {"type": "string"}
                            }
                        }
                    },
                    "required": ["error"]
                }
            ]
        }
        self.fields = {"type": "REST"}

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional[TaskProgress] = None
    ) -> Dict[str, Any]:
        """Execute async operation."""
        try:
            # Submit job
            if progress:
                await progress.set_message("Submitting job...")

            job_id = self._submit_job(arguments["data"])

            # Poll for completion
            result = await self._poll_job(job_id, progress)

            return {
                "data": {
                    "result": result,
                    "job_id": job_id
                },
                "metadata": {
                    "tool": self.name
                }
            }

        except Exception as e:
            return {
                "error": {
                    "message": str(e),
                    "error_type": "execution_error"
                }
            }

    def _submit_job(self, data: str) -> str:
        """Submit job (sync helper)."""
        response = requests.post(
            "https://api.example.com/jobs",
            json={"data": data}
        )
        response.raise_for_status()
        return response.json()["job_id"]

    async def _poll_job(
        self,
        job_id: str,
        progress: Optional[TaskProgress]
    ) -> str:
        """Poll job until complete."""
        max_attempts = 180

        for attempt in range(max_attempts):
            response = requests.get(
                f"https://api.example.com/jobs/{job_id}"
            )
            response.raise_for_status()
            status = response.json()

            if status["status"] == "completed":
                return status["result"]

            if progress:
                percent = (attempt / max_attempts) * 100
                await progress.set_message(
                    f"Processing... ({percent:.0f}% time elapsed)"
                )

            await asyncio.sleep(10)

        raise TimeoutError(f"Job {job_id} timed out")

    def get_batch_concurrency_limit(self):
        return 5

    def handle_error(self, exception):
        return ToolError(
            message=str(exception),
            error_type="execution_error",
            details={"exception_type": type(exception).__name__}
        )
```

### Step 2: Create Configuration JSON

**File**: `src/tooluniverse/data/my_async_tools.json`

```json
{
  "tools": [
    {
      "type": "MyAsyncTool",
      "name": "My_Async_Tool",
      "description": "Process data with long-running job (5-30 minutes). Runs as background task.",
      "execution": {
        "taskSupport": "required"
      },
      "parameter": {
        "type": "object",
        "properties": {
          "data": {
            "type": "string",
            "description": "Data to process"
          }
        },
        "required": ["data"]
      },
      "return_schema": {
        "oneOf": [
          {
            "type": "object",
            "properties": {
              "data": {
                "type": "object",
                "properties": {
                  "result": {"type": "string"},
                  "job_id": {"type": "string"}
                }
              },
              "metadata": {"type": "object"}
            },
            "required": ["data"]
          },
          {
            "type": "object",
            "properties": {
              "error": {"type": "object"}
            },
            "required": ["error"]
          }
        ]
      },
      "example": {
        "arguments": {
          "data": "test_input"
        }
      }
    }
  ]
}
```

**Critical**: `"taskSupport": "required"` makes it run as background task!

### Step 3: Register Tool in ToolUniverse

**File**: `src/tooluniverse/default_config.py`

Add to tool type mappings:

```python
TOOL_TYPE_MAPPINGS = {
    # ... existing mappings ...
    "MyAsyncTool": "my_async_tool.MyAsyncTool",
}
```

### Step 4: Test Your Tool

**File**: `examples/test_my_async_tool.py`

```python
"""Test my async tool."""
import asyncio
from tooluniverse import ToolUniverse


async def test_async_tool():
    """Test async tool execution."""
    tu = ToolUniverse()
    tu.load_tools()

    print("Running async tool...")
    result = await tu.tools.My_Async_Tool(data="test_input")

    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_async_tool())
```

Run:
```bash
python examples/test_my_async_tool.py
```

---

## Progress Reporting Patterns

### Pattern 1: Simple Messages

```python
async def run(self, arguments, progress=None):
    if progress:
        await progress.set_message("Step 1: Initializing...")

    # Do work

    if progress:
        await progress.set_message("Step 2: Processing...")

    # Do work

    if progress:
        await progress.set_message("Step 3: Finalizing...")

    return result
```

### Pattern 2: Percentage Complete

```python
async def run(self, arguments, progress=None):
    total_steps = 10

    for step in range(total_steps):
        # Do work for this step
        process_step(step)

        if progress:
            percent = ((step + 1) / total_steps) * 100
            await progress.set_message(
                f"Processing step {step + 1}/{total_steps} ({percent:.0f}%)"
            )
```

### Pattern 3: API Progress

```python
async def run(self, arguments, progress=None):
    job_id = submit_job()

    while True:
        status = check_status(job_id)

        if progress:
            # Use API's progress percentage
            await progress.set_message(
                f"Job {job_id}: {status['progress']}% complete"
            )

        if status["done"]:
            break

        await asyncio.sleep(10)
```

### Pattern 4: Time-Based Progress

```python
async def run(self, arguments, progress=None):
    start_time = time.time()
    estimated_duration = 600  # 10 minutes

    while not is_complete():
        elapsed = time.time() - start_time
        percent = min(100, (elapsed / estimated_duration) * 100)

        if progress:
            await progress.set_message(
                f"Processing... ({percent:.0f}% of estimated time)"
            )

        await asyncio.sleep(10)
```

---

## When to Use Async vs Sync

### Use Sync Tool When:

✅ Operation completes in < 5 seconds
✅ Simple REST API query
✅ Database lookup
✅ File read (small files)
✅ Simple calculation
✅ No polling required

**Examples**:
- UniProt protein lookup
- PubChem compound search
- Quick database queries
- Simple calculations

### Use Async Tool When:

✅ Operation takes > 5 seconds
✅ Requires job submission + polling
✅ Long computation (> 1 minute)
✅ File processing (large files)
✅ Multiple dependent API calls
✅ Want progress updates

**Examples**:
- ProteinsPlus docking (5-60 minutes)
- SwissDock simulations (10-30 minutes)
- Large file downloads
- Complex computations
- Video processing

---

## Common Patterns

### Pattern 1: Job Submission + Polling

```python
async def run(self, arguments, progress=None):
    # 1. Submit job
    job_id = self._submit_job(arguments)

    # 2. Poll for completion
    while True:
        status = self._check_status(job_id)

        if status["complete"]:
            return self._fetch_results(job_id)

        if progress:
            await progress.set_message(status["message"])

        await asyncio.sleep(polling_interval)
```

### Pattern 2: Multi-Step Pipeline

```python
async def run(self, arguments, progress=None):
    # Step 1
    if progress:
        await progress.set_message("Step 1: Preprocessing...")
    step1_result = await self._preprocess(arguments)

    # Step 2
    if progress:
        await progress.set_message("Step 2: Main processing...")
    step2_result = await self._process(step1_result)

    # Step 3
    if progress:
        await progress.set_message("Step 3: Postprocessing...")
    final_result = await self._postprocess(step2_result)

    return {"data": final_result}
```

### Pattern 3: Parallel Sub-Tasks

```python
async def run(self, arguments, progress=None):
    if progress:
        await progress.set_message("Starting parallel tasks...")

    # Run 3 sub-tasks in parallel
    results = await asyncio.gather(
        self._task1(arguments),
        self._task2(arguments),
        self._task3(arguments)
    )

    if progress:
        await progress.set_message("Combining results...")

    combined = self._combine_results(results)
    return {"data": combined}
```

---

## Testing Async Tools

### Unit Test Example

```python
import pytest
import pytest_asyncio
from tooluniverse import ToolUniverse


@pytest_asyncio.fixture
async def tu():
    """ToolUniverse fixture."""
    tu = ToolUniverse()
    tu.load_tools()
    yield tu
    tu.close()


@pytest.mark.asyncio
async def test_my_async_tool(tu):
    """Test async tool execution."""
    result = await tu.tools.My_Async_Tool(data="test_input")

    assert "data" in result
    assert "result" in result["data"]
    assert result["data"]["result"] is not None


@pytest.mark.asyncio
async def test_async_tool_error_handling(tu):
    """Test async tool handles errors."""
    result = await tu.tools.My_Async_Tool(data="invalid_input")

    assert "error" in result
    assert "message" in result["error"]
```

### Integration Test with TaskManager

```python
@pytest.mark.asyncio
async def test_async_tool_with_task_manager():
    """Test async tool runs as task."""
    from tooluniverse.task_manager import TaskManager

    tu = ToolUniverse()
    tu.load_tools()
    manager = TaskManager(tool_universe=tu)

    try:
        # Create task
        task_id = await manager.create_task(
            tool_name="My_Async_Tool",
            arguments={"data": "test_input"},
            ttl=3600000
        )

        # Wait for completion
        result = await manager.get_result(task_id, timeout=300)

        assert "data" in result
        assert "result" in result["data"]

    finally:
        await manager.stop()
        tu.close()
```

---

## Common Mistakes & Solutions

### ❌ Mistake 1: Using `time.sleep()` in async function

```python
async def run(self, arguments, progress=None):
    time.sleep(10)  # ❌ Blocks entire event loop!
```

**✅ Solution**: Use `asyncio.sleep()`
```python
async def run(self, arguments, progress=None):
    await asyncio.sleep(10)  # ✅ Non-blocking!
```

### ❌ Mistake 2: Forgetting `await`

```python
async def run(self, arguments, progress=None):
    result = self._async_helper()  # ❌ Returns coroutine, not result!
```

**✅ Solution**: Add `await`
```python
async def run(self, arguments, progress=none):
    result = await self._async_helper()  # ✅ Gets actual result
```

### ❌ Mistake 3: Not checking `progress` is provided

```python
async def run(self, arguments, progress):
    await progress.set_message("...")  # ❌ Crashes if progress=None!
```

**✅ Solution**: Always check first
```python
async def run(self, arguments, progress=None):
    if progress:  # ✅ Check first!
        await progress.set_message("...")
```

### ❌ Mistake 4: Polling too frequently

```python
async def run(self, arguments, progress=None):
    while True:
        status = check_status()
        await asyncio.sleep(1)  # ❌ Too frequent! API may rate-limit
```

**✅ Solution**: Poll every 5-10 seconds
```python
async def run(self, arguments, progress=None):
    while True:
        status = check_status()
        await asyncio.sleep(10)  # ✅ Reasonable interval
```

### ❌ Mistake 5: No timeout

```python
async def run(self, arguments, progress=None):
    while True:  # ❌ Infinite loop!
        status = check_status()
        if status["done"]:
            break
        await asyncio.sleep(10)
```

**✅ Solution**: Add max attempts
```python
async def run(self, arguments, progress=None):
    max_attempts = 180  # 30 minutes
    for attempt in range(max_attempts):  # ✅ Will timeout
        status = check_status()
        if status["done"]:
            break
        await asyncio.sleep(10)
    else:
        raise TimeoutError("Job timed out")
```

---

## Real-World Example: ProteinsPlus Tool

Here's a simplified version of the actual ProteinsPlus tool:

```python
async def run(self, arguments, progress=None):
    """Run ProteinsPlus analysis (5-60 minutes)."""

    # Step 1: Submit job
    if progress:
        await progress.set_message("Submitting job to ProteinsPlus...")

    response = requests.post(
        "https://proteins.plus/api/dogsite_rest",
        json={"dogsite": {"pdbCode": arguments["pdb_id"]}}
    )

    # Extract job location
    location = response.headers.get("location")

    # Step 2: Poll for completion
    max_polls = 360  # 60 minutes (10s interval)
    for poll in range(max_polls):
        status_resp = requests.get(location)

        # Check HTTP status
        if status_resp.status_code == 200:
            # Also check internal status_code field
            status_data = status_resp.json()
            if status_data.get("status_code") == 202:
                # Still processing
                if progress:
                    await progress.set_message(
                        f"Processing structure... (poll {poll})"
                    )
                await asyncio.sleep(10)
                continue

            # Complete!
            return {
                "data": {
                    "pockets": status_data["pockets"],
                    "pdb_id": arguments["pdb_id"]
                },
                "metadata": {
                    "polls": poll,
                    "duration_seconds": poll * 10
                }
            }

        elif status_resp.status_code == 202:
            # Still processing (HTTP level)
            if progress:
                await progress.set_message("Processing structure...")
            await asyncio.sleep(10)
            continue

        else:
            # Error
            return {
                "error": {
                    "message": f"API error: {status_resp.status_code}",
                    "error_type": "api_error"
                }
            }

    # Timeout
    return {
        "error": {
            "message": "Job timed out after 60 minutes",
            "error_type": "timeout"
        }
    }
```

**Key Features**:
- ✅ Handles both HTTP 200 and 202 status codes
- ✅ Checks internal `status_code` field
- ✅ Progress updates every 10 seconds
- ✅ Timeout after 60 minutes
- ✅ Clear error messages

---

## Checklist: Creating an Async Tool

### Code Implementation
- [ ] Add `async` keyword to `run()` method
- [ ] Add `progress: Optional[TaskProgress] = None` parameter
- [ ] Use `await asyncio.sleep()` instead of `time.sleep()`
- [ ] Check `if progress:` before calling progress methods
- [ ] Add timeout/max attempts to polling loops
- [ ] Handle all error cases
- [ ] Return proper error dict format
- [ ] Implement `get_batch_concurrency_limit()`
- [ ] Implement `handle_error()`

### Configuration JSON
- [ ] Set `"taskSupport": "required"` in execution section
- [ ] Add clear description mentioning duration
- [ ] Include `oneOf` in return_schema
- [ ] Add data wrapper in success schema
- [ ] Include error schema
- [ ] Provide real example (no placeholders)

### Testing
- [ ] Create unit test with `@pytest.mark.asyncio`
- [ ] Test successful execution
- [ ] Test error handling
- [ ] Test timeout behavior
- [ ] Test with TaskManager integration
- [ ] Verify progress updates work

### Documentation
- [ ] Add docstrings to class and methods
- [ ] Document expected duration
- [ ] Explain progress updates
- [ ] List error conditions
- [ ] Provide usage examples

---

## Summary

| Aspect | Sync Tool | Async Tool |
|--------|-----------|------------|
| **Duration** | < 5 seconds | > 5 seconds |
| **Method** | `def run(self, arguments)` | `async def run(self, arguments, progress)` |
| **Sleep** | `time.sleep()` (blocks) | `await asyncio.sleep()` (non-blocking) |
| **Progress** | None | `await progress.set_message()` |
| **Config** | `"taskSupport": "forbidden"` | `"taskSupport": "required"` |
| **MCP Behavior** | Runs directly | Runs as background task |
| **User Experience** | Waits for completion | Gets immediate task ID |
| **Testing** | Standard pytest | `@pytest.mark.asyncio` |

**Choose Async when**: Users would benefit from progress updates and non-blocking execution!

---

## Next Steps

1. Review existing async tools:
   - `src/tooluniverse/proteinsplus_tool.py`
   - `src/tooluniverse/swissdock_tool.py`

2. Read comprehensive guide:
   - `docs/MCP_TASKS_GUIDE.md`

3. Check test examples:
   - `tests/test_mcp_tasks_integration.py`

4. Try creating your own async tool!

---

**Questions?** Check the [MCP Tasks Guide](docs/MCP_TASKS_GUIDE.md) or ask in [Slack](https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ).
