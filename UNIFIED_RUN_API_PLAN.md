# Unified run() API: Context-Aware Execution

**Date**: 2026-02-09
**Objective**: Single `run()` method that works in both sync and async contexts
**User Request**: "Can i only expose one run instead of having a new arun?"

---

## The Problem

Having two methods (`run()` and `arun()`) is confusing:
- Users must remember which to use
- Code becomes cluttered with two APIs
- Not intuitive

**Better**: One `run()` method that "just works" everywhere!

---

## The Solution: Context-Aware run()

### Smart Behavior

```python
# In SYNC context (regular Python):
result = tu.run(...)  # Returns result directly (may block)

# In ASYNC context (async function):
result = await tu.run(...)  # Returns coroutine, must await
```

**One method, two modes!** The method detects which context it's in and behaves appropriately.

---

## Implementation

### Core Logic

```python
def run(self, fcall_str, **kwargs):
    """
    Context-aware execution - works in both sync and async contexts.

    In sync context:
        result = tu.run(...)  # Returns result directly

    In async context:
        result = await tu.run(...)  # Returns coroutine, must await

    The method automatically detects the context and behaves appropriately.
    """
    # Detect if we're in an async context
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context - return coroutine
        return self._run_async(fcall_str, **kwargs)
    except RuntimeError:
        # Not in async context - run synchronously
        return self._run_sync(fcall_str, **kwargs)
```

### Helper Methods

```python
def _run_sync(self, fcall_str, **kwargs):
    """Execute synchronously (blocks if tool is async)."""
    function_call_json = self.extract_function_call_json(fcall_str, ...)

    if isinstance(function_call_json, list):
        # Batch execution
        return self._execute_function_call_list_sync(function_call_json, **kwargs)
    else:
        # Single execution
        return self._run_one_function_sync(function_call_json, **kwargs)


async def _run_async(self, fcall_str, **kwargs):
    """Execute asynchronously (non-blocking)."""
    function_call_json = self.extract_function_call_json(fcall_str, ...)

    if isinstance(function_call_json, list):
        # Batch execution (parallel)
        return await self._execute_function_call_list_async(function_call_json, **kwargs)
    else:
        # Single execution
        return await self._run_one_function_async(function_call_json, **kwargs)
```

### Tool Execution

```python
def _run_one_function_sync(self, function_call_json, **kwargs):
    """Execute single tool synchronously."""
    tool_instance = self._get_tool_instance(function_name)

    if inspect.iscoroutinefunction(tool_instance.run):
        # Async tool in sync context - need event loop
        result = asyncio.run(self._execute_tool_async(tool_instance, arguments))
    else:
        # Sync tool - execute directly
        result = tool_instance.run(arguments)

    return result


async def _run_one_function_async(self, function_call_json, **kwargs):
    """Execute single tool asynchronously."""
    tool_instance = self._get_tool_instance(function_name)

    if inspect.iscoroutinefunction(tool_instance.run):
        # Async tool - await directly (non-blocking)
        result = await tool_instance.run(arguments)
    else:
        # Sync tool - run in thread pool (non-blocking)
        result = await asyncio.to_thread(tool_instance.run, arguments)

    return result
```

---

## Usage Examples

### Sync Context (Backward Compatible)

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Just call run() - it detects sync context
result = tu.run({
    "name": "ProteinsPlus_predict_binding_sites",
    "arguments": {"pdb_id": "2OZR"}
})

# For async tools, this blocks until complete
print(result)  # ✅ Works!
```

### Async Context (Non-Blocking)

```python
import asyncio
from tooluniverse import ToolUniverse

async def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Same run() method, but returns coroutine in async context
    result = await tu.run({
        "name": "ProteinsPlus_predict_binding_sites",
        "arguments": {"pdb_id": "2OZR"}
    })

    # Non-blocking! ✅
    print(result)

asyncio.run(main())
```

### Parallel Execution in Async Context

```python
async def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Run 3 jobs in parallel!
    results = await asyncio.gather(
        tu.run({"name": "ProteinsPlus_...", "arguments": {"pdb_id": "2OZR"}}),
        tu.run({"name": "ProteinsPlus_...", "arguments": {"pdb_id": "1ABC"}}),
        tu.run({"name": "ProteinsPlus_...", "arguments": {"pdb_id": "3XYZ"}}),
    )

    # All 3 run concurrently! ✅
    return results
```

### Jupyter Notebook (Auto-Detects)

```python
# Cell 1: Setup
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Cell 2: Run async tool
# Jupyter automatically creates async context, so this works!
result = await tu.run({
    "name": "ProteinsPlus_predict_binding_sites",
    "arguments": {"pdb_id": "2OZR"}
})

print(result)  # ✅ Non-blocking in Jupyter!
```

---

## Tools Property (tu.tools.X)

### Also Make tools Property Context-Aware

```python
class ToolCallable:
    """Context-aware callable for tools."""

    def __call__(self, **kwargs):
        """Execute tool - returns result (sync) or coroutine (async)."""
        # Detect context
        try:
            loop = asyncio.get_running_loop()
            # Async context - return coroutine
            return self._call_async(**kwargs)
        except RuntimeError:
            # Sync context - return result
            return self._call_sync(**kwargs)

    def _call_sync(self, **kwargs):
        """Synchronous execution."""
        return self.engine.run({
            "name": self.tool_name,
            "arguments": kwargs
        })

    async def _call_async(self, **kwargs):
        """Asynchronous execution."""
        return await self.engine.run({
            "name": self.tool_name,
            "arguments": kwargs
        })
```

**Usage:**

```python
# Sync context:
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Async context:
result = await tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Same API! ✅
```

---

## Implementation Plan

### Phase 1: Update Core run() Method (2 hours)

**File**: `src/tooluniverse/execute_function.py`

1. **Modify `run()` to detect context**:
```python
def run(self, fcall_str, return_message=False, verbose=True,
        format="llama", stream_callback=None, use_cache=False, max_workers=None):
    """Context-aware run - works in both sync and async contexts."""

    # Detect async context
    try:
        asyncio.get_running_loop()
        # In async context - return coroutine
        return self._run_async_impl(fcall_str, return_message, verbose,
                                     format, stream_callback, use_cache)
    except RuntimeError:
        # Not in async context - run sync
        return self._run_sync_impl(fcall_str, return_message, verbose,
                                   format, stream_callback, use_cache, max_workers)
```

2. **Implement `_run_sync_impl()`** (current run logic)
3. **Implement `_run_async_impl()`** (new async logic)

### Phase 2: Update ToolCallable (1 hour)

**File**: `src/tooluniverse/execute_function.py`

Update `ToolCallable.__call__()` to be context-aware:

```python
def __call__(self, *, stream_callback=None, use_cache=False, validate=True, **kwargs):
    """Context-aware execution."""
    try:
        asyncio.get_running_loop()
        # Async context
        return self._async_call(stream_callback, use_cache, validate, **kwargs)
    except RuntimeError:
        # Sync context
        return self._sync_call(stream_callback, use_cache, validate, **kwargs)

def _sync_call(self, stream_callback, use_cache, validate, **kwargs):
    """Sync execution (current implementation)."""
    return self.engine.run_one_function(
        {"name": self.tool_name, "arguments": kwargs},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )

async def _async_call(self, stream_callback, use_cache, validate, **kwargs):
    """Async execution."""
    return await self.engine._run_one_function_async(
        {"name": self.tool_name, "arguments": kwargs},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )
```

### Phase 3: Add Async Implementations (2 hours)

**File**: `src/tooluniverse/execute_function.py`

Implement async versions of execution methods:

1. `async def _run_async_impl()` - Async version of run logic
2. `async def _run_one_function_async()` - Async single execution
3. `async def _execute_tool_with_stream_async()` - Async tool wrapper
4. `async def _execute_function_call_list_async()` - Async batch

### Phase 4: Testing (2 hours)

1. Test sync context with sync tools
2. Test sync context with async tools
3. Test async context with sync tools
4. Test async context with async tools
5. Test parallel execution
6. Test error handling in both contexts

### Phase 5: Documentation (1 hour)

Update docs to show unified API:
- Single `run()` method
- Works in both contexts
- Examples for each use case

---

## Comparison: Dual API vs Unified API

| Aspect | Dual API (run + arun) | Unified API (run only) |
|--------|----------------------|------------------------|
| **Number of methods** | 2 | 1 ✅ |
| **User confusion** | Higher | Lower ✅ |
| **API simplicity** | Medium | High ✅ |
| **Backwards compatible** | ✅ Yes | ✅ Yes |
| **Jupyter friendly** | ✅ Yes | ✅ Yes |
| **Implementation complexity** | Medium | Medium |
| **Explicitness** | High | Medium |

---

## Pros and Cons

### Unified API (Single run())

**Pros:**
- ✅ Simpler API - one method to learn
- ✅ Less confusion - no need to choose
- ✅ Context-aware - "just works"
- ✅ Cleaner code - no method duplication
- ✅ Backwards compatible

**Cons:**
- ⚠️ Magic behavior - might surprise some users
- ⚠️ Must remember to `await` in async context
- ⚠️ Type hints are tricky (Union[T, Awaitable[T]])

### Dual API (run + arun)

**Pros:**
- ✅ Explicit - clear which is which
- ✅ Type hints are clear
- ✅ No "magic" detection

**Cons:**
- ⚠️ Two methods to learn
- ⚠️ User must choose correctly
- ⚠️ More code to maintain

---

## Type Hints Challenge

### The Problem

```python
def run(self, fcall_str) -> Union[Dict, Awaitable[Dict]]:
    """Returns either result or coroutine."""
    # Type checkers can't tell which!
```

### Solution: Overload

```python
from typing import overload, Literal

@overload
def run(self, fcall_str, *, _async: Literal[False] = ...) -> Dict:
    ...

@overload
def run(self, fcall_str, *, _async: Literal[True]) -> Awaitable[Dict]:
    ...

def run(self, fcall_str, _async=None):
    """Implementation."""
    if _async is None:
        # Auto-detect
        try:
            asyncio.get_running_loop()
            _async = True
        except RuntimeError:
            _async = False

    if _async:
        return self._run_async_impl(fcall_str)
    else:
        return self._run_sync_impl(fcall_str)
```

**Usage:**
```python
# Type checker knows this returns Dict
result = tu.run(..., _async=False)

# Type checker knows this returns Awaitable[Dict]
coro = tu.run(..., _async=True)
result = await coro
```

But auto-detection still works:
```python
result = tu.run(...)  # Auto-detects context
```

---

## Recommendation

### ✅ **Implement Unified API** (Single run())

**Why:**
1. Simpler user experience
2. One method to learn
3. Works everywhere
4. Backwards compatible
5. Jupyter-friendly

**Timeline:**
- Phase 1-3: 5 hours (implementation)
- Phase 4: 2 hours (testing)
- Phase 5: 1 hour (docs)
- **Total: 8 hours**

---

## Example: Before and After

### Before (Current - Broken)

```python
# Returns coroutine object (wrong!)
result = tu.run(...)  # <coroutine object>
```

### After Option A (Dual API)

```python
# Sync
result = tu.run(...)  # Blocks

# Async
result = await tu.arun(...)  # Non-blocking

# Two methods to remember!
```

### After Option B (Unified API) ⭐

```python
# Sync context
result = tu.run(...)  # Blocks, returns result

# Async context
result = await tu.run(...)  # Non-blocking, same method!

# One method, works everywhere! ✅
```

---

## Decision Matrix

| Criterion | Keep Broken | Dual API | **Unified API** ⭐ |
|-----------|------------|----------|-------------------|
| **Backwards compatible** | ❌ | ✅ | ✅ |
| **Non-blocking async** | ❌ | ✅ | ✅ |
| **API simplicity** | N/A | ⚠️ Medium | ✅ **Simple** |
| **User experience** | ❌ | ⚠️ OK | ✅ **Great** |
| **Implementation time** | 0 | 7 hours | 8 hours |
| **Magic/implicit** | N/A | Low | Medium |
| **Recommended** | ❌ | ⚠️ | ✅ **YES** |

---

## Final Recommendation

### ✅ **Implement Unified run() API**

**Summary:**
- Single `run()` method that works in both sync and async contexts
- Auto-detects context using `asyncio.get_running_loop()`
- Returns result (sync) or coroutine (async) accordingly
- Backwards compatible
- Simple, intuitive API

**Next Steps:**
1. Implement context detection in `run()`
2. Add async execution paths
3. Update `ToolCallable` for context awareness
4. Test thoroughly
5. Document unified API

**Ready to implement?** 🚀

