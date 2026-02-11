# Async Architecture Plan: Native Async Support in ToolUniverse

**Date**: 2026-02-09
**Objective**: Make ToolUniverse.run() non-blocking for async tools
**Approach**: Dual API (sync + async) with smart tool detection

---

## User Requirement

> "I want the tooluniverse.run also be Asynchronous FOR these Asynchronous tools."

**Goal**:
- Long-running tools (ProteinsPlus, SwissDock) should be async
- `tu.run()` should handle them without blocking
- Both Python SDK and MCP should work smoothly
- Maintain backwards compatibility for existing sync tools

---

## Proposed Architecture

### Dual API Pattern

```python
class ToolUniverse:
    def run(self, tool_call):
        """
        Synchronous API - handles BOTH sync and async tools intelligently

        For sync tools: Executes directly
        For async tools: Runs in event loop (blocking but correct)
        """

    async def arun(self, tool_call):
        """
        Asynchronous API - preferred for async tools

        For async tools: Awaits directly (non-blocking)
        For sync tools: Runs in thread pool (non-blocking)
        """
```

### Tool Layer

```
┌─────────────────────────────────────────────────────┐
│                 Tool Implementations                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Sync Tools (majority)        Async Tools          │
│  ├─ def run(args)             ├─ async def run()   │
│  ├─ return result             ├─ await async_op()  │
│  └─ Quick execution           └─ Long-running      │
│                                                     │
└─────────────────────────────────────────────────────┘
                         ↑
                         │
┌────────────────────────┴─────────────────────────────┐
│           ToolUniverse Core (Dual API)               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  run(sync) ──→ Detects tool type ──→ Executes       │
│                ├─ Sync tool: Direct call            │
│                └─ Async tool: asyncio.run()         │
│                                                      │
│  arun(async) ─→ Detects tool type ──→ Executes      │
│                ├─ Async tool: await                 │
│                └─ Sync tool: asyncio.to_thread()    │
│                                                      │
└──────────────────────────────────────────────────────┘
                         ↑
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼─────────┐              ┌────────▼────────┐
│  Python SDK     │              │   MCP Server    │
│  (Both APIs)    │              │   (Async)       │
└─────────────────┘              └─────────────────┘
```

---

## Implementation Plan

### Phase 1: Add Async API to ToolUniverse Core

#### Task 1.1: Add arun() Method

**File**: `src/tooluniverse/execute_function.py`

**Add new async method**:
```python
async def arun(
    self,
    fcall_str,
    return_message=False,
    verbose=True,
    format="llama",
    stream_callback=None,
    use_cache: bool = False,
):
    """
    Execute function calls asynchronously (non-blocking).

    This method is the async version of run(). It handles both sync and async tools:
    - Async tools: Awaits directly (non-blocking)
    - Sync tools: Runs in thread pool via asyncio.to_thread() (non-blocking)

    Args:
        fcall_str: Input string or data containing function call information.
        return_message (bool): Whether to return formatted messages.
        verbose (bool): Whether to enable verbose output.
        format (str): Format type for parsing.
        stream_callback: Optional callback for streaming responses.
        use_cache (bool): Whether to use result caching.

    Returns:
        Same as run(), but execution is non-blocking.

    Example:
        # In async context:
        result = await tu.arun({
            "name": "ProteinsPlus_predict_binding_sites",
            "arguments": {"pdb_id": "2OZR"}
        })
        # Returns immediately, doesn't block event loop
    """
    if return_message:
        function_call_json, message = self.extract_function_call_json(
            fcall_str, return_message=return_message, verbose=verbose, format=format
        )
    else:
        function_call_json = self.extract_function_call_json(
            fcall_str, return_message=return_message, verbose=verbose, format=format
        )
        message = ""

    if function_call_json is not None:
        if isinstance(function_call_json, list):
            # Execute batch asynchronously
            batch_results = await self._execute_function_call_list_async(
                function_call_json,
                stream_callback=stream_callback,
                use_cache=use_cache,
            )

            call_results = []
            for idx, call_result in enumerate(batch_results):
                call_id = self.call_id_gen()
                function_call_json[idx]["call_id"] = call_id
                call_results.append({
                    "role": "tool",
                    "content": json.dumps({"content": call_result, "call_id": call_id})
                })

            revised_messages = [
                {
                    "role": "assistant",
                    "content": message,
                    "tool_calls": json.dumps(function_call_json),
                }
            ] + call_results
            return revised_messages
        else:
            return await self.arun_one_function(
                function_call_json,
                stream_callback=stream_callback,
                use_cache=use_cache,
            )
    else:
        error("Not a function call")
        return None
```

#### Task 1.2: Add arun_one_function() Method

```python
async def arun_one_function(
    self,
    function_call_json,
    stream_callback=None,
    use_cache=False,
    validate=True
):
    """
    Execute a single function call asynchronously.

    This method handles both sync and async tools intelligently:
    - Detects if tool.run() is a coroutine function
    - Async tools: Awaits directly
    - Sync tools: Runs in thread pool

    Args:
        function_call_json (dict): Function name and arguments.
        stream_callback: Callback for streaming.
        use_cache (bool): Whether to use caching.
        validate (bool): Whether to validate parameters.

    Returns:
        Tool execution result (dict).
    """
    function_name = function_call_json.get("name", "")
    arguments = function_call_json.get("arguments", {})

    # Resolve tool name
    function_name = self._resolve_tool_name(function_name)

    if not function_name:
        return {"error": "Missing or empty function name"}

    if not isinstance(arguments, dict):
        return {"error": f"Arguments must be a dictionary, got {type(arguments).__name__}"}

    # [... same validation and caching logic as run_one_function ...]

    # Execute the tool asynchronously
    tool_arguments = arguments
    try:
        tool_instance = self._get_tool_instance(function_name, cache=True)

        if tool_instance:
            # Call async execution wrapper
            result, tool_arguments = await self._execute_tool_with_stream_async(
                tool_instance, arguments, stream_callback, use_cache, validate
            )
        else:
            return self._create_dual_format_error(
                ToolUnavailableError(f"Tool '{function_name}' not available")
            )

        # [... same post-execution logic as run_one_function ...]

        return result

    except Exception as e:
        # [... same error handling ...]
        return self._create_dual_format_error(e)
```

#### Task 1.3: Add _execute_tool_with_stream_async() Method

```python
async def _execute_tool_with_stream_async(
    self,
    tool_instance,
    arguments,
    stream_callback,
    use_cache=False,
    validate=True
):
    """
    Execute tool asynchronously, handling both sync and async tools.

    Key logic:
    - Detects if tool.run() is async (inspect.iscoroutinefunction)
    - Async tools: Awaits directly (non-blocking)
    - Sync tools: Runs in thread pool (non-blocking)
    """
    tool_arguments = arguments

    if isinstance(arguments, dict):
        tool_arguments = dict(arguments)

        # Handle stream callback if needed
        stream_flag_key = getattr(tool_instance, "STREAM_FLAG_KEY", None) if stream_callback else None
        if stream_callback and stream_flag_key and stream_flag_key not in tool_arguments:
            tool_arguments[stream_flag_key] = True

    # Inspect tool signature
    signature = inspect.signature(tool_instance.run)
    params = signature.parameters

    # Build kwargs
    kwargs = {}
    if stream_callback is not None and "stream_callback" in params:
        kwargs["stream_callback"] = stream_callback
    if "use_cache" in params:
        kwargs["use_cache"] = use_cache
    if "validate" in params:
        kwargs["validate"] = validate

    # Check if tool.run() is async
    if inspect.iscoroutinefunction(tool_instance.run):
        # ✅ ASYNC TOOL - await directly (non-blocking)
        self.logger.debug(f"Executing async tool: {tool_instance.name}")
        result = await tool_instance.run(tool_arguments, **kwargs)
        return result, tool_arguments
    else:
        # ✅ SYNC TOOL - run in thread pool (non-blocking)
        self.logger.debug(f"Executing sync tool in thread pool: {tool_instance.name}")
        result = await asyncio.to_thread(tool_instance.run, tool_arguments, **kwargs)
        return result, tool_arguments
```

#### Task 1.4: Update run() to Handle Async Tools

**Modify existing `run()` method**:

```python
def run(
    self,
    fcall_str,
    return_message=False,
    verbose=True,
    format="llama",
    stream_callback=None,
    use_cache: bool = False,
    max_workers: Optional[int] = None,
):
    """
    Execute function calls synchronously (may block for async tools).

    For sync tools: Executes directly (no blocking)
    For async tools: Runs in new event loop (blocks until complete, but correct)

    Note: For non-blocking execution of async tools, use arun() instead.
    """
    # [... existing parsing logic ...]

    if function_call_json is not None:
        if isinstance(function_call_json, list):
            # Batch execution
            batch_results = self._execute_function_call_list(
                function_call_json,
                stream_callback=stream_callback,
                use_cache=use_cache,
                max_workers=max_workers,
            )
            # [... rest of batch logic ...]
        else:
            # Single execution - check if we need async handling
            return self.run_one_function(
                function_call_json,
                stream_callback=stream_callback,
                use_cache=use_cache,
            )
    else:
        error("Not a function call")
        return None
```

**Update `run_one_function()`**:

```python
def run_one_function(
    self,
    function_call_json,
    stream_callback=None,
    use_cache=False,
    validate=True
):
    """
    Execute a single function call synchronously.

    For async tools, this will create a new event loop and run until complete.
    Consider using arun_one_function() for better async support.
    """
    # [... validation and setup logic ...]

    try:
        tool_instance = self._get_tool_instance(function_name, cache=True)

        if tool_instance:
            # Check if tool is async
            if inspect.iscoroutinefunction(tool_instance.run):
                # Async tool in sync context - need to run in event loop
                self.logger.debug(f"Running async tool in sync context: {function_name}")

                # Try to get running loop
                try:
                    loop = asyncio.get_running_loop()
                    # Already in async context - cannot use asyncio.run()
                    raise RuntimeError(
                        f"Tool '{function_name}' is async. "
                        f"You're in an async context - use arun() instead of run()."
                    )
                except RuntimeError as e:
                    if "no running event loop" in str(e).lower():
                        # Not in async context - safe to create new loop
                        result, tool_arguments = asyncio.run(
                            self._execute_tool_with_stream_async(
                                tool_instance, arguments, stream_callback, use_cache, validate
                            )
                        )
                    else:
                        # Already in async context error
                        raise
            else:
                # Sync tool - execute directly
                result, tool_arguments = self._execute_tool_with_stream(
                    tool_instance, arguments, stream_callback, use_cache, validate
                )
        else:
            return self._create_dual_format_error(
                ToolUnavailableError(f"Tool '{function_name}' not available")
            )

        # [... rest of logic ...]

    except Exception as e:
        # [... error handling ...]
        pass
```

#### Task 1.5: Add Async Batch Execution

```python
async def _execute_function_call_list_async(
    self,
    function_call_list: List[Dict],
    stream_callback=None,
    use_cache: bool = False,
):
    """
    Execute multiple function calls asynchronously and in parallel.

    All tools (sync and async) execute concurrently:
    - Async tools: Run directly in event loop
    - Sync tools: Run in thread pool

    This is MUCH faster than sequential execution for long-running tools.
    """
    # Create tasks for all calls
    tasks = [
        self.arun_one_function(
            call,
            stream_callback=stream_callback,
            use_cache=use_cache,
        )
        for call in function_call_list
    ]

    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=False)

    return results
```

---

### Phase 2: Update Tools to Stay Async

**Keep the current async implementation**:
- ProteinsPlus: `async def run()` ✅
- SwissDock: `async def run()` ✅

**No changes needed** - tools are already async!

---

### Phase 3: Add Convenience Properties for Async Access

#### Task 3.1: Add atools Property

**File**: `src/tooluniverse/execute_function.py`

```python
class ToolUniverse:
    # [... existing code ...]

    @property
    def atools(self):
        """
        Async version of tools property.

        Usage:
            result = await tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
            # Non-blocking!
        """
        if not hasattr(self, '_atools_proxy'):
            self._atools_proxy = AsyncToolsProxy(self)
        return self._atools_proxy


class AsyncToolsProxy:
    """Proxy for async tool access via tu.atools.X()"""

    def __init__(self, engine: ToolUniverse):
        self.engine = engine

    def __getattr__(self, tool_name: str):
        if tool_name.startswith('_'):
            raise AttributeError(f"Tool '{tool_name}' not found")

        if tool_name not in self.engine.all_tool_dict:
            raise AttributeError(f"Tool '{tool_name}' not found")

        return AsyncToolCallable(self.engine, tool_name)


class AsyncToolCallable:
    """Async callable wrapper for a tool."""

    def __init__(self, engine: ToolUniverse, tool_name: str):
        self.engine = engine
        self.tool_name = tool_name
        self.schema = engine.all_tool_dict[tool_name]["parameter"]
        self.__doc__ = engine.all_tool_dict[tool_name].get("description", tool_name)

    async def __call__(
        self,
        *,
        stream_callback=None,
        use_cache=False,
        validate=True,
        **kwargs
    ):
        """Execute tool asynchronously."""
        return await self.engine.arun_one_function(
            {"name": self.tool_name, "arguments": kwargs},
            stream_callback=stream_callback,
            use_cache=use_cache,
            validate=validate,
        )
```

---

## Usage Examples

### Python SDK - Async Usage (Non-Blocking) ✅

```python
import asyncio
from tooluniverse import ToolUniverse

async def main():
    tu = ToolUniverse()
    tu.load_tools()

    # ✅ Non-blocking execution
    result = await tu.arun({
        "name": "ProteinsPlus_predict_binding_sites",
        "arguments": {"pdb_id": "2OZR"}
    })
    print(result)

    # Or using atools property:
    result = await tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
    print(result)

# Run
asyncio.run(main())
```

### Python SDK - Async Batch (Parallel Execution) ✅

```python
import asyncio
from tooluniverse import ToolUniverse

async def main():
    tu = ToolUniverse()
    tu.load_tools()

    # Run 3 jobs in parallel! (15 min total instead of 45 min)
    results = await asyncio.gather(
        tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR"),
        tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="1ABC"),
        tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="3XYZ"),
    )

    for result in results:
        print(result)

asyncio.run(main())
```

### Python SDK - Sync Usage (Still Works) ✅

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# For async tools, this blocks but returns correct result
result = tu.run({
    "name": "ProteinsPlus_predict_binding_sites",
    "arguments": {"pdb_id": "2OZR"}
})
# Blocks for 15 minutes, then returns result
print(result)

# Or:
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
# Also blocks, but works correctly
```

### MCP Server - No Changes Needed ✅

```python
# MCP server already uses async
# TaskManager already handles this correctly
# No changes needed!
```

---

## Comparison: Before vs After

### Before (Proposed Sync Architecture)

```python
# Blocking for 15 minutes
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
```

**Problem**: Blocks, no way to avoid it in Python SDK

### After (Async Architecture)

```python
# Option 1: Sync (blocks but works)
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Option 2: Async (non-blocking!) ✅
result = await tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Option 3: Parallel async
results = await asyncio.gather(
    tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR"),
    tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="1ABC"),
)
```

**Benefits**: Users choose sync or async based on needs!

---

## Implementation Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| **Phase 1** | Add async API to core | 3 hours |
| - Task 1.1 | Add arun() method | 1 hour |
| - Task 1.2 | Add arun_one_function() | 1 hour |
| - Task 1.3 | Add _execute_tool_with_stream_async() | 30 min |
| - Task 1.4 | Update run() for async tools | 30 min |
| **Phase 2** | Keep tools async | 0 hours |
| (Already done!) | ProteinsPlus, SwissDock async | ✅ |
| **Phase 3** | Add atools property | 1 hour |
| - Task 3.1 | Implement AsyncToolsProxy | 1 hour |
| **Phase 4** | Testing | 2 hours |
| **Phase 5** | Documentation | 1 hour |
| **Total** | | **7 hours** |

---

## Benefits

### For Users

1. **Choice**: Sync or async, you choose
2. **Non-blocking**: Async API doesn't block event loop
3. **Parallel execution**: Run multiple jobs concurrently
4. **Backwards compatible**: Existing sync code still works
5. **Progressive enhancement**: Start with sync, migrate to async when needed

### For Developers

1. **Clean architecture**: Tools can be sync or async
2. **Type detection**: Core handles both automatically
3. **No breaking changes**: Additive changes only
4. **Testable**: Easy to test both sync and async paths

---

## Migration Guide

### Existing Code (Sync)

```python
# Still works, just blocks for async tools
result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
```

**No changes needed!** ✅

### New Code (Async, Non-Blocking)

```python
# Wrap in async function
async def my_analysis():
    result = await tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")
    return result

# Run
result = asyncio.run(my_analysis())
```

### Jupyter Notebooks

```python
# Cell 1: Import and setup
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Cell 2: Run async tool (non-blocking!)
result = await tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

# Jupyter automatically handles async/await!
```

---

## Testing Strategy

### Test Sync API with Async Tools

```python
def test_sync_api_with_async_tool():
    """Test that sync API works with async tools."""
    tu = ToolUniverse()
    tu.load_tools()

    # Should work (blocks, but returns correct result)
    result = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

    assert isinstance(result, dict)
    assert "data" in result or "error" in result
```

### Test Async API with Async Tools

```python
@pytest.mark.asyncio
async def test_async_api_with_async_tool():
    """Test that async API works with async tools (non-blocking)."""
    tu = ToolUniverse()
    tu.load_tools()

    # Should not block event loop
    result = await tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR")

    assert isinstance(result, dict)
    assert "data" in result or "error" in result
```

### Test Async API with Sync Tools

```python
@pytest.mark.asyncio
async def test_async_api_with_sync_tool():
    """Test that async API works with sync tools too."""
    tu = ToolUniverse()
    tu.load_tools()

    # Sync tool via async API (runs in thread pool)
    result = await tu.atools.UniProt_get_entry_by_accession(accession="P05067")

    assert isinstance(result, dict)
```

### Test Parallel Execution

```python
@pytest.mark.asyncio
async def test_parallel_execution():
    """Test running multiple async tools in parallel."""
    tu = ToolUniverse()
    tu.load_tools()

    start = time.time()

    # Run 3 in parallel
    results = await asyncio.gather(
        tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="2OZR"),
        tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="1ABC"),
        tu.atools.ProteinsPlus_predict_binding_sites(pdb_id="3XYZ"),
    )

    elapsed = time.time() - start

    # Should take ~15 min (parallel) not 45 min (sequential)
    assert elapsed < 1800  # 30 min max (with buffer)
    assert len(results) == 3
```

---

## Decision: Async Architecture vs Sync Architecture

| Criterion | Sync Architecture | Async Architecture |
|-----------|------------------|-------------------|
| **Non-blocking SDK** | ❌ No | ✅ Yes |
| **Backwards compatible** | ✅ Yes | ✅ Yes |
| **Parallel execution** | Via threads | ✅ Native async |
| **User choice** | ❌ Blocking only | ✅ Sync or async |
| **Implementation time** | 8.5 hours | 7 hours |
| **Complexity** | Low | Medium |
| **Recommended** | ❌ | ✅ **YES** |

---

## Recommendation

### ✅ Implement Async Architecture (This Plan)

**Why:**
1. Gives users **choice** (sync or async)
2. Enables **non-blocking** Python SDK usage
3. Enables **parallel execution** easily
4. **Backwards compatible** (sync API still works)
5. **Less implementation time** than sync revert

**This is the best solution!** 🎯

---

## Next Steps

1. **Review plan** with team
2. **Approve approach** (async architecture)
3. **Begin implementation** (Phase 1)
4. **Test thoroughly**
5. **Document** new async API
6. **Release** with migration guide

**Estimated delivery**: 1-2 days

---

**Status**: Awaiting approval
**Recommendation**: ✅ **Implement this async architecture**
**Impact**: Major improvement in usability!

