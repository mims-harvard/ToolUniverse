# Guide: Creating Async Tools with MCP Tasks Support

## 📚 Complete Guide to Creating New Async Tools

This guide shows you how to create new tools that support MCP Tasks and can be tracked by TaskManager.

---

## 🎯 Overview

To create a tool that works with MCP Tasks, you need to:

1. ✅ Define the tool class with **async methods**
2. ✅ Add **progress reporting** support
3. ✅ Configure **execution.taskSupport** in JSON
4. ✅ Handle **non-blocking operations**
5. ✅ Follow **return schema** conventions

---

## 📝 Step-by-Step Guide

### Step 1: Create Async Tool Class

Create your tool class with async methods:

```python
# src/tooluniverse/my_new_tool.py

import asyncio
import httpx
from typing import Dict, Any, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from .tool_registry import register_tool

if TYPE_CHECKING:
    from .task_progress import TaskProgress


@register_tool("MyNewTool")
class MyNewTool(BaseTool):
    """
    My new tool that supports MCP Tasks.

    This tool performs long-running operations asynchronously
    with progress reporting.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        # Initialize any configuration
        self.api_url = tool_config.get("fields", {}).get("api_url", "")
        self.timeout = tool_config.get("fields", {}).get("timeout", 60)

    # ============================================================
    # MAIN ENTRY POINT - Must be async and accept progress
    # ============================================================

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional["TaskProgress"] = None
    ) -> Dict[str, Any]:
        """
        Main execution method - MUST be async!

        Args:
            arguments: Tool input parameters
            progress: Optional progress reporter (provided by TaskManager)

        Returns:
            Dict with either:
            - {"data": {...}, "metadata": {...}} for success
            - {"error": "..."} for errors
        """
        try:
            # Step 1: Validate inputs
            if progress:
                await progress.set_message("Validating inputs")

            required_param = arguments.get("required_param")
            if not required_param:
                return {"error": "required_param is missing"}

            # Step 2: Submit job to external API
            if progress:
                await progress.set_message("Submitting job to API")

            job_id = await self._submit_job(required_param)

            # Step 3: Poll for completion (non-blocking)
            if progress:
                await progress.set_message(f"Job {job_id} submitted, polling")

            result = await self._poll_until_complete(job_id, progress)

            # Step 4: Return success with data wrapper
            return {
                "data": result,
                "metadata": {
                    "job_id": job_id,
                    "source": "MyNewTool"
                }
            }

        except Exception as e:
            # Return error (no data wrapper for errors!)
            return {"error": f"Tool execution failed: {str(e)}"}

    # ============================================================
    # HELPER METHODS - All async
    # ============================================================

    async def _submit_job(self, param: str) -> str:
        """Submit job to external API (non-blocking)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/submit",
                json={"param": param}
            )

            if response.status_code != 200:
                raise RuntimeError(f"Job submission failed: {response.status_code}")

            data = response.json()
            return data["job_id"]

    async def _poll_until_complete(
        self,
        job_id: str,
        progress: Optional["TaskProgress"] = None
    ) -> Dict[str, Any]:
        """
        Poll job status until completion (non-blocking).

        CRITICAL: Use await asyncio.sleep(), NOT time.sleep()!
        """
        attempt = 0
        max_attempts = 120  # 10 minutes with 5-second intervals

        while attempt < max_attempts:
            attempt += 1

            # Check status (async HTTP request)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_url}/status/{job_id}"
                )

                if response.status_code != 200:
                    raise RuntimeError(f"Status check failed: {response.status_code}")

                data = response.json()
                status = data.get("status")

                # Update progress
                if progress:
                    await progress.set_message(
                        f"Polling job {job_id} (attempt {attempt}/{max_attempts})"
                    )

                # Check completion
                if status == "completed":
                    # Retrieve final results
                    if progress:
                        await progress.set_message("Job completed, retrieving results")
                    return data.get("result", {})

                elif status == "failed":
                    error = data.get("error", "Unknown error")
                    raise RuntimeError(f"Job failed: {error}")

                # Still running, wait and retry
                # ⚠️ CRITICAL: Use asyncio.sleep() for non-blocking!
                await asyncio.sleep(5)  # ✅ Non-blocking

        # Timeout
        raise TimeoutError(f"Job {job_id} did not complete within timeout")
```

---

### Step 2: Create Tool Configuration JSON

Create the JSON configuration file:

```json
// src/tooluniverse/data/my_new_tool.json

[
  {
    "type": "MyNewTool",
    "name": "MyNewTool_analyze_data",
    "description": "Analyze data using my new tool. This is a long-running operation that takes 5-10 minutes. Returns analysis results with insights and recommendations.",

    "parameter": {
      "type": "object",
      "required": ["required_param"],
      "properties": {
        "required_param": {
          "type": "string",
          "description": "The main input parameter for analysis"
        },
        "optional_param": {
          "type": "string",
          "description": "Optional parameter for additional configuration"
        }
      }
    },

    "fields": {
      "api_url": "https://api.example.com",
      "timeout": 60
    },

    // ============================================================
    // CRITICAL: Add execution.taskSupport configuration
    // ============================================================
    "execution": {
      "taskSupport": "required"
      // Options:
      // - "required": Tool MUST be called as task (for long operations)
      // - "optional": Tool MAY be task (variable duration)
      // - "forbidden": Tool cannot be task (instant operations)
    },

    // ============================================================
    // CRITICAL: Return schema MUST follow oneOf pattern
    // ============================================================
    "return_schema": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "data": {
              "type": "object",
              "properties": {
                "result": {
                  "type": "object",
                  "description": "Analysis results"
                },
                "insights": {
                  "type": "array",
                  "items": {
                    "type": "string"
                  }
                }
              }
            },
            "metadata": {
              "type": "object",
              "properties": {
                "job_id": {"type": "string"},
                "source": {"type": "string"}
              }
            }
          },
          "required": ["data"]
        },
        {
          "type": "object",
          "properties": {
            "error": {
              "type": "string",
              "description": "Error message if operation failed"
            }
          },
          "required": ["error"]
        }
      ]
    },

    "test_examples": [
      {
        "required_param": "test_value_123"
      }
    ]
  }
]
```

---

### Step 3: Register Tool in ToolUniverse

Add your tool to the default configuration:

```python
# src/tooluniverse/default_config.py

TOOL_FILES = {
    # ... existing tools ...
    "my_new_tool": "data/my_new_tool.json",
}
```

---

### Step 4: Test Your Tool

Create a test file:

```python
# tests/test_my_new_tool.py

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from tooluniverse.my_new_tool import MyNewTool


@pytest.fixture
def tool_config():
    return {
        "name": "MyNewTool_analyze_data",
        "type": "MyNewTool",
        "fields": {
            "api_url": "https://api.example.com",
            "timeout": 60
        }
    }


@pytest.mark.asyncio
async def test_tool_execution(tool_config):
    """Test basic tool execution."""
    tool = MyNewTool(tool_config)

    # Mock the HTTP calls
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mock responses
        mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = {
            "job_id": "test-job-123"
        }
        mock_client.return_value.__aenter__.return_value.get.return_value.json.return_value = {
            "status": "completed",
            "result": {"analysis": "complete"}
        }

        # Run tool
        result = await tool.run({"required_param": "test"})

        # Verify
        assert "data" in result
        assert result["data"]["analysis"] == "complete"


@pytest.mark.asyncio
async def test_tool_with_progress(tool_config):
    """Test tool with progress reporting."""
    from tooluniverse.task_progress import TaskProgress
    from tooluniverse.task_manager import Task
    from datetime import datetime

    tool = MyNewTool(tool_config)

    # Create mock task and progress
    task = Task(
        task_id="test-task",
        tool_name="MyNewTool_analyze_data",
        arguments={"required_param": "test"},
        status="working",
        created_at=datetime.now(),
        ttl=3600000
    )
    progress = TaskProgress(task)

    # Run with progress
    with patch('httpx.AsyncClient') as mock_client:
        # Setup mocks...
        result = await tool.run({"required_param": "test"}, progress=progress)

        # Verify progress was updated
        assert task.status_message is not None
```

---

## 🔧 Key Requirements Checklist

When creating a new async tool, ensure:

### ✅ Code Requirements

- [ ] **Class decorated with `@register_tool("ToolName")`**
- [ ] **`run()` method is `async def`**
- [ ] **`run()` accepts `progress: Optional[TaskProgress]` parameter**
- [ ] **All I/O operations use `async` (httpx, not requests)**
- [ ] **Use `await asyncio.sleep()`, NOT `time.sleep()`**
- [ ] **Import with TYPE_CHECKING for TaskProgress**
- [ ] **Return schema follows oneOf pattern**

### ✅ Configuration Requirements

- [ ] **JSON file created in `src/tooluniverse/data/`**
- [ ] **`execution.taskSupport` configured**
- [ ] **`return_schema` uses oneOf structure**
- [ ] **Success returns have `data` wrapper**
- [ ] **Errors return plain `{"error": "..."}`**
- [ ] **Tool registered in `default_config.py`**

### ✅ Return Schema Requirements

```python
# ✅ CORRECT - Success with data wrapper
return {
    "data": {"result": "..."},
    "metadata": {"source": "..."}
}

# ✅ CORRECT - Error without data wrapper
return {
    "error": "Something went wrong"
}

# ❌ WRONG - Extra fields in error
return {
    "status": "error",
    "error": "...",
    "job_id": "123"  # ❌ Violates oneOf!
}

# ❌ WRONG - No data wrapper for success
return {
    "result": "...",  # ❌ Should be wrapped in "data"
    "metadata": "..."
}
```

---

## 📊 Task Support Modes Explained

### Mode 1: `"required"` (Long Operations)

**Use for**: Operations taking > 5 seconds

```json
"execution": {
  "taskSupport": "required"
}
```

**Behavior**:
- Client MUST call with `_task` parameter
- Always returns task ID immediately
- Runs in background
- Examples: ProteinsPlus, SwissDock docking

### Mode 2: `"optional"` (Variable Duration)

**Use for**: Operations with unpredictable duration

```json
"execution": {
  "taskSupport": "optional"
}
```

**Behavior**:
- Client can choose: task mode OR direct execution
- With `_task`: Returns task ID
- Without `_task`: Executes directly and blocks
- Example: Database queries (may be instant or slow)

### Mode 3: `"forbidden"` (Instant Operations)

**Use for**: Operations taking < 1 second

```json
"execution": {
  "taskSupport": "forbidden"
}
```

**Behavior**:
- Always executes directly
- Returns result immediately
- Cannot be used as task
- Examples: Status checks, cache lookups

---

## 🎨 Progress Reporting Best Practices

### Good Progress Messages

```python
# ✅ GOOD - Clear, informative
await progress.set_message("Submitting job to API")
await progress.set_message("Job abc123 submitted, polling")
await progress.set_message("Processing data (45% complete)")
await progress.set_message("Retrieving results")

# ✅ GOOD - With percentage
await progress.set_progress(45, 100, "Analyzing structures")
# Result: "Analyzing structures (45%)"
```

### Poor Progress Messages

```python
# ❌ BAD - Too vague
await progress.set_message("Processing")

# ❌ BAD - No context
await progress.set_message("Step 3")

# ❌ BAD - Too technical
await progress.set_message("Executing HTTP POST to endpoint")
```

### Progress Update Frequency

```python
# ✅ GOOD - Update at major steps
await progress.set_message("Validating inputs")
# ... work ...
await progress.set_message("Submitting job")
# ... work ...
await progress.set_message("Polling status (attempt 5/120)")

# ❌ BAD - Too frequent (every iteration)
for i in range(10000):
    await progress.set_message(f"Processing item {i}")  # Too many updates!

# ✅ GOOD - Update periodically
for i in range(10000):
    if i % 1000 == 0:  # Every 1000 items
        await progress.set_progress(i, 10000, "Processing items")
```

---

## 🔄 Common Patterns

### Pattern 1: Submit → Poll → Retrieve

**Use case**: External API with job queue

```python
async def run(self, arguments, progress=None):
    # 1. Submit
    if progress:
        await progress.set_message("Submitting job")
    job_id = await self._submit_job(arguments)

    # 2. Poll
    if progress:
        await progress.set_message(f"Job {job_id} submitted")

    attempt = 0
    while True:
        attempt += 1
        status = await self._check_status(job_id)

        if status == "complete":
            break
        elif status == "failed":
            return {"error": "Job failed"}

        if progress:
            await progress.set_message(f"Polling (attempt {attempt})")

        await asyncio.sleep(5)  # ✅ Non-blocking

    # 3. Retrieve
    if progress:
        await progress.set_message("Retrieving results")

    results = await self._get_results(job_id)
    return {"data": results, "metadata": {"job_id": job_id}}
```

### Pattern 2: Multi-Step Processing

**Use case**: Multiple sequential operations

```python
async def run(self, arguments, progress=None):
    # Step 1: Download data
    if progress:
        await progress.set_message("Downloading data")
    data = await self._download(arguments["url"])

    # Step 2: Process data
    if progress:
        await progress.set_progress(0, 100, "Processing data")

    for i, item in enumerate(data):
        await self._process_item(item)

        # Update progress periodically
        if i % 10 == 0:
            percent = (i / len(data)) * 100
            if progress:
                await progress.set_progress(i, len(data), "Processing data")

    # Step 3: Generate report
    if progress:
        await progress.set_message("Generating report")
    report = await self._generate_report(data)

    return {"data": report}
```

### Pattern 3: Parallel Operations

**Use case**: Multiple independent tasks

```python
async def run(self, arguments, progress=None):
    # Launch multiple operations in parallel
    if progress:
        await progress.set_message("Starting parallel operations")

    tasks = [
        self._operation_1(arguments),
        self._operation_2(arguments),
        self._operation_3(arguments),
    ]

    # Wait for all to complete
    results = await asyncio.gather(*tasks)

    if progress:
        await progress.set_message("All operations complete")

    return {
        "data": {
            "result_1": results[0],
            "result_2": results[1],
            "result_3": results[2],
        }
    }
```

---

## 🚨 Common Mistakes to Avoid

### ❌ Mistake 1: Using Blocking Sleep

```python
# ❌ WRONG - Blocks entire server!
def run(self, arguments):
    time.sleep(10)  # Blocks everything!
    return {"data": "..."}

# ✅ CORRECT - Non-blocking
async def run(self, arguments):
    await asyncio.sleep(10)  # Non-blocking
    return {"data": "..."}
```

### ❌ Mistake 2: Using Synchronous HTTP

```python
# ❌ WRONG - Blocking HTTP
def run(self, arguments):
    response = requests.get(url)  # Blocks!
    return {"data": response.json()}

# ✅ CORRECT - Async HTTP
async def run(self, arguments):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # Non-blocking
    return {"data": response.json()}
```

### ❌ Mistake 3: Wrong Return Schema

```python
# ❌ WRONG - Extra fields in error
return {
    "status": "error",
    "error": "Failed",
    "job_id": "123"  # Violates oneOf!
}

# ✅ CORRECT - Clean error
return {
    "error": "Failed"
}
```

### ❌ Mistake 4: Missing Progress Parameter

```python
# ❌ WRONG - No progress parameter
async def run(self, arguments):
    return {"data": "..."}

# ✅ CORRECT - Has progress parameter
async def run(self, arguments, progress=None):
    if progress:
        await progress.set_message("Processing")
    return {"data": "..."}
```

### ❌ Mistake 5: Not Checking taskSupport

```python
# Configuration forgotten:
{
  "name": "MyTool",
  // ❌ Missing execution.taskSupport!
  "parameter": {...}
}

# ✅ CORRECT - Always specify
{
  "name": "MyTool",
  "execution": {
    "taskSupport": "required"  // or "optional" or "forbidden"
  }
}
```

---

## 🧪 Testing Your Async Tool

### Basic Test Template

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_my_new_tool():
    from tooluniverse.my_new_tool import MyNewTool

    config = {
        "name": "MyNewTool_analyze_data",
        "type": "MyNewTool",
        "fields": {"api_url": "https://api.example.com"}
    }

    tool = MyNewTool(config)

    # Mock async HTTP
    with patch('httpx.AsyncClient') as mock:
        # Setup mock
        mock_client = AsyncMock()
        mock.return_value.__aenter__.return_value = mock_client

        mock_client.post.return_value.status_code = 200
        mock_client.post.return_value.json.return_value = {"job_id": "123"}

        mock_client.get.return_value.status_code = 200
        mock_client.get.return_value.json.return_value = {
            "status": "completed",
            "result": {"data": "test"}
        }

        # Run tool
        result = await tool.run({"required_param": "test"})

        # Verify
        assert "data" in result
        assert result["data"]["data"] == "test"
```

---

## 📋 Quick Reference

### Async Tool Checklist

```python
# 1. Import requirements
import asyncio
import httpx
from typing import Dict, Any, Optional, TYPE_CHECKING
from .base_tool import BaseTool
from .tool_registry import register_tool

if TYPE_CHECKING:
    from .task_progress import TaskProgress

# 2. Register tool
@register_tool("MyToolName")
class MyTool(BaseTool):

    # 3. Async run method with progress
    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional["TaskProgress"] = None
    ) -> Dict[str, Any]:

        # 4. Report progress
        if progress:
            await progress.set_message("Starting")

        # 5. Use async I/O
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        # 6. Non-blocking sleep
        await asyncio.sleep(5)

        # 7. Return with data wrapper
        return {
            "data": result,
            "metadata": {...}
        }
```

### Configuration Checklist

```json
{
  "type": "MyToolName",
  "name": "MyToolName_operation",
  "description": "...",
  "parameter": {...},
  "fields": {...},

  "execution": {
    "taskSupport": "required"  // ✅ Must specify!
  },

  "return_schema": {
    "oneOf": [  // ✅ Must use oneOf!
      {
        "type": "object",
        "properties": {
          "data": {...},  // ✅ Success has data wrapper
          "metadata": {...}
        },
        "required": ["data"]
      },
      {
        "type": "object",
        "properties": {
          "error": {"type": "string"}  // ✅ Error is plain
        },
        "required": ["error"]
      }
    ]
  }
}
```

---

## 🎓 Summary

To create a new async tool tracked by TaskManager:

1. ✅ **Make it async**: `async def run(arguments, progress)`
2. ✅ **Use async I/O**: `httpx` instead of `requests`
3. ✅ **Non-blocking sleep**: `await asyncio.sleep()`
4. ✅ **Add progress**: Report status updates
5. ✅ **Configure taskSupport**: Specify in JSON config
6. ✅ **Follow oneOf schema**: Data wrapper for success, plain error
7. ✅ **Test it**: Create unit tests
8. ✅ **Register it**: Add to default_config.py

**Result**: Your tool will automatically work with MCP Tasks! 🎉

---

**Last Updated**: 2026-02-08
**Version**: 1.0.0
**See Also**:
- `MCP_TASKS_ARCHITECTURE.md` - System architecture
- `MCP_TASKS_IMPLEMENTATION_COMPLETE.md` - Full documentation
- `tests/test_task_manager.py` - Testing examples
