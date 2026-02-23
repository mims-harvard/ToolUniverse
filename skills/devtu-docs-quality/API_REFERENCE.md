# ToolUniverse API Reference for Doc Auditing

## Valid Public Methods (ground truth)

Derive the live list any time with:
```python
import sys; sys.path.insert(0, "src")
from tooluniverse import ToolUniverse
print("\n".join(m for m in sorted(dir(ToolUniverse)) if not m.startswith("_")))
```

Key methods docs most often reference:

| Method | Signature summary |
|--------|------------------|
| `run()` | `run(fcall_str, use_cache=False, max_workers=None, ...)` — accepts str, dict, or **list** (batch) |
| `run_one_function()` | Low-level single-call sync |
| `load_tools()` | `load_tools(tool_type=None, include_tools=None, exclude_tools=None, include_tool_types=None, exclude_tool_types=None, tool_config_files=None, tools_file=None)` |
| `tool_specification()` | `tool_specification(tool_name, format="default"\|"openai")` — returns `'parameter'` by default, `'parameters'` only with `format="openai"` |
| `list_built_in_tools()` | `list_built_in_tools(mode, scan_all=False)` |
| `return_all_loaded_tools()` | Returns `list[dict]` of loaded tool configs |
| `all_tool_dict` | Attribute (dict): loaded tools by name — use for membership checks |
| `get_tool_types()` | Returns `list[str]` of category names |
| `get_tool_by_name()` | `get_tool_by_name(tool_names, format)` |
| `filter_tools()` | `filter_tools(include_tools, exclude_tools, include_tool_types, exclude_tool_types)` |
| `register_custom_tool()` | `register_custom_tool(tool_class=None, tool_name=None, tool_config=None, instantiate=True, tool_instance=None)` |
| `clear_cache()` | Clear result cache |
| `close()` | Shut down MCP connections |

`ToolUniverse.__init__` kwargs: `tool_files`, `keep_default_tools`, `log_level`, `hooks_enabled`, `hook_config`, `hook_type`, `enable_name_shortening`

---

## Known-Wrong Methods Table

Every entry below appeared in ToolUniverse docs and does **not exist**. Fix or remove on sight.

| Wrong call | Fix / Action |
|---|---|
| `tu.run_batch(list)` | `tu.run(list, max_workers=N)` — `run()` accepts list natively |
| `tu.run_async(query)` | `await tu.run(query)` — `run()` is context-aware |
| `tu.call_tool('Name', {...})` | `tu.run({"name": "Name", "arguments": {...}})` |
| `tu.execute_tool('Name', {...})` | `tu.run({"name": "Name", "arguments": {...}})` |
| `tu.list_tools()` | `tu.list_built_in_tools(mode='list_name')` or `tu.all_tool_dict` |
| `tu.get_tool('Name')` | `tu.get_tool_by_name('Name')` |
| `tu.register_tool(instance)` | `tu.register_custom_tool(tool_instance=instance)` |
| `tu.register_tool_from_config(cfg)` | `tu.register_custom_tool(tool_config=cfg)` |
| `tu.list_tools_by_category('X')` | `tu.filter_tools(include_tool_types=['X'])` + check `tu.get_tool_types()` for valid names |
| `tu.configure_api_keys({...})` | **Remove** — keys are env vars only |
| `tu.get_exposed_name(name)` | **Remove** — shortening is automatic with `ToolUniverse(enable_name_shortening=True)` |
| `tu.list_available_methods()` | Client-side utility only — change code block to `.. code-block:: text` if showing as error example |
| `ToolUniverse(timeout=30)` | Remove `timeout=` — not a valid `__init__` kwarg |
| `tu.ToolName(key=val)` shorthand | `tu.run({"name": "ToolName", "arguments": {"key": val}})` |
| `load_tools(use_cache=True)` | Remove `use_cache`/`cache_dir` — not valid kwargs |
| `opentarget_get_*` (lowercase) | Rename to `OpenTargets_get_*` (capital O and T) |
| `targets[:N]` on OpenTargets result | `targets['data']['disease']['associatedTargets']['rows'][:N]` |

---

## Fix-vs-Remove Decision

> Wrong information must be fixed or removed. It must never be left as-is.

```
Wrong call found
    │
    ▼
Correct equivalent method exists?
    ├── YES → Fix to the correct method immediately
    └── NO  → Does the feature conceptually exist?
                  ├── YES (auto/internal) → Remove the call; add a prose comment if needed
                  └── NO  → Delete the code block or section entirely
```

---

## Correct Patterns

```python
# ✅ tool_specification — use format="openai" to get 'parameters' key
spec = tu.tool_specification("Tool_Name", format="openai")
for param, info in spec['parameters']['properties'].items():
    print(param, info['type'])

# ✅ batch execution
results = tu.run([
    {"name": "Tool1", "arguments": {"id": "1"}},
    {"name": "Tool1", "arguments": {"id": "2"}},
], max_workers=4)

# ✅ check if tool loaded
if "My_Tool" in tu.all_tool_dict: ...

# ✅ list tool names
names = tu.list_built_in_tools(mode='list_name')

# ✅ filter by category
tools = tu.filter_tools(include_tool_types=["uniprot"])

# ✅ async context — run() is context-aware
result = await tu.run(query)  # no run_async() needed

# ✅ register custom tool from config dict
tu.register_custom_tool(tool_config=my_config_dict)
```

---

## Context-Aware `spec['parameters']` Check

Only flag `spec['parameters']` as wrong if `format="openai"` is **not** set in the same call:

```bash
grep -n -B5 "spec\['parameters'\]" <file>
# Verify tool_specification(..., format="openai") appears above it
```
