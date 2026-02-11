# Converting Async Tools to AsyncPollingTool: Complete Guide

**Date**: 2026-02-09
**Status**: ✅ Production Ready

---

## 📋 Table of Contents

1. [Why Convert?](#why-convert)
2. [When to Use AsyncPollingTool](#when-to-use-asyncpollingtool)
3. [Conversion Pattern](#conversion-pattern)
4. [Real Examples](#real-examples)
   - [Example 1: ProteinsPlus (Simple Polling)](#example-1-proteinsplus)
   - [Example 2: SwissDock (Complex Multi-Step)](#example-2-swissdock)
5. [Common Patterns](#common-patterns)
6. [Migration Checklist](#migration-checklist)
7. [Troubleshooting](#troubleshooting)

---

## Why Convert?

### Before AsyncPollingTool (Manual Implementation)

**Typical async tool code: ~150-275 lines**

```python
class MyAsyncTool(BaseTool):
    async def run(self, arguments, progress=None):
        # Validation (10 lines)
        if not arguments.get("required_param"):
            return {"error": "Missing parameter"}

        # Submit job (20 lines)
        response = await self._submit_job(arguments)
        job_id = self._extract_job_id(response)

        # ❌ MANUAL POLLING LOOP (40+ lines of boilerplate)
        max_attempts = self.max_wait_time // self.poll_interval
        for attempt in range(max_attempts):
            if progress:
                await progress.set_message(f"Polling... (attempt {attempt})")

            status = await self._check_status(job_id)

            if status["done"]:
                return self._format_results(status["data"])

            await asyncio.sleep(self.poll_interval)  # ❌ Manual sleep

        # ❌ TIMEOUT HANDLING (10 lines)
        return {"error": "Job timed out"}
```

**Problems:**
- ❌ 40+ lines of repetitive polling boilerplate
- ❌ Timeout logic duplicated across tools
- ❌ Progress updates scattered throughout
- ❌ Error handling inconsistent
- ❌ Hard to maintain and test

### After AsyncPollingTool (Base Class)

**Same tool with base class: ~20-55 lines**

```python
class MyAsyncTool(AsyncPollingTool):
    name = "My_Async_Tool"
    description = "Analyzes data (5-30 minutes)"
    poll_interval = 10
    max_duration = 3600

    parameter = {
        "type": "object",
        "properties": {
            "required_param": {"type": "string"}
        },
        "required": ["required_param"]
    }

    def submit_job(self, arguments):
        """Just YOUR job submission logic!"""
        response = requests.post(API_URL, json=arguments)
        return response.json()["job_id"]

    def check_status(self, job_id):
        """Just YOUR status check logic!"""
        response = requests.get(f"{API_URL}/jobs/{job_id}")
        data = response.json()
        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),
            "progress": data.get("progress", 0)
        }
```

**Benefits:**
- ✅ **87% less code** (150 → 20 lines)
- ✅ **No polling boilerplate** - handled automatically
- ✅ **Automatic progress reporting** - just focus on your API
- ✅ **Consistent behavior** - all tools work the same way
- ✅ **Easier to test** - mock just 2 methods instead of entire workflow
- ✅ **Auto-generated schemas** - no manual oneOf definitions

---

## When to Use AsyncPollingTool

### ✅ Perfect For

**Job-based APIs with polling pattern:**
1. Submit job → get job_id
2. Poll status until complete
3. Retrieve results

**Examples:**
- Molecular docking (SwissDock, AutoDock)
- Protein structure prediction (AlphaFold, ESMFold)
- Binding site analysis (ProteinsPlus DoGSite)
- Sequence alignment (BLAST, HMMER)
- Virtual screening
- Molecular dynamics simulations
- Any computational job taking >30 seconds

### ❌ Not Suitable For

**Instant operations:**
- Database lookups (PubChem, UniProt search)
- Simple calculations (< 1 second)
- File downloads
- Data transformations

**Streaming operations:**
- Real-time data feeds
- WebSocket connections
- Server-sent events
- Use `AsyncStreamingTool` instead

**Complex state machines:**
- Multi-phase workflows with user input
- Jobs requiring intermediate approvals
- Workflows with branching logic

---

## Conversion Pattern

### Step 1: Identify the Polling Loop

Look for this pattern in your existing code:

```python
# ❌ BEFORE (manual polling)
async def run(self, arguments, progress=None):
    # Submit job
    job_id = await self._submit_job(arguments)

    # ❌ THIS IS THE BOILERPLATE TO REPLACE
    for attempt in range(max_attempts):
        status = await self._check_status(job_id)
        if status["done"]:
            return status["result"]
        await asyncio.sleep(poll_interval)

    raise TimeoutError("Job timed out")
```

### Step 2: Extract Two Core Methods

Split your code into two focused methods:

**Method 1: submit_job()**
- Everything BEFORE the polling loop
- Job submission
- Parameter validation
- Returns: job_id (string)

**Method 2: check_status()**
- Everything INSIDE the polling loop
- Status checking
- Result retrieval
- Returns: dict with `{"done": bool, "result": any, "progress": int}`

### Step 3: Convert to AsyncPollingTool

```python
from tooluniverse.async_base import AsyncPollingTool

class YourTool(AsyncPollingTool):
    # ✅ STEP 3A: Define class attributes
    name = "Your_Tool_Name"
    description = "What it does (expected time)"
    poll_interval = 10  # seconds between checks
    max_duration = 3600  # timeout in seconds

    # ✅ STEP 3B: Define parameters
    parameter = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            # ... your parameters
        },
        "required": ["param1"]
    }

    # ✅ STEP 3C: Implement submit_job()
    def submit_job(self, arguments):
        """Just YOUR job submission logic"""
        # Extract from your old run() method
        # Everything BEFORE the polling loop
        response = requests.post(API_URL, json=arguments)
        return response.json()["job_id"]

    # ✅ STEP 3D: Implement check_status()
    def check_status(self, job_id):
        """Just YOUR status check logic"""
        # Extract from your old polling loop
        response = requests.get(f"{API_URL}/jobs/{job_id}")
        data = response.json()

        return {
            "done": data["status"] == "completed",
            "result": data.get("result"),  # Required if done=True
            "progress": data.get("progress", 0),  # Optional
            "error": data.get("error")  # Optional
        }

    # ✅ STEP 3E: Optional - customize result format
    def format_result(self, result):
        """Optional: customize output format"""
        return {
            "data": result,
            "metadata": {"tool": self.name}
        }
```

### Step 4: Remove Old Code

Delete from your class:
- ❌ Manual polling loop
- ❌ Timeout management
- ❌ Progress update logic
- ❌ `return_schema` definition
- ❌ `get_batch_concurrency_limit()` (unless custom)
- ❌ `handle_error()` (unless custom)

That's it! The base class handles everything else.

---

## Real Examples

### Example 1: ProteinsPlus (Simple Polling)

**Original Implementation: ~240 lines**

```python
class ProteinsPlusOriginal:
    def __init__(self):
        self.name = "ProteinsPlus_Predict_Binding_Sites"
        self.poll_interval = 10
        self.max_wait_time = 1800

        # 30 lines of parameter definition
        self.parameter = {...}

        # 30 lines of return_schema
        self.return_schema = {
            "oneOf": [
                {"type": "object", "properties": {"data": {...}}},
                {"type": "object", "properties": {"error": {...}}}
            ]
        }

    async def run(self, arguments, progress=None):
        try:
            # Submit job (20 lines)
            if progress:
                await progress.set_message("Submitting job...")

            payload = {"dogsite": {"pdbCode": arguments["pdb_id"]}}
            response = await client.post(API_URL, json=payload)
            job_location = response.headers.get("location")

            # ❌ MANUAL POLLING (80 lines of boilerplate)
            max_polls = self.max_wait_time // self.poll_interval
            for poll_num in range(max_polls):
                await asyncio.sleep(self.poll_interval)

                status_response = await client.get(job_location)

                if status_response.status_code == 202:
                    if progress:
                        await progress.set_message(f"Processing... (poll #{poll_num})")
                    continue

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("status_code") == 202:
                        continue

                    return {
                        "data": {"pockets": status_data.get("pockets")},
                        "metadata": {"tool": self.name}
                    }

                return {"error": f"Failed with status {status_response.status_code}"}

            # ❌ TIMEOUT HANDLING
            return {"error": "Job timed out"}

        except Exception as e:
            return {"error": str(e)}
```

**With AsyncPollingTool: ~71 lines**

```python
class ProteinsPlusSimplified(AsyncPollingTool):
    name = "ProteinsPlus_Predict_Binding_Sites"
    description = "Predict protein binding sites (5-60 minutes)"
    poll_interval = 10
    max_duration = 3600

    parameter = {
        "type": "object",
        "properties": {
            "pdb_id": {
                "type": "string",
                "pattern": "^[0-9][A-Za-z0-9]{3}$"
            }
        },
        "required": ["pdb_id"]
    }

    def __init__(self):
        super().__init__()
        self.base_url = "https://proteins.plus/api"

    def submit_job(self, arguments):
        """Just the job submission logic - 20 lines!"""
        payload = {"dogsite": {"pdbCode": arguments["pdb_id"]}}

        response = requests.post(
            f"{self.base_url}/dogsite_rest",
            json=payload,
            headers={"Accept": "application/json"}
        )

        if response.status_code != 202:
            raise RuntimeError(f"Job submission failed: {response.status_code}")

        job_location = response.headers.get("location")
        if not job_location:
            raise RuntimeError("No job location in response")

        return job_location  # Job location URL is the job_id

    def check_status(self, job_id):
        """Just the status check logic - 20 lines!"""
        response = requests.get(job_id, headers={"Accept": "application/json"})

        # ProteinsPlus uses HTTP 202 for "still processing"
        if response.status_code == 202:
            return {"done": False, "progress": 0}

        if response.status_code != 200:
            return {"done": True, "error": f"HTTP {response.status_code}"}

        status_data = response.json()

        # Check internal status_code field (ProteinsPlus specific)
        if status_data.get("status_code") == 202:
            return {"done": False, "progress": 50}

        # Job complete!
        return {
            "done": True,
            "result": status_data.get("pockets", []),
            "progress": 100
        }
```

**Results:**
- ✅ 240 → 71 lines = **70% reduction**
- ✅ No polling boilerplate
- ✅ No timeout management
- ✅ No manual progress updates
- ✅ Auto-generated return_schema

---

### Example 2: SwissDock (Complex Multi-Step)

**Original Implementation: ~275 lines**

```python
class SwissDockOriginal:
    MAX_POLL_ATTEMPTS = 120
    POLL_INTERVAL = 5

    async def run(self, arguments, progress=None):
        try:
            # Server check (10 lines)
            if not await self._check_server_status():
                return {"error": "Server not responding"}

            # Validation (20 lines)
            ligand_smiles = arguments.get("ligand_smiles")
            pdb_id = arguments.get("pdb_id")
            if not ligand_smiles or not pdb_id:
                return {"error": "Missing parameters"}

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Step 1: Prepare ligand (15 lines + error handling)
            if progress:
                await progress.set_message("Preparing ligand...")
            ligand_result = await self._prepare_ligand(session_id, ligand_smiles)
            if not ligand_result["success"]:
                return {"error": ligand_result["error"]}

            # Step 2: Prepare target (15 lines + error handling)
            if progress:
                await progress.set_message("Preparing target...")
            target_result = await self._prepare_target(session_id, pdb_id)
            if not target_result["success"]:
                return {"error": target_result["error"]}

            # Step 3: Set parameters (15 lines + error handling)
            if progress:
                await progress.set_message("Setting parameters...")
            param_result = await self._set_parameters(session_id, ...)
            if not param_result["success"]:
                return {"error": param_result["error"]}

            # Step 4: Start docking (15 lines + error handling)
            if progress:
                await progress.set_message("Starting docking...")
            start_result = await self._start_docking(session_id)
            if not start_result["success"]:
                return {"error": start_result["error"]}

            # ❌ STEP 5: MANUAL POLLING (40 lines of boilerplate)
            for attempt in range(self.MAX_POLL_ATTEMPTS):
                if progress:
                    await progress.set_message(f"Polling... ({attempt+1}/{self.MAX_POLL_ATTEMPTS})")

                status = await self._check_status(session_id)

                if status["status"] == "FINISHED":
                    if progress:
                        await progress.set_message("Retrieving results...")
                    results = await self._retrieve_results(session_id)
                    return {"data": results}

                elif status["status"] == "ERROR":
                    return {"error": "Docking failed"}

                elif status["status"] == "RUNNING":
                    await asyncio.sleep(self.POLL_INTERVAL)  # ❌ Manual sleep

            # ❌ TIMEOUT HANDLING
            return {
                "data": {
                    "session_id": session_id,
                    "message": "Still running, check later"
                }
            }

        except Exception as e:
            return {"error": str(e)}
```

**With AsyncPollingTool: ~183 lines**

```python
class SwissDockSimplified(AsyncPollingTool):
    name = "SwissDock_Dock_Ligand"
    description = "Protein-ligand docking (5-10 minutes)"
    poll_interval = 5
    max_duration = 600

    parameter = {
        "type": "object",
        "properties": {
            "ligand_smiles": {"type": "string"},
            "pdb_id": {"type": "string", "pattern": "^[0-9A-Za-z]{4}$"},
            "exhaustiveness": {"type": "integer", "default": 8}
        },
        "required": ["ligand_smiles", "pdb_id"]
    }

    def __init__(self):
        super().__init__()
        self.timeout = 60

    def submit_job(self, arguments):
        """Multi-step workflow - just YOUR logic! ~30 lines"""
        loop = asyncio.get_event_loop()

        # Validate
        ligand_smiles = arguments.get("ligand_smiles")
        pdb_id = arguments.get("pdb_id")
        if not ligand_smiles or not pdb_id:
            raise ValueError("Missing required parameters")

        # Check server
        if not loop.run_until_complete(self._check_server_status()):
            raise RuntimeError("Server not responding")

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Execute workflow (exceptions raised, not error dicts)
        loop.run_until_complete(self._prepare_ligand(session_id, ligand_smiles))
        loop.run_until_complete(self._prepare_target(session_id, pdb_id))
        loop.run_until_complete(self._set_parameters(session_id, arguments))
        loop.run_until_complete(self._start_docking(session_id))

        return session_id  # Return job_id for polling

    def check_status(self, job_id):
        """Status check + result retrieval - just YOUR logic! ~25 lines"""
        loop = asyncio.get_event_loop()

        async def _async_check():
            # Check status
            url = f"{SWISSDOCK_BASE_URL}/checkstatus"
            params = {"sessionNumber": job_id}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)

                if response.status_code != 200:
                    return {"done": False, "error": f"HTTP {response.status_code}"}

                status_text = response.text.strip().upper()

                # Job complete - retrieve results
                if "COMPLETE" in status_text or "FINISHED" in status_text:
                    results = await self._retrieve_results(job_id)
                    return {"done": True, "result": results, "progress": 100}

                # Job failed
                elif "ERROR" in status_text or "FAIL" in status_text:
                    return {"done": False, "error": "Docking failed"}

                # Still running
                else:
                    return {"done": False, "progress": 50}

        return loop.run_until_complete(_async_check())
```

**Results:**
- ✅ 275 → 183 lines = **33% reduction**
- ✅ Complex multi-step workflow simplified
- ✅ No polling boilerplate (40 lines eliminated)
- ✅ No timeout handling (10 lines eliminated)
- ✅ Cleaner separation of concerns

---

## Common Patterns

### Pattern 1: HTTP Status Codes for Polling

Many APIs use HTTP status codes to indicate job status:

```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")

    # Common patterns:
    if response.status_code == 202:  # Still processing
        return {"done": False, "progress": 0}

    elif response.status_code == 200:  # Complete
        return {"done": True, "result": response.json(), "progress": 100}

    elif response.status_code == 404:  # Not found
        return {"done": False, "error": "Job not found"}

    else:  # Error
        return {"done": False, "error": f"HTTP {response.status_code}"}
```

### Pattern 2: Status Field in Response

Some APIs return status in JSON:

```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    status = data.get("status", "").lower()

    if status in ("completed", "success", "finished"):
        return {"done": True, "result": data.get("result"), "progress": 100}

    elif status in ("running", "processing", "queued"):
        progress = data.get("progress", 0)
        return {"done": False, "progress": progress}

    elif status in ("failed", "error"):
        return {"done": False, "error": data.get("error", "Unknown error")}

    else:
        # Unknown status, assume still running
        return {"done": False, "progress": 0}
```

### Pattern 3: Location Header for Job URL

Jobs that return a location header:

```python
def submit_job(self, arguments):
    response = requests.post(API_URL, json=arguments)

    if response.status_code != 202:
        raise RuntimeError(f"Job submission failed: {response.status_code}")

    # Get job location from header
    job_url = response.headers.get("location")
    if not job_url:
        # Fallback: extract job_id from response
        job_id = response.json().get("job_id")
        job_url = f"{API_URL}/jobs/{job_id}"

    return job_url  # Return URL as job_id
```

### Pattern 4: Multi-Step Workflow

Complex workflows with multiple preparation steps:

```python
def submit_job(self, arguments):
    """Multi-step: prepare → configure → start → return ID"""

    # Step 1: Prepare input
    prep_response = requests.post(f"{API_URL}/prepare", json=arguments)
    session_id = prep_response.json()["session_id"]

    # Step 2: Configure
    config_response = requests.post(
        f"{API_URL}/configure",
        json={"session_id": session_id, "params": arguments}
    )

    # Step 3: Start job
    start_response = requests.post(
        f"{API_URL}/start",
        json={"session_id": session_id}
    )

    if start_response.status_code != 200:
        raise RuntimeError("Job start failed")

    return session_id
```

### Pattern 5: Progress Percentage

APIs that provide progress information:

```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    status = data.get("status")

    if status == "completed":
        return {"done": True, "result": data.get("result"), "progress": 100}

    elif status == "running":
        # Extract progress percentage
        progress = data.get("progress_percent", 0)
        return {"done": False, "progress": progress}

    else:
        return {"done": False, "error": "Unknown status"}
```

---

## Migration Checklist

Use this checklist when converting an existing async tool:

### ✅ Pre-Conversion

- [ ] Read the current implementation thoroughly
- [ ] Identify the polling loop (usually in `run()` method)
- [ ] Note any complex workflows or multi-step submissions
- [ ] Check for custom error handling or result formatting
- [ ] Review existing tests to understand expected behavior

### ✅ Conversion Steps

- [ ] Create new class inheriting from `AsyncPollingTool`
- [ ] Set class attributes: `name`, `description`, `poll_interval`, `max_duration`
- [ ] Copy `parameter` definition (remove `return_schema`)
- [ ] Extract job submission logic → `submit_job()` method
- [ ] Extract status check logic → `check_status()` method
- [ ] Add custom `format_result()` if needed (optional)
- [ ] Add custom `handle_error()` if needed (optional)
- [ ] Remove old polling loop code
- [ ] Remove old timeout management code
- [ ] Remove old progress update code

### ✅ Testing

- [ ] Write unit tests for `submit_job()` alone
- [ ] Write unit tests for `check_status()` alone
- [ ] Test the complete workflow with mocked API
- [ ] Test timeout behavior (set low `max_duration`)
- [ ] Test error handling (job failure, network errors)
- [ ] Test progress reporting (check messages)
- [ ] Compare behavior with original implementation

### ✅ Documentation

- [ ] Update tool docstrings to mention expected duration
- [ ] Document any special requirements or limitations
- [ ] Add examples to README or documentation
- [ ] Update API documentation with new structure

---

## Troubleshooting

### Issue 1: "submit_job() is blocking"

**Problem:**
```python
def submit_job(self, arguments):
    # ❌ This will block the event loop
    result = await self._async_helper(arguments)
    return result
```

**Solution:** Use `asyncio.run()` or get the event loop:
```python
def submit_job(self, arguments):
    # ✅ Run async code in sync context
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(self._async_helper(arguments))
    return result
```

Or use `requests` instead of `httpx` for simplicity:
```python
def submit_job(self, arguments):
    # ✅ Sync HTTP calls work fine
    response = requests.post(API_URL, json=arguments)
    return response.json()["job_id"]
```

### Issue 2: "Job never completes"

**Problem:**
```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    # ❌ Missing "done": True in any case
    if data["status"] == "running":
        return {"done": False}
    # Forgot to handle "completed" status!
```

**Solution:** Always handle all status cases:
```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    status = data.get("status", "").lower()

    # ✅ Explicit handling of all cases
    if status in ("completed", "success", "finished"):
        return {"done": True, "result": data.get("result"), "progress": 100}
    elif status in ("running", "processing"):
        return {"done": False, "progress": 50}
    elif status in ("failed", "error"):
        return {"done": False, "error": data.get("error")}
    else:
        # Unknown status - log and treat as running
        print(f"Unknown status: {status}")
        return {"done": False, "progress": 0}
```

### Issue 3: "Missing result on completion"

**Problem:**
```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    if data["status"] == "completed":
        # ❌ Missing "result" key!
        return {"done": True, "progress": 100}
```

**Solution:** Always include `result` when `done=True`:
```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    if data["status"] == "completed":
        # ✅ Include result
        return {
            "done": True,
            "result": data.get("result", {}),  # Default to empty dict
            "progress": 100
        }
```

### Issue 4: "TypeError: 'float' object cannot be interpreted as an integer"

**Problem:**
```python
poll_interval = 0.1  # For fast testing
max_duration = 10
```

**Solution:** Already fixed in base class, but ensure your config uses integers or the base class will convert:
```python
# ✅ Base class handles this automatically
poll_interval = 10  # seconds (int or float both work)
max_duration = 3600  # seconds (int or float both work)
```

### Issue 5: "Progress not updating"

**Problem:** Progress messages not appearing during polling.

**Solution:** The base class handles this automatically! Just ensure you're returning progress values:
```python
def check_status(self, job_id):
    response = requests.get(f"{API_URL}/jobs/{job_id}")
    data = response.json()

    if data["status"] == "running":
        # ✅ Return progress percentage (0-100)
        return {
            "done": False,
            "progress": data.get("progress_percent", 0)
        }
```

The base class will automatically format messages like:
- "Processing... 45% complete"
- "Processing... (120s elapsed, ~180s remaining)"

---

## Summary

### Key Takeaways

1. **AsyncPollingTool reduces code by 70-87%**
   - Eliminates polling boilerplate
   - Auto-generates return schemas
   - Handles timeouts automatically

2. **Focus on YOUR API logic**
   - `submit_job()` - Your workflow
   - `check_status()` - Your status check
   - Everything else is automatic

3. **Two methods, that's it!**
   - No manual polling loops
   - No timeout management
   - No progress update logic

4. **Works with complex workflows**
   - Multi-step submissions (SwissDock example)
   - Simple polling (ProteinsPlus example)
   - Any job-based API pattern

### When to Convert

**High Priority:**
- Tools with >100 lines of polling code
- Tools with complex timeout logic
- Tools used frequently
- Tools with inconsistent behavior

**Medium Priority:**
- Tools with simple polling but still have boilerplate
- Tools that need better progress reporting
- Tools that are hard to test

**Low Priority:**
- Tools that work well and rarely change
- Tools with <50 lines total
- Tools scheduled for deprecation

### Next Steps

1. **Start with one tool** - Convert your simplest async tool first
2. **Test thoroughly** - Ensure behavior matches original
3. **Document patterns** - Note any API-specific quirks
4. **Convert more tools** - Apply learnings to other tools
5. **Share knowledge** - Help others convert their tools

---

**AsyncPollingTool makes async tool development 10x easier!** 🚀

See examples:
- `examples/proteinsplus_comparison.py` - Simple polling example
- `examples/swissdock_comparison.py` - Complex multi-step example
- `examples/async_base_example.py` - Generic examples and patterns

For questions or issues, see `GUIDE_WRITING_ASYNC_TOOLS.md` or check the test suite in `tests/test_async_base.py`.
