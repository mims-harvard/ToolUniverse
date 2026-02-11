# Relationship Between run() and run_one_function()

## Overview

```
┌────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  tu.run(fcall_str)              tu.tools.X(**kwargs)       │
│         │                                │                 │
│         │                                │                 │
│         ▼                                ▼                 │
│  ┌──────────────┐              ┌────────────────┐         │
│  │   run()      │              │ ToolCallable   │         │
│  │  - Parses    │              │ .__call__()    │         │
│  │  - Routes    │              │  - Builds      │         │
│  │  - Handles   │              │    function    │         │
│  │    batch     │              │    call dict   │         │
│  └──────┬───────┘              └────────┬───────┘         │
│         │                                │                 │
│         └────────────┬───────────────────┘                 │
│                      ▼                                     │
│            ┌──────────────────┐                            │
│            │ run_one_function │                            │
│            │  - Validates     │                            │
│            │  - Caches        │                            │
│            │  - Executes      │                            │
│            │  - Applies hooks │                            │
│            └─────────┬────────┘                            │
│                      ▼                                     │
│         ┌──────────────────────────┐                       │
│         │ _execute_tool_with_stream│                       │
│         │  - Calls tool.run()      │                       │
│         └─────────┬────────────────┘                       │
│                   ▼                                        │
│            ┌─────────────┐                                 │
│            │ tool.run()  │                                 │
│            │ (Actual     │                                 │
│            │  execution) │                                 │
│            └─────────────┘                                 │
└────────────────────────────────────────────────────────────┘
```

---

## Detailed Explanation

### 1. `run()` - High-Level Entry Point

**Location**: `src/tooluniverse/execute_function.py:2095`

**Purpose**:
- **Public API** for executing tools
- Handles **parsing** of input (strings, dicts, etc.)
- Supports **batch execution** (multiple tools at once)
- Routes to appropriate handler

**Code Flow**:
```python
def run(self, fcall_str, ...):
    # Step 1: Parse input
    function_call_json = self.extract_function_call_json(fcall_str, ...)

    # Step 2: Check if single or batch
    if isinstance(function_call_json, list):
        # Batch: Execute multiple tools
        return self._execute_function_call_list(function_call_json, ...)
    else:
        # Single: Execute one tool
        return self.run_one_function(function_call_json, ...)  # ← Calls run_one_function
```

**Key Responsibilities**:
- ✅ Input parsing and validation
- ✅ Batch vs single detection
- ✅ Message formatting (if return_message=True)
- ✅ Routing to execution

---

### 2. `run_one_function()` - Single Tool Execution

**Location**: `src/tooluniverse/execute_function.py:2197`

**Purpose**:
- **Executes a single tool**
- No parsing - expects structured dict
- Handles validation, caching, hooks
- Core execution logic

**Code Flow**:
```python
def run_one_function(self, function_call_json, ...):
    function_name = function_call_json.get("name")
    arguments = function_call_json.get("arguments")

    # Step 1: Resolve tool name
    function_name = self._resolve_tool_name(function_name)

    # Step 2: Check cache
    if use_cache:
        cached_value = self.cache_manager.get(...)
        if cached_value:
            return cached_value

    # Step 3: Validate parameters
    if validate:
        validation_error = self._validate_parameters(function_name, arguments)
        if validation_error:
            return error_response

    # Step 4: Get tool instance
    tool_instance = self._get_tool_instance(function_name)

    # Step 5: Execute tool
    result, tool_arguments = self._execute_tool_with_stream(
        tool_instance, arguments, ...
    )  # ← Calls _execute_tool_with_stream

    # Step 6: Apply hooks (if enabled)
    if self.hooks_enabled and self.hook_manager:
        result = self.hook_manager.apply_output_hook(result, ...)

    # Step 7: Cache result (if enabled)
    if use_cache:
        self.cache_manager.set(result, ...)

    return result
```

**Key Responsibilities**:
- ✅ Parameter validation
- ✅ Caching (get/set)
- ✅ Tool instance management
- ✅ Actual tool execution
- ✅ Hook application
- ✅ Error handling

---

### 3. `_execute_tool_with_stream()` - Low-Level Execution

**Location**: `src/tooluniverse/execute_function.py:2397`

**Purpose**:
- **Calls tool.run()** with proper parameters
- Inspects tool signature
- Handles streaming callbacks

**Code Flow**:
```python
def _execute_tool_with_stream(self, tool_instance, arguments, ...):
    # Inspect tool signature
    signature = inspect.signature(tool_instance.run)
    params = signature.parameters

    # Build kwargs based on what tool accepts
    kwargs = {}
    if "stream_callback" in params and stream_callback:
        kwargs["stream_callback"] = stream_callback
    if "use_cache" in params:
        kwargs["use_cache"] = use_cache

    # Call tool.run()
    result = tool_instance.run(arguments, **kwargs)  # ← Actual tool execution

    return result, arguments
```

---

## Usage Patterns

### Pattern 1: Using `run()` Directly

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# High-level API - handles parsing
result = tu.run({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})

# Flow:
# 1. run() parses input
# 2. run() calls run_one_function()
# 3. run_one_function() validates, caches, executes
# 4. Returns result
```

### Pattern 2: Using `tu.tools.X()`

```python
# Convenient property access
result = tu.tools.UniProt_get_entry_by_accession(accession="P05067")

# Flow:
# 1. ToolCallable.__call__() builds function_call dict
# 2. Calls run_one_function() directly (skips run()!)
# 3. run_one_function() validates, caches, executes
# 4. Returns result
```

### Pattern 3: Batch Execution

```python
# Multiple tools at once
results = tu.run([
    {"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P05067"}},
    {"name": "RCSB_PDB_get_structure_by_id", "arguments": {"pdb_id": "2OZR"}},
])

# Flow:
# 1. run() detects list
# 2. run() calls _execute_function_call_list()
# 3. For each call, _execute_function_call_list() calls run_one_function()
# 4. Returns list of results
```

---

## Key Differences

| Aspect | `run()` | `run_one_function()` |
|--------|---------|---------------------|
| **Purpose** | High-level API | Core execution logic |
| **Input** | String/dict/list (flexible) | Dict only (structured) |
| **Parsing** | ✅ Yes (extract_function_call_json) | ❌ No (expects parsed) |
| **Batch support** | ✅ Yes (handles lists) | ❌ No (single tool only) |
| **Message formatting** | ✅ Yes (if return_message=True) | ❌ No |
| **Validation** | ❌ No (delegates) | ✅ Yes |
| **Caching** | ❌ No (delegates) | ✅ Yes |
| **Hooks** | ❌ No (delegates) | ✅ Yes |
| **Tool execution** | ❌ No (delegates) | ✅ Yes |
| **Called by** | User code | `run()`, `ToolCallable` |
| **Calls** | `run_one_function()` | `_execute_tool_with_stream()` |

---

## Call Stack Examples

### Example 1: Simple Tool Call

```python
# User code:
result = tu.run({"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P05067"}})

# Call stack:
tu.run()
  └─> self.extract_function_call_json()  # Parse input
  └─> self.run_one_function()
        └─> self._resolve_tool_name()     # Resolve aliases
        └─> self._validate_parameters()   # Validate
        └─> self._get_tool_instance()     # Get tool
        └─> self._execute_tool_with_stream()
              └─> tool_instance.run()     # ← Actual tool execution
        └─> self.hook_manager.apply_hook() # Post-process
        └─> self.cache_manager.set()      # Cache result
  └─> return result
```

### Example 2: Using tu.tools.X()

```python
# User code:
result = tu.tools.UniProt_get_entry_by_accession(accession="P05067")

# Call stack:
ToolCallable.__call__()
  └─> self.engine.run_one_function()  # ← Directly calls run_one_function()
        └─> self._validate_parameters()
        └─> self._get_tool_instance()
        └─> self._execute_tool_with_stream()
              └─> tool_instance.run()
        └─> self.hook_manager.apply_hook()
        └─> self.cache_manager.set()
  └─> return result

# Note: Skips run() entirely!
```

### Example 3: Batch Execution

```python
# User code:
results = tu.run([
    {"name": "Tool1", "arguments": {...}},
    {"name": "Tool2", "arguments": {...}},
])

# Call stack:
tu.run()
  └─> self.extract_function_call_json()  # Parse input
  └─> self._execute_function_call_list()
        ├─> self.run_one_function(call1)  # Execute Tool1
        │     └─> ... (full execution)
        └─> self.run_one_function(call2)  # Execute Tool2
              └─> ... (full execution)
  └─> return [result1, result2]
```

---

## Why This Design?

### Separation of Concerns

1. **`run()`** = User-facing API
   - Flexible input formats
   - Batch support
   - Message formatting
   - Entry point

2. **`run_one_function()`** = Core logic
   - Single tool execution
   - Validation, caching, hooks
   - Reusable by different entry points
   - Implementation details

### Benefits

✅ **`run_one_function()` is reusable**:
   - Called by `run()` for single execution
   - Called by `_execute_function_call_list()` for batch
   - Called by `ToolCallable` for property access
   - Called by MCP server

✅ **Clean separation**:
   - Parsing logic in `run()`
   - Execution logic in `run_one_function()`
   - Easy to maintain

✅ **Flexibility**:
   - `run()` can add features (parsing, batching) without changing core
   - `run_one_function()` can optimize execution without changing API

---

## Implications for Async Implementation

### Current Relationship

```
run() (sync)
  └─> run_one_function() (sync)
        └─> _execute_tool_with_stream() (sync)
              └─> tool.run() (ASYNC for some tools!) ← Problem!
```

### Solution: Parallel Async Versions

```
run() (context-aware)
  ├─> _run_sync() → run_one_function() → tool.run()
  └─> _run_async() → _run_one_function_async() → tool.run() (await)

run_one_function() (context-aware)
  ├─> _run_one_function_sync() → tool.run()
  └─> _run_one_function_async() → tool.run() (await)
```

**Key insight**: We need **async versions of the entire chain**, not just the top-level method!

---

## Summary

### Relationship

```
run()               ← Public API (parsing, routing)
  └─> run_one_function()  ← Core logic (validation, caching, execution)
        └─> _execute_tool_with_stream()  ← Low-level (call tool.run())
              └─> tool.run()  ← Actual tool implementation
```

### Key Points

1. **`run()`** is the **public entry point** - flexible, user-friendly
2. **`run_one_function()`** is the **core engine** - validation, caching, execution
3. **`_execute_tool_with_stream()`** is the **thin wrapper** - calls tool.run()
4. **`tu.tools.X()`** **bypasses `run()`** and calls `run_one_function()` directly
5. For async support, we need **async versions of all three layers**

---

## Next Steps for Async Implementation

To support async tools properly, we need:

1. ✅ **Keep `run()` context-aware** (detects sync/async)
2. ✅ **Add `_run_one_function_async()`** (async version of core logic)
3. ✅ **Add `_execute_tool_with_stream_async()`** (async wrapper)
4. ✅ **Update `ToolCallable`** to be context-aware
5. ✅ **Keep tool.run() async** for long-running tools

This maintains the clean separation while adding async support at each layer!

