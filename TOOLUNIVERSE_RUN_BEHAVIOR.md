# ToolUniverse.run() Behavior: Planned Architecture

## TL;DR

**When you call `tu.run()` in the planned architecture:**

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# This will BLOCK for 5-15 minutes!
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
print(result)  # Finally prints after waiting
```

**Behavior**: The call **blocks** (waits) until the tool completes, just like any normal Python function.

---

## Detailed Explanation

### Current Architecture (Broken)

```python
# Current (WRONG):
result = tu.run({"name": "ProteinsPlus_predict_binding_sites", "arguments": {...}})

# Returns: <coroutine object ProteinsPlusRESTTool.run at 0x...>
# ❌ NOT the actual result!
# ❌ You get a coroutine object, which is useless in sync context
```

### Planned Architecture (Correct)

```python
# Planned (CORRECT):
result = tu.run({"name": "ProteinsPlus_predict_binding_sites", "arguments": {...}})

# Your program BLOCKS here for 5-15 minutes...
# (Control flow is stuck, waiting for the tool to finish)
# ...
# Finally returns: {"data": {"pockets": [...]}}
# ✅ Actual result!
```

---

## What "Blocking" Means

### Blocking Example

```python
import time
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

print("Starting at:", time.time())

# This line blocks (waits) until complete
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

print("Finished at:", time.time())  # 5-15 minutes later!
print("Result:", result)
```

**Output:**
```
Starting at: 1707484200.0
(5-15 minutes pass... your program is frozen here)
Finished at: 1707485100.0  # 15 minutes later
Result: {'data': {'pockets': [...]}}
```

**During those 15 minutes:**
- ❌ Your program cannot do anything else
- ❌ You cannot run other tools
- ❌ You cannot check progress
- ❌ Control flow is stuck on that line

---

## Comparison: Python SDK vs MCP

### Python SDK (Synchronous)

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Direct call - BLOCKS
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
# ⏳ Waits 5-15 minutes here
# ✅ Then returns result

print(result)  # Finally executes
```

**Behavior:**
- ⏳ **Blocks** for entire duration
- ✅ Returns actual result when done
- ❌ Cannot run other operations meanwhile
- ✅ Simple, straightforward API

### MCP Client (Asynchronous)

```python
# In MCP client (e.g., Claude Code):
# Call ProteinsPlus_predict_binding_sites

# MCP Server does:
task_id = await task_manager.create_task(
    tool_name="ProteinsPlus_predict_binding_sites",
    arguments={"pdb_id": "2OZR"}
)
# ✅ Returns IMMEDIATELY with task_id

# Tool runs in background (thread pool)
# Client polls for status:
while True:
    status = await task_manager.get_status(task_id)
    if status["status"] == "completed":
        break
    await asyncio.sleep(5)  # Check every 5 seconds

result = await task_manager.get_result(task_id)
```

**Behavior:**
- ✅ Returns **immediately** (< 1 second)
- ✅ Tool runs in background
- ✅ Can do other things meanwhile
- ✅ Progress updates available
- ✅ Can cancel if needed

---

## Side-by-Side Comparison

| Aspect | Python SDK (`tu.run()`) | MCP Client |
|--------|------------------------|-----------|
| **Call returns** | After 5-15 min | Immediately |
| **Can do other work?** | ❌ No (blocked) | ✅ Yes |
| **Progress updates?** | ❌ No | ✅ Yes |
| **Cancellable?** | ❌ No | ✅ Yes |
| **Result availability** | Immediate (after wait) | Poll or wait |
| **Complexity** | Simple | More complex |
| **Use case** | Scripts, notebooks | Interactive, parallel |

---

## Use Cases

### When to Use Python SDK (Blocking)

✅ **Good for:**
```python
# 1. Simple scripts where blocking is OK
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
analyze(result)

# 2. Sequential processing (one after another)
for pdb_id in ["2OZR", "1ABC", "3XYZ"]:
    result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id=pdb_id)
    save_results(result)
    # Total time: 45 minutes (sequential)

# 3. Jupyter notebooks (cell can block)
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
# Show progress bar in next cell while waiting
```

❌ **Not good for:**
```python
# 1. Parallel processing
# This processes ONE AT A TIME (slow!)
results = []
for pdb_id in ["2OZR", "1ABC", "3XYZ"]:  # Takes 45 min total!
    result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id=pdb_id)
    results.append(result)

# 2. Interactive applications
# User is stuck waiting 15 minutes!
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id=user_input)
show_result(result)  # Finally shows after 15 min wait

# 3. Real-time systems
# System freezes for 15 minutes!
```

### When to Use MCP (Non-Blocking)

✅ **Good for:**
```python
# 1. Parallel processing (via MCP client)
task_ids = []
for pdb_id in ["2OZR", "1ABC", "3XYZ"]:
    task_id = await task_manager.create_task(...)
    task_ids.append(task_id)
    # All 3 run in parallel! Total time: ~15 min

# 2. Interactive applications
# User gets feedback immediately
task_id = await task_manager.create_task(...)
show_message("Job submitted! Check back later")
# User can do other things

# 3. Long-running workflows
# Submit multiple jobs, monitor progress
```

---

## What If I Want Non-Blocking in Python?

### Option 1: Use tu.run_batch() (Parallel Execution)

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Run multiple tools in parallel (using ThreadPoolExecutor internally)
calls = [
    {"name": "ProteinsPlus_predict_binding_sites", "arguments": {"pdb_id": "2OZR"}},
    {"name": "ProteinsPlus_predict_binding_sites", "arguments": {"pdb_id": "1ABC"}},
    {"name": "ProteinsPlus_predict_binding_sites", "arguments": {"pdb_id": "3XYZ"}},
]

# Still blocks, but runs in parallel
results = tu.run_batch(calls, max_workers=3)
# Takes ~15 minutes (parallel) instead of 45 minutes (sequential)
```

### Option 2: Use Python threading yourself

```python
import threading
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

result = None

def run_tool():
    global result
    result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Start tool in background thread
thread = threading.Thread(target=run_tool)
thread.start()

# Do other work
print("Tool is running in background...")
do_other_work()

# Wait for completion
thread.join()
print("Tool finished:", result)
```

### Option 3: Use MCP via HTTP API

```python
import requests
import time

# Submit job via HTTP API (if running HTTP server)
response = requests.post("http://localhost:8000/tools/call", json={
    "name": "ProteinsPlus_predict_binding_sites",
    "arguments": {"pdb_id": "2OZR"},
    "task": {"ttl": 3600000}
})

task_id = response.json()["task"]["taskId"]
print(f"Task created: {task_id}")

# Poll for completion
while True:
    status = requests.get(f"http://localhost:8000/tasks/{task_id}/status").json()
    if status["status"] == "completed":
        break
    print(f"Status: {status['statusMessage']}")
    time.sleep(5)

# Get result
result = requests.get(f"http://localhost:8000/tasks/{task_id}/result").json()
print("Result:", result)
```

### Option 4: Use asyncio with async wrapper

```python
import asyncio
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

async def run_tool_async():
    # Run sync tool in thread pool
    result = await asyncio.to_thread(
        tu.tools.ProteinsPlus_predict_binding_sites,
        pdb_id="2OZR"
    )
    return result

async def main():
    # Now can run multiple in parallel
    results = await asyncio.gather(
        run_tool_async(),  # Tool 1
        run_tool_async(),  # Tool 2
        run_tool_async(),  # Tool 3
    )
    return results

# Run
results = asyncio.run(main())
```

---

## Why This Design?

### Design Rationale

**Q**: Why make Python SDK blocking if we have async infrastructure?

**A**: Separation of concerns:
1. **Tools** = Simple, synchronous, work anywhere
2. **Orchestration** = Complex, async, MCP layer

**Benefits:**
- ✅ Tools are simple to write (no async complexity)
- ✅ Tools work in any context (sync or async)
- ✅ Python SDK has simple API (just call functions)
- ✅ MCP layer provides advanced features (tasks, progress, cancellation)
- ✅ Users choose the right tool for the job

### Analogy

Think of it like HTTP requests:

```python
# requests library (blocking, like ToolUniverse)
response = requests.get("https://api.example.com/slow-endpoint")
# Blocks for 30 seconds
print(response.json())

# httpx library with async (non-blocking, like MCP)
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/slow-endpoint")
    # Doesn't block event loop
    print(response.json())
```

Both are valid! Choose based on your needs:
- Simple script? Use `requests` (blocking is fine)
- High-performance server? Use `httpx` async (non-blocking)

Same with ToolUniverse:
- Simple analysis? Use `tu.run()` (blocking is fine)
- Interactive app? Use MCP client (non-blocking)

---

## Summary

### Python SDK (`tu.run()`) - Planned Behavior

```python
# Synchronous, blocking execution
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
```

**What happens:**
1. ✅ Tool runs synchronously (blocks)
2. ⏳ Your program waits 5-15 minutes
3. ✅ Returns actual result (dict)
4. ✅ Simple, predictable behavior
5. ❌ Cannot do other work during wait
6. ❌ No progress updates
7. ❌ Cannot cancel

**Use when:**
- Running simple scripts
- Sequential processing is OK
- Don't need progress updates
- Don't need to run multiple jobs in parallel

### MCP Client - Planned Behavior

```python
# Asynchronous, non-blocking execution
task_id = await task_manager.create_task(...)
```

**What happens:**
1. ✅ Returns immediately (< 1 second)
2. ✅ Tool runs in background (thread pool)
3. ✅ Can poll for status
4. ✅ Get progress updates
5. ✅ Can cancel
6. ✅ Can run multiple jobs in parallel

**Use when:**
- Need non-blocking execution
- Want progress updates
- Need cancellation support
- Running multiple jobs in parallel
- Building interactive applications

---

## Migration Path for Existing Code

### If your code currently does:

```python
# This currently returns a coroutine (broken!)
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
```

### After the architecture fix:

**Option 1: Keep using Python SDK (blocking)**
```python
# Will work, but blocks for 5-15 minutes
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
# ⏳ Waits here...
print(result)  # Finally prints
```

**Option 2: Switch to MCP for non-blocking**
```python
# Use MCP client or HTTP API for non-blocking execution
# See examples above
```

**Option 3: Use tu.run_batch() for parallel**
```python
# Run multiple in parallel
results = tu.run_batch([...])
```

---

## Decision Tree

```
Do you need the result immediately?
├─ Yes → Use MCP client (non-blocking)
│         - Interactive app
│         - Need progress updates
│         - Multiple parallel jobs
│
└─ No → Use Python SDK (blocking is OK)
          - Simple script
          - Sequential processing
          - Don't need progress
```

---

## Key Takeaway

**Python SDK behavior after architecture fix:**
- ✅ Works correctly (returns actual results, not coroutines)
- ⏳ Blocks during execution (5-15 minutes for ProteinsPlus)
- 🎯 This is intentional and correct!

**If you need non-blocking:**
- Use MCP client instead
- Or use `tu.run_batch()` for parallel execution
- Or wrap in `asyncio.to_thread()` yourself

The architecture separates concerns cleanly:
- **Tools** = Simple, synchronous
- **Python SDK** = Direct execution, blocking
- **MCP layer** = Advanced features, non-blocking

Choose the right tool for your use case! 🎯
