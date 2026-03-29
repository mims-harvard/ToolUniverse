---
name: tooluniverse-custom-tool
description: >
  Add custom local tools to ToolUniverse and use them alongside the 1000+ built-in tools.
  Use this skill when a user wants to: create their own tool for a private or custom API,
  add a local tool to their workspace, integrate an internal service with ToolUniverse,
  or use a custom tool via the MCP server or Python API. Covers both the JSON config
  approach (easiest, no Python needed) and the Python class approach (full control).
  Also covers how to verify tools loaded correctly and how to call them.
  Also covers the plugin package approach for reusable, shareable, pip-installable tool sets.
---

# Adding Custom Tools to ToolUniverse

**When to create a custom tool:** Create one if you need to access an API that ToolUniverse
doesn't cover, or if you need a specialized data transformation that no existing tool provides.
Start with the JSON config approach (simplest — no Python needed); escalate to a Python class
only if you need custom response parsing or stateful logic.

Three ways to add tools — pick the one that fits your needs:

| Approach | When to use |
|---|---|
| **JSON config** | REST API with standard request/response — no coding needed |
| **Python class (workspace)** | Custom logic for local/private use only |
| **Plugin package** | Reusable tools you want to share or install via pip |

---

## Option A — Workspace tools (local use)

Tools in `.tooluniverse/tools/` are auto-discovered at startup. No installation needed.

```bash
mkdir -p .tooluniverse/tools
```

### JSON config

Create `.tooluniverse/tools/my_tools.json`:

```json
[
  {
    "name": "MyAPI_search",
    "description": "Search my internal database. Returns matching records with id, title, and score.",
    "type": "BaseRESTTool",
    "fields": {
      "endpoint": "https://my-api.example.com/search"
    },
    "parameter": {
      "type": "object",
      "properties": {
        "q": {
          "type": "string",
          "description": "Search query"
        },
        "limit": {
          "type": ["integer", "null"],
          "description": "Max results to return (default 10)"
        }
      },
      "required": ["q"]
    }
  }
]
```

One JSON file can define multiple tools — just add more objects to the array.

For the full JSON field reference, see [references/json-tool.md](references/json-tool.md).

### Python class

Create `.tooluniverse/tools/my_tool.py`:

```python
from tooluniverse.tool_registry import register_tool

@register_tool
class MyAPI_search:
    name = "MyAPI_search"
    description = "Search my internal database. Returns matching records with id, title, and score."
    input_schema = {
        "type": "object",
        "properties": {
            "q": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (default 10)"}
        },
        "required": ["q"]
    }

    def run(self, q: str, limit: int = 10) -> dict:
        import requests
        resp = requests.get(
            "https://my-api.example.com/search",
            params={"q": q, "limit": limit},
            timeout=30,
        )
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
```

Note: workspace Python tools use `run(self, **named_params)` — arguments are unpacked as keyword
arguments matching the `input_schema` properties.

For the full Python class reference, see [references/python-tool.md](references/python-tool.md).

### Test workspace tools

```bash
# Uses test_examples from the tool's JSON config — zero config needed
tu test MyAPI_search

# Single ad-hoc call
tu test MyAPI_search '{"q": "test"}'

# Full config with assertions
tu test --config my_tool_tests.json
```

`tu test` automatically runs these checks on every call:
- Result is not None or empty
- `return_schema` validation — validates `result["data"]` against the JSON Schema defined in `return_schema` (if present)
- `expect_status` and `expect_keys` — only if set in the config file

**Gotchas:** (1) `tu test` does NOT verify non-empty results — `[]` passes schema validation. Use test_examples args that return real data. (2) Verify test_examples manually first with urllib (not curl) to confirm the API returns JSON, not HTML. Use 2-4 broad keywords.

Add `test_examples` and `return_schema` to JSON config for best coverage. `tu test` validates `result["data"]` against `return_schema` (match `"type": "array"` or `"type": "object"` to your data shape).

Optional `my_tool_tests.json` for extra assertions (`expect_status`, `expect_keys`).

### Use with MCP server

Tools in `.tooluniverse/tools/` are auto-available via `tu serve`. Workspace priority: `--workspace` flag → `TOOLUNIVERSE_HOME` env → `./.tooluniverse/` → `~/.tooluniverse/`.

To use a different tools directory, add `sources: [./my-custom-tools/]` in `.tooluniverse/profile.yaml` and start with `tooluniverse --load .tooluniverse/profile.yaml`.

---

## Option B — Plugin package (shareable, pip-installable)

Use this when you want to distribute tools as a reusable Python package that other users can
install with `pip install`. The plugin package has the same directory layout as a workspace, plus a
`pyproject.toml` that declares the entry point.

### Package layout

```
my_project_root/           # directory containing pyproject.toml
    pyproject.toml
    my_tools_package/      # importable Python package (matches entry-point value)
        __init__.py        # minimal — one-line docstring, no registration code
        my_api_tool.py     # tool class(es) with @register_tool
        data/
            my_api_tools.json  # JSON tool configs (type must match registered class name)
        profile.yaml       # optional: name, description, required_env
```

JSON config files are discovered from both `data/` and the package root directory. The convention is `data/`.

### `pyproject.toml` entry point

```toml
[project.entry-points."tooluniverse.plugins"]
my-tools = "my_tools_package"
```

The value (`my_tools_package`) must be the importable Python package name.

### Python class in a plugin package

Plugin package tools use `BaseTool` and receive all arguments as a single `Dict`:

```python
import requests
from typing import Dict, Any
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

@register_tool("MyAPITool")
class MyAPITool(BaseTool):
    """Tool description here."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query", "")
        if not query:
            return {"error": "query parameter is required"}
        try:
            resp = requests.get(
                "https://my-api.example.com/search",
                params={"q": query},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return {"status": "success", "data": resp.json()}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
```

Key differences from the workspace pattern:
- Inherit from `BaseTool` (from `tooluniverse.base_tool`)
- `@register_tool("ClassName")` takes the class name as a string argument
- `run(self, arguments: Dict)` receives all arguments in a single dict — extract them with `.get()`
- `__init__` receives `tool_config` dict; call `super().__init__(tool_config)` first

### JSON config in a plugin package

Place configs in `data/my_api_tools.json`. The `"type"` field must match the string passed to
`@register_tool(...)`:

```json
[
  {
    "name": "MyAPI_search",
    "description": "Search my API. Returns matching records.",
    "type": "MyAPITool",
    "fields": { "operation": "search" },
    "parameter": {
      "type": "object",
      "properties": {
        "query": { "type": "string", "description": "Search query" },
        "limit": { "type": ["integer", "null"], "description": "Max results" }
      },
      "required": ["query"]
    }
  }
]
```

### `__init__.py`

Keep minimal — just a docstring. The plugin system auto-imports all `.py` files via `_discover_entry_point_plugins()`, so `@register_tool` decorators fire automatically. Optional: add `from . import my_api_tool` for IDE support (idempotent). Do NOT add registration logic or JSON loading here.

### Install and verify

```bash
pip install -e /path/to/my_project_root
cd /path/to/my_project_root   # MUST run from plugin repo directory
tu test MyAPI_search '{"query": "test"}'
```

Must `pip install -e` first. Run `tu test` from plugin repo dir (workspace auto-detection needs `.tooluniverse/`). Add `test_examples` to JSON config for zero-config testing. Use `tu info MyAPI_search` to confirm the tool loaded.

---

## Offline / pure-computation tools

Calculator tools (no HTTP) follow the plugin-package pattern but skip the HTTP layer. Key design patterns:

- **Preset lookup tables**: Define `Dict[str, float]` at module level. Resolution priority: explicit value → preset name → default. Include presets in `metadata` for discoverability.
- **Bidirectional equations**: Expose as separate `operation` values in a single tool. Use `"fields": {"operation": "default_op"}` in JSON config.
- **Physical constants**: Define at module level (`_MU0 = 4*pi*1e-7`, etc.). Material-specific values as named dicts.
- **Multi-output**: Return all related results in `data` (e.g., temperature + headroom + pass/fail) rather than forcing multiple calls.

For complete patterns, see [references/python-tool.md](references/python-tool.md).
