# Making Async Tool Development Easier

**Status**: Proposal
**Last Updated**: 2026-02-09
**Goal**: Reduce async tool creation from 60 minutes to 10 minutes

---

## Current Pain Points

### 1. Too Much Boilerplate
```python
# Developers write this 100 times:
class MyTool:
    def __init__(self):
        self.name = "..."
        self.description = "..."
        self.parameter = {...}  # 20 lines
        self.return_schema = {...}  # 30 lines
        self.fields = {"type": "REST"}

    async def run(self, arguments, progress=None):
        if progress:
            await progress.set_message("...")
        # ... repeat for every step
```

**Problem**: 90% of code is repetitive setup!

### 2. Polling Logic Everywhere
```python
# Everyone rewrites this pattern:
while True:
    status = check_status()
    if status["done"]:
        break
    if progress:
        await progress.set_message(...)
    await asyncio.sleep(10)
```

**Problem**: Same polling code in every tool!

### 3. Manual Progress Updates
```python
# Every tool manually checks:
if progress:
    await progress.set_message("Step 1...")
# ... 50 more lines
if progress:
    await progress.set_message("Step 2...")
```

**Problem**: Tedious and error-prone!

### 4. Complex Configuration
```json
// 50+ lines of JSON for each tool
{
  "type": "...",
  "name": "...",
  "description": "...",
  "execution": {"taskSupport": "required"},
  "parameter": { /* 20 lines */ },
  "return_schema": { /* 30 lines */ }
}
```

**Problem**: Easy to make mistakes!

---

## Proposal 1: Base Classes (Easiest Win!)

### AsyncPollingTool Base Class

**Idea**: Extract common polling pattern into base class

#### Usage (After):
```python
from tooluniverse.async_base import AsyncPollingTool

class MyAPITool(AsyncPollingTool):
    """Just implement 3 methods - that's it!"""

    name = "My_API_Tool"
    description = "Does something (5-30 minutes)"
    poll_interval = 10  # seconds
    max_duration = 3600  # 60 minutes

    # Just define parameters!
    parameter = {
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        },
        "required": ["input"]
    }

    def submit_job(self, arguments: dict) -> str:
        """Submit job and return job_id."""
        response = requests.post(
            "https://api.example.com/jobs",
            json=arguments
        )
        return response.json()["job_id"]

    def check_status(self, job_id: str) -> dict:
        """Check job status. Return {'done': bool, 'result': any, 'progress': int}."""
        response = requests.get(f"https://api.example.com/jobs/{job_id}")
        data = response.json()
        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),
            "progress": data.get("progress", 0),
            "error": data.get("error")
        }

    def format_result(self, result: any) -> dict:
        """Format final result."""
        return {"data": {"result": result}}
```

**Benefits**:
- ✅ 80% less code
- ✅ No polling logic to write
- ✅ Automatic progress reporting
- ✅ Built-in error handling
- ✅ Automatic timeout

#### Implementation:

```python
# src/tooluniverse/async_base.py
"""Base classes for async tool development."""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .task_progress import TaskProgress
from .exceptions import ToolError


class AsyncPollingTool(ABC):
    """
    Base class for async tools that poll job status.

    Subclass and implement:
    - submit_job()
    - check_status()
    - format_result()

    Everything else is handled automatically!
    """

    # Subclass must set these
    name: str
    description: str
    parameter: dict

    # Optional configuration
    poll_interval: int = 10  # seconds between polls
    max_duration: int = 3600  # max seconds before timeout
    fields: dict = {"type": "REST"}

    def __init__(self):
        # Auto-generate return_schema
        self.return_schema = self._generate_return_schema()

    @abstractmethod
    def submit_job(self, arguments: Dict[str, Any]) -> str:
        """
        Submit job to API and return job_id.

        Args:
            arguments: Tool arguments

        Returns:
            job_id as string
        """
        pass

    @abstractmethod
    def check_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check job status.

        Args:
            job_id: Job identifier

        Returns:
            {
                "done": bool,  # Is job complete?
                "result": any,  # Result if done (optional)
                "progress": int,  # Progress 0-100 (optional)
                "error": str  # Error message if failed (optional)
            }
        """
        pass

    def format_result(self, result: Any) -> Dict[str, Any]:
        """
        Format final result.

        Default implementation wraps in {"data": {...}}.
        Override to customize.
        """
        return {"data": {"result": result}}

    async def run(
        self,
        arguments: Dict[str, Any],
        progress: Optional[TaskProgress] = None
    ) -> Dict[str, Any]:
        """
        Execute tool (automatically implemented!).

        This method:
        1. Submits job
        2. Polls until complete
        3. Reports progress
        4. Handles errors
        5. Returns formatted result
        """
        try:
            # Step 1: Submit job
            if progress:
                await progress.set_message("Submitting job...")

            job_id = self.submit_job(arguments)

            if progress:
                await progress.set_message(f"Job {job_id} submitted, waiting...")

            # Step 2: Poll until complete
            result = await self._poll_until_complete(job_id, progress)

            # Step 3: Format and return
            return self.format_result(result)

        except Exception as e:
            return self.handle_error(e)

    async def _poll_until_complete(
        self,
        job_id: str,
        progress: Optional[TaskProgress]
    ) -> Any:
        """Poll job status until complete (internal)."""
        max_attempts = self.max_duration // self.poll_interval

        for attempt in range(max_attempts):
            # Check status
            status = self.check_status(job_id)

            # Check for errors
            if status.get("error"):
                raise RuntimeError(status["error"])

            # Check if done
            if status.get("done"):
                return status.get("result")

            # Update progress
            if progress:
                percent = status.get("progress", 0)
                elapsed = attempt * self.poll_interval
                msg = f"Processing... ({percent}% complete, {elapsed}s elapsed)"
                await progress.set_message(msg)

            # Wait before next poll
            await asyncio.sleep(self.poll_interval)

        # Timeout
        raise TimeoutError(
            f"Job {job_id} timed out after {self.max_duration} seconds"
        )

    def _generate_return_schema(self) -> dict:
        """Auto-generate return schema."""
        return {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
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

    def get_batch_concurrency_limit(self) -> int:
        """Default concurrency limit."""
        return 3

    def handle_error(self, exception: Exception) -> dict:
        """Default error handling."""
        return {
            "error": {
                "message": str(exception),
                "error_type": type(exception).__name__
            }
        }
```

**Impact**: Developers write **20 lines instead of 150 lines**!

---

## Proposal 2: CLI Generator

### Interactive Tool Generator

**Idea**: `tooluniverse create-async-tool` generates all boilerplate

#### Usage:
```bash
$ tooluniverse create-async-tool

🚀 ToolUniverse Async Tool Generator

Tool name: My API Tool
Tool type (rest/soap/graphql): rest
Description: Analyzes protein structures
API base URL: https://api.example.com

Does this API use job polling? (y/n): y
  Submit endpoint: /jobs
  Status endpoint: /jobs/{job_id}
  Poll interval (seconds): 10
  Max duration (seconds): 3600

Parameters:
  Add parameter (press enter when done)
  Name: protein_id
  Type (string/number/boolean/object/array): string
  Description: PDB ID of protein structure
  Required? (y/n): y

  Add parameter (press enter when done): [ENTER]

✅ Generated files:
  - src/tooluniverse/my_api_tool.py
  - src/tooluniverse/data/my_api_tools.json
  - examples/test_my_api_tool.py
  - tests/test_my_api_tool.py

📝 Next steps:
  1. Edit src/tooluniverse/my_api_tool.py (customize API calls)
  2. Add to default_config.py: "MyAPITool": "my_api_tool.MyAPITool"
  3. Test: python examples/test_my_api_tool.py
```

#### Generated Code:

**`src/tooluniverse/my_api_tool.py`**:
```python
"""Auto-generated async tool for My API Tool."""
from tooluniverse.async_base import AsyncPollingTool
import requests


class MyAPITool(AsyncPollingTool):
    """Analyzes protein structures."""

    name = "My_API_Tool"
    description = "Analyzes protein structures (estimated 5-60 minutes)"
    poll_interval = 10
    max_duration = 3600

    parameter = {
        "type": "object",
        "properties": {
            "protein_id": {
                "type": "string",
                "description": "PDB ID of protein structure"
            }
        },
        "required": ["protein_id"]
    }

    def __init__(self):
        super().__init__()
        self.api_url = "https://api.example.com"

    def submit_job(self, arguments):
        """TODO: Customize API call."""
        response = requests.post(
            f"{self.api_url}/jobs",
            json=arguments
        )
        response.raise_for_status()
        return response.json()["job_id"]

    def check_status(self, job_id):
        """TODO: Customize status check."""
        response = requests.get(f"{self.api_url}/jobs/{job_id}")
        response.raise_for_status()
        data = response.json()

        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),
            "progress": data.get("progress", 0),
            "error": data.get("error")
        }
```

**Benefits**:
- ✅ 5-minute setup
- ✅ No copy-paste errors
- ✅ Consistent structure
- ✅ Test files included

---

## Proposal 3: Decorators for Progress

### Auto-Progress Decorator

**Idea**: Automatically report progress without manual checks

#### Usage:
```python
from tooluniverse.decorators import with_progress, poll_until_complete

class MyTool(AsyncPollingTool):

    @with_progress("Submitting job...")
    def submit_job(self, arguments):
        response = requests.post(...)
        return response.json()["job_id"]

    @poll_until_complete(interval=10, timeout=3600)
    async def wait_for_result(self, job_id):
        """This decorator handles ALL polling logic!"""
        response = requests.get(f"/jobs/{job_id}")
        data = response.json()

        # Return None to continue polling
        if data["status"] == "processing":
            return None

        # Return result to complete
        return data["result"]
```

#### Implementation:

```python
# src/tooluniverse/decorators.py
"""Decorators for async tool development."""
import asyncio
from functools import wraps
from typing import Callable, Optional


def with_progress(message: str):
    """Auto-report progress before function execution."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if hasattr(self, '_progress') and self._progress:
                await self._progress.set_message(message)
            return await func(self, *args, **kwargs) if asyncio.iscoroutinefunction(func) else func(self, *args, **kwargs)
        return wrapper
    return decorator


def poll_until_complete(interval: int = 10, timeout: int = 3600):
    """
    Auto-poll a function until it returns non-None.

    Function should:
    - Return None to continue polling
    - Return result to complete
    - Raise exception on error
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            max_attempts = timeout // interval

            for attempt in range(max_attempts):
                result = await func(self, *args, **kwargs) if asyncio.iscoroutinefunction(func) else func(self, *args, **kwargs)

                if result is not None:
                    return result

                # Update progress
                if hasattr(self, '_progress') and self._progress:
                    elapsed = attempt * interval
                    await self._progress.set_message(
                        f"Polling... ({elapsed}s elapsed)"
                    )

                await asyncio.sleep(interval)

            raise TimeoutError(f"Polling timed out after {timeout} seconds")

        return wrapper
    return decorator
```

**Benefits**:
- ✅ No manual progress checks
- ✅ Cleaner code
- ✅ Less boilerplate

---

## Proposal 4: OpenAPI/Swagger Generator

### Auto-Generate from API Specs

**Idea**: Parse OpenAPI spec and generate tools automatically

#### Usage:
```bash
$ tooluniverse generate-from-openapi https://api.example.com/openapi.json

🔍 Found 15 endpoints in API spec
📊 Detected 3 async operations (long-running jobs)

Generating tools:
  ✓ MyAPI_analyze_protein (async)
  ✓ MyAPI_predict_structure (async)
  ✓ MyAPI_get_protein_info (sync)
  ... 12 more

✅ Generated 15 tools in src/tooluniverse/myapi_tools.py

Next steps:
  1. Review generated code
  2. Customize polling logic if needed
  3. Add API key configuration
  4. Test tools
```

**Benefits**:
- ✅ Zero manual coding for standard APIs
- ✅ Automatic parameter validation
- ✅ Consistent with API docs

---

## Proposal 5: Testing Utilities

### Easy Async Testing

**Idea**: Provide utilities for testing async tools

#### Usage:
```python
from tooluniverse.testing import AsyncToolTester, MockAsyncAPI

# Create mock API
mock_api = MockAsyncAPI()
mock_api.add_job_response("job123", {
    "status": "processing",
    "progress": 50
}, delay=5)
mock_api.add_job_response("job123", {
    "status": "completed",
    "result": {"answer": 42}
}, delay=10)

# Test tool with mock
tester = AsyncToolTester(MyAPITool)
result = await tester.run(
    arguments={"input": "test"},
    mock_api=mock_api,
    assert_progress=True  # Verify progress updates
)

assert result["data"]["answer"] == 42
tester.assert_progress_updated(times=2)
tester.assert_completed_in(seconds=15)
```

#### Implementation:

```python
# src/tooluniverse/testing.py
"""Testing utilities for async tools."""
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch


class MockAsyncAPI:
    """Mock async API for testing."""

    def __init__(self):
        self.job_responses: Dict[str, List[dict]] = {}
        self.call_count = 0

    def add_job_response(self, job_id: str, response: dict, delay: int = 0):
        """Add a response for a job ID."""
        if job_id not in self.job_responses:
            self.job_responses[job_id] = []
        self.job_responses[job_id].append({
            "response": response,
            "delay": delay
        })

    async def get_status(self, job_id: str) -> dict:
        """Mock status check."""
        self.call_count += 1

        if job_id not in self.job_responses:
            raise ValueError(f"Unknown job: {job_id}")

        responses = self.job_responses[job_id]
        if not responses:
            raise ValueError(f"No more responses for {job_id}")

        response_data = responses.pop(0)
        await asyncio.sleep(response_data["delay"])
        return response_data["response"]


class AsyncToolTester:
    """Test helper for async tools."""

    def __init__(self, tool_class):
        self.tool = tool_class()
        self.progress_updates: List[str] = []

    async def run(
        self,
        arguments: dict,
        mock_api: Optional[MockAsyncAPI] = None,
        assert_progress: bool = False
    ) -> dict:
        """Run tool with mock progress tracking."""

        # Mock progress
        mock_progress = Mock()

        async def capture_progress(msg):
            self.progress_updates.append(msg)

        mock_progress.set_message = capture_progress

        # Patch API if provided
        if mock_api:
            with patch.object(self.tool, 'check_status', mock_api.get_status):
                result = await self.tool.run(arguments, progress=mock_progress)
        else:
            result = await self.tool.run(arguments, progress=mock_progress)

        if assert_progress:
            assert len(self.progress_updates) > 0, "No progress updates!"

        return result

    def assert_progress_updated(self, times: int):
        """Assert progress was updated N times."""
        assert len(self.progress_updates) >= times, \
            f"Expected {times} progress updates, got {len(self.progress_updates)}"

    def assert_completed_in(self, seconds: int):
        """Assert tool completed within time limit."""
        # Would need timing tracking in run()
        pass
```

**Benefits**:
- ✅ Easy to test without real APIs
- ✅ Verify progress reporting
- ✅ Test timeout scenarios

---

## Proposal 6: Documentation Generator

### Auto-Generate User Docs

**Idea**: Generate docs from tool code

#### Usage:
```bash
$ tooluniverse generate-docs src/tooluniverse/my_api_tool.py

📝 Generating documentation...

✅ Created:
  - docs/my_api_tool.md (user guide)
  - docs/my_api_tool_api.md (API reference)
  - examples/my_api_tool_examples.py (code examples)
```

**Generated `docs/my_api_tool.md`**:
````markdown
# My API Tool

Analyzes protein structures using async processing.

## Usage

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Run analysis (takes 5-60 minutes)
result = await tu.tools.My_API_Tool(protein_id="2OZR")

print(result["data"]["analysis"])
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| protein_id | string | Yes | PDB ID of protein structure |

## Returns

```json
{
  "data": {
    "analysis": {...}
  }
}
```

## Notes

- Operation takes 5-60 minutes
- Runs as background task in MCP clients
- Progress updates every 10 seconds
````

**Benefits**:
- ✅ Consistent documentation
- ✅ Always up-to-date
- ✅ Less manual work

---

## Proposal 7: Visual Builder (Advanced)

### Web UI for Tool Creation

**Idea**: Visual interface for building tools

```
┌─────────────────────────────────────────┐
│  ToolUniverse Tool Builder              │
├─────────────────────────────────────────┤
│                                         │
│  Tool Name: [My API Tool            ]  │
│  Type: [REST ▼]  Async: [✓]           │
│                                         │
│  API Base URL:                          │
│  [https://api.example.com           ]  │
│                                         │
│  ┌──────── Endpoints ────────┐        │
│  │ Submit: [/jobs          ]  │        │
│  │ Status: [/jobs/{id}     ]  │        │
│  │ Result: [/jobs/{id}     ]  │        │
│  └────────────────────────────┘        │
│                                         │
│  ┌──────── Parameters ────────┐       │
│  │ ├ protein_id (string) *     │       │
│  │ └ options (object)          │       │
│  │   [+ Add Parameter]         │       │
│  └────────────────────────────┘        │
│                                         │
│  ┌──────── Testing ────────────┐      │
│  │ Test Endpoint: [Test ▶]     │       │
│  │ Status: ✓ Connected          │       │
│  └────────────────────────────┘        │
│                                         │
│  [Cancel]  [Generate Code ▶]           │
└─────────────────────────────────────────┘
```

**Benefits**:
- ✅ Non-programmers can create tools
- ✅ Visual API testing
- ✅ Immediate feedback

---

## Implementation Roadmap

### Phase 1: Quick Wins (1 week)

**Priority 1: Base Classes**
- [ ] Create `AsyncPollingTool` base class
- [ ] Add examples
- [ ] Update documentation
- [ ] Test with 3 existing tools

**Effort**: 2 days
**Impact**: 🟢 High (80% less code!)

---

### Phase 2: Developer Tools (2 weeks)

**Priority 2: CLI Generator**
- [ ] Build interactive prompts
- [ ] Template system
- [ ] Code generation
- [ ] Test file generation

**Effort**: 1 week
**Impact**: 🟢 High (5-minute setup!)

**Priority 3: Testing Utilities**
- [ ] `MockAsyncAPI` class
- [ ] `AsyncToolTester` class
- [ ] Example tests

**Effort**: 3 days
**Impact**: 🟡 Medium (easier testing)

---

### Phase 3: Advanced Features (1 month)

**Priority 4: Decorators**
- [ ] `@with_progress` decorator
- [ ] `@poll_until_complete` decorator
- [ ] Documentation

**Effort**: 3 days
**Impact**: 🟡 Medium (cleaner code)

**Priority 5: OpenAPI Generator**
- [ ] Parse OpenAPI specs
- [ ] Detect async operations
- [ ] Generate tool classes

**Effort**: 1 week
**Impact**: 🟢 High (for API-heavy users)

**Priority 6: Doc Generator**
- [ ] Extract metadata from code
- [ ] Generate markdown docs
- [ ] Generate examples

**Effort**: 5 days
**Impact**: 🟡 Medium

---

### Phase 4: Visual Tools (3 months)

**Priority 7: Web UI Builder**
- [ ] React frontend
- [ ] API testing interface
- [ ] Code generation backend

**Effort**: 2-3 months
**Impact**: 🟢 High (democratizes tool creation)

---

## Comparison: Before vs After

### Current (Manual)

```python
# 150 lines of boilerplate
class MyTool:
    def __init__(self):
        self.name = "..."
        self.description = "..."
        self.parameter = {...}  # 20 lines
        self.return_schema = {...}  # 30 lines

    async def run(self, arguments, progress=None):
        if progress:
            await progress.set_message("...")

        job_id = self._submit_job(arguments)

        while True:
            status = self._check_status(job_id)
            if status["done"]:
                break
            if progress:
                await progress.set_message(...)
            await asyncio.sleep(10)

        return {"data": status["result"]}

    def _submit_job(self, arguments):
        # ...

    def _check_status(self, job_id):
        # ...

    def get_batch_concurrency_limit(self):
        return 3

    def handle_error(self, exception):
        return {...}
```

**Time**: 60 minutes

---

### With Base Class

```python
# 20 lines - focus on YOUR logic!
from tooluniverse.async_base import AsyncPollingTool

class MyTool(AsyncPollingTool):
    name = "My_Tool"
    description = "Does something (5-30 minutes)"
    poll_interval = 10
    max_duration = 3600

    parameter = {
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        },
        "required": ["input"]
    }

    def submit_job(self, arguments):
        response = requests.post("https://api.example.com/jobs", json=arguments)
        return response.json()["job_id"]

    def check_status(self, job_id):
        response = requests.get(f"https://api.example.com/jobs/{job_id}")
        data = response.json()
        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),
            "progress": data.get("progress", 0)
        }
```

**Time**: 10 minutes!

---

### With CLI Generator

```bash
$ tooluniverse create-async-tool
# Answer 5 questions
# Get complete working tool!
```

**Time**: 5 minutes!

---

## Summary: Proposed Improvements

| Proposal | Complexity | Impact | Time to Implement | Priority |
|----------|-----------|---------|-------------------|----------|
| **Base Classes** | 🟢 Low | 🟢 Very High | 2 days | P1 ⭐⭐⭐ |
| **CLI Generator** | 🟡 Medium | 🟢 High | 1 week | P2 ⭐⭐ |
| **Testing Utilities** | 🟢 Low | 🟡 Medium | 3 days | P2 ⭐⭐ |
| **Decorators** | 🟢 Low | 🟡 Medium | 3 days | P3 ⭐ |
| **OpenAPI Generator** | 🟡 Medium | 🟢 High | 1 week | P3 ⭐ |
| **Doc Generator** | 🟡 Medium | 🟡 Medium | 5 days | P3 ⭐ |
| **Visual Builder** | 🔴 High | 🟢 High | 2-3 months | P4 |

---

## Recommendation

### Start with Phase 1: Base Classes (2 days)

**Why**:
- ✅ Easiest to implement
- ✅ Biggest impact (80% less code)
- ✅ No new dependencies
- ✅ Backwards compatible

**Next Steps**:
1. Create `AsyncPollingTool` base class
2. Convert 2-3 existing tools to use it
3. Update documentation
4. Get community feedback

**Then**: Add CLI generator (Phase 2) based on user feedback

---

## What Do You Think?

Which proposals would help you most?
1. Base classes (less boilerplate)?
2. CLI generator (quick setup)?
3. Testing utilities (easier testing)?
4. OpenAPI generator (auto-generate from specs)?
5. Something else?

Let me know and I can start implementing! 🚀
