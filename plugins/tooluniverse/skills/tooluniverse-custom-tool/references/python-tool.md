# Python Tool Reference

There are two Python class patterns depending on where the tool lives.

---

## Pattern 1 — Workspace tool (`.tooluniverse/tools/`)

Use this for local/private tools dropped into a workspace directory.

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

Key points:
- `@register_tool` with no argument — the class name is used as the tool name
- `run(self, **named_params)` — ToolUniverse unpacks the validated arguments as keyword args
- `name`, `description`, `input_schema` are class attributes (not `__init__`)

---

## Pattern 2 — Plugin package tool

Use this for tools in a pip-installable package (e.g. `tooluniverse-circuit`).

```python
import requests
from typing import Dict, Any
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

@register_tool("MyAPITool")
class MyAPITool(BaseTool):
    """Tool description here (used as docstring, not as the LLM-facing description)."""

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

Key differences from Pattern 1:
- `@register_tool("ClassName")` takes the class name as a **string argument**
- Inherits from `BaseTool` (`from tooluniverse.base_tool import BaseTool`)
- `__init__` receives `tool_config` dict — call `super().__init__(tool_config)` first
- `run(self, arguments: Dict)` receives all arguments in **one dict** — use `.get()` to extract
- The LLM-facing name and description come from the JSON config file, not the class
- `fields` in the config can pass routing info to `__init__` (commonly `"operation"`)

### Multiple tools from one class (fields.operation pattern)

One Python class can back multiple JSON-configured tools. Use `"fields": {"operation": "..."}` in
the JSON config and `self.operation` in `__init__` to dispatch:

```python
@register_tool("MyAPITool")
class MyAPITool(BaseTool):
    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.operation == "search":
            return self._search(arguments)
        elif self.operation == "list":
            return self._list(arguments)
        return {"error": f"Unknown operation: {self.operation}"}
```

JSON configs for the two tools both set `"type": "MyAPITool"` but different `"fields"`:

```json
[
  { "name": "MyAPI_search", "type": "MyAPITool", "fields": {"operation": "search"}, ... },
  { "name": "MyAPI_list",   "type": "MyAPITool", "fields": {"operation": "list"},   ... }
]
```

Each JSON entry becomes a separate tool in ToolUniverse with its own name, description, and parameters.

---

## Required elements (both patterns)

| Element | Pattern 1 (workspace) | Pattern 2 (plugin) |
|---|---|---|
| Decorator | `@register_tool` | `@register_tool("ClassName")` |
| Base class | plain class | `BaseTool` |
| Name/description | class attributes | JSON config file |
| `run` signature | `run(self, param1, param2=...)` | `run(self, arguments: Dict)` |

---

## Return format

Always return a dict. Conventions:

```python
# Success — data can be a list or a dict
return {"status": "success", "data": result}

# Success with extra context (source URL, total count, applied filters, etc.)
return {
    "status": "success",
    "data": result,
    "metadata": {
        "source": "My API (api.example.com)",
        "query": query,
        "total_results": len(result),
    },
}

# Error — return, don't raise
return {"status": "error", "message": "Record not found"}

# Plugin packages sometimes use "error" key directly (no "status"):
return {"error": "Record not found"}
```

`tu test` validates `result["data"]` against `return_schema` (only when `status == "success"`).
The `metadata` key is ignored by schema validation — it is purely informational for the caller.
Make sure the `return_schema` top-level type matches what you put in `data`:
- List of results → `"type": "array"`
- Single record lookup → `"type": "object"`

---

## input_schema patterns (Pattern 1 / workspace)

```python
input_schema = {
    "type": "object",
    "properties": {
        # Required string
        "gene_id": {"type": "string", "description": "Ensembl gene ID (e.g. ENSG00000139618)"},

        # Optional string (include "null" in type, omit from required)
        "species": {"type": ["string", "null"], "description": "Species name (default: human)"},

        # Optional integer
        "limit": {"type": ["integer", "null"], "description": "Max results (default 10)"},

        # Enum
        "format": {
            "type": "string",
            "enum": ["json", "csv", "tsv"],
            "description": "Output format"
        },
    },
    "required": ["gene_id"]
}
```

If a tool has NO required parameters (all params are optional), use `"required": []` — do not
omit the key entirely:

```python
input_schema = {
    "type": "object",
    "properties": {
        "query": {"type": ["string", "null"], "description": "Optional search filter"},
        "limit": {"type": ["integer", "null"], "description": "Max results (default 50)"},
    },
    "required": []
}
```

For plugin packages, the schema is in the JSON config file under `"parameter"`, not in the class.

---

## In-memory caching (for large one-time fetches)

If your tool fetches a large index that rarely changes (e.g. a full catalog or reference dataset),
cache it at module level so subsequent calls within the same process are instant:

```python
from typing import Optional, List, Dict, Any

_cache: Optional[List[Dict[str, Any]]] = None

def _fetch_data(timeout: int = 30) -> List[Dict[str, Any]]:
    global _cache
    if _cache is None:
        import requests
        resp = requests.get("https://api.example.com/full-index", timeout=timeout)
        resp.raise_for_status()
        _cache = resp.json().get("items", [])
    return _cache

@register_tool("MyCachingTool")
class MyCachingTool(BaseTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        items = _fetch_data(self.timeout)
        # filter/search locally ...
        return {"status": "success", "data": results}
```

This avoids re-downloading on every `tu test` run and makes local search very fast.

---

## Using environment variables

```python
import os

def run(self, q: str) -> dict:
    api_key = os.environ.get("MY_API_KEY")
    if not api_key:
        return {"status": "error", "message": "MY_API_KEY not set in .tooluniverse/.env"}
    # ...
```

Set the value in `.tooluniverse/.env` (workspace) or export it in the shell (plugin packages).

---

## Multiple tools in one file

```python
from tooluniverse.tool_registry import register_tool

@register_tool
class MyAPI_search:
    name = "MyAPI_search"
    description = "..."
    input_schema = { ... }
    def run(self, q: str) -> dict: ...

@register_tool
class MyAPI_get_record:
    name = "MyAPI_get_record"
    description = "..."
    input_schema = { ... }
    def run(self, record_id: str) -> dict: ...
```

---

## Tagging for category search (Pattern 1)

Add a `category` class attribute to make the tool discoverable by `tu list --category`:

```python
@register_tool
class MyAPI_search:
    name = "MyAPI_search"
    category = ["my_domain", "search"]
    description = "..."
    ...
```

---

## Error handling pattern

```python
def run(self, q: str) -> dict:
    import requests
    try:
        resp = requests.get("https://api.example.com/search", params={"q": q}, timeout=30)
        resp.raise_for_status()
        return {"status": "success", "data": resp.json()}
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out"}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

---

## Return schema for tools with multiple output shapes

When a single tool returns different fields depending on inputs (e.g., an RC filter returns
`cutoff_frequency_Hz` but an LC filter returns `resonant_frequency_Hz`), use a loose schema
that only requires the fields common to all paths. Do not `require` fields that are absent in
some cases — schema validation will fail for those code paths even when the tool is correct:

```python
# In JSON config: only require fields that are always present
"return_schema": {
    "type": "object",
    "properties": {
        "topology": {"type": "string"},
        "formula":  {"type": "string"}
    }
    # No "required" list — or only fields that always appear
}
```

This is better than `oneOf` for tools that are one class with multiple dispatch paths, because
`oneOf` requires exactly one schema to match which can be fragile.

---

## Pure-computation tools (no HTTP)

Tools that perform local calculations (unit converters, color codes, checksum
calculators, etc.) follow the same pattern but skip the HTTP layer entirely.
Move the logic into standalone helper functions and call them from `run()`:

```python
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool
from typing import Dict, Any

def _compute(value: float) -> Dict[str, Any]:
    """Pure computation — no imports needed at module level."""
    result = value * 2  # replace with real logic
    return {"input": value, "output": result}


@register_tool("MyCalculatorTool")
class MyCalculatorTool(BaseTool):
    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.operation = tool_config.get("fields", {}).get("operation", "compute")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            value = float(arguments.get("value") or 0)
            result = _compute(value)
            return {
                "status": "success",
                "data": result,
                "metadata": {"note": "Runs offline — no network request."},
            }
        except Exception as e:
            return {"error": str(e)}
```

Key points for pure-computation tools:
- No `requests` import needed — the tool is always available even without internet
- Put logic in module-level helper functions; keep `run()` thin
- State the offline nature in the description and `metadata.note`
- No `timeout` parameter needed in `__init__`

### SI prefix formatting helper

A reusable pattern for formatting numbers with SI prefixes (Ω, V, A, F, etc.).
Always return the prefix without a trailing space so callers can append the unit
directly (`"4.7k" + "Ω"` → `"4.7kΩ"`, not `"4.7k Ω"`):

```python
def _fmt_si(value: float) -> str:
    """Return value with SI prefix, no unit. Append unit in caller."""
    abs_v = abs(value)
    if abs_v == 0:
        return "0"
    if abs_v >= 1e9:
        return f"{value / 1e9:.4g}G"
    if abs_v >= 1e6:
        return f"{value / 1e6:.4g}M"
    if abs_v >= 1e3:
        return f"{value / 1e3:.4g}k"
    if abs_v >= 1:
        return f"{value:.4g}"
    if abs_v >= 1e-3:
        return f"{value * 1e3:.4g}m"
    if abs_v >= 1e-6:
        return f"{value * 1e6:.4g}µ"
    if abs_v >= 1e-9:
        return f"{value * 1e9:.4g}n"
    return f"{value * 1e12:.4g}p"

# Usage:
formatted = _fmt_si(4700) + "Ω"   # "4.7kΩ"
formatted = _fmt_si(0.02) + "A"    # "20mA"
formatted = _fmt_si(0.000047) + "F" # "47µF"
```

The `:.4g` format gives 4 significant figures and drops trailing zeros automatically
(`4.700` → `4.7`, `100.0` → `100`).

**Gotcha — never pass a pre-scaled unit to a two-argument `_fmt_si(value, unit)` variant.**
Some existing circuit tools use a variant that takes the unit as a second argument and
appends it after the SI prefix. This only works correctly when the input value is in the
**base SI unit** (meters, ohms, volts, amps, farads, hertz). If you pass an already-scaled
value (e.g. width in mm) or a compound unit (e.g. `"mΩ/m"`), you will get double-prefixed
output:

```python
# WRONG — value is in mm, not metres; unit already contains "m"
_fmt_si(0.7814, "mm")  # → "781.4 mmm"   (triple-m!)

# CORRECT — value is in base SI unit (metres)
_fmt_si(0.0007814, "m")  # → "781.4 µm"

# CORRECT for non-SI-scalable compound units — just format directly
f"{resistance_mohm_per_m:.4g} mΩ/m"   # → "667.5 mΩ/m"
```

The unit-free variant above (returning only the prefixed number) is safer because the
caller always provides the unit explicitly at the call site, making the scale clear.

---

## Tools with no required parameters

When all parameters are optional (e.g., a "get current position" tool that takes no input),
set `"required": []` in the JSON config and add `{}` as a test example:

```json
{
  "parameter": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "test_examples": [{}]
}
```

`tu test` will call the tool with an empty dict `{}` and validate the result normally.

**Gotcha — `"required": []` does not mean "no runtime requirements".** Many calculator tools
set `"required": []` in the JSON schema (to avoid schema validation errors when callers omit
optional parameters) but still need certain params at runtime depending on the operation.
Check for missing required parameters in `run()` and return a clear error:

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    alpha = arguments.get("switching_activity")
    cap_F = arguments.get("capacitance_F")
    missing = [n for n, v in [("switching_activity", alpha), ("capacitance_F", cap_F)]
               if v is None]
    if missing:
        return {"status": "error",
                "message": f"Missing required parameters: {missing}"}
```

---

## Handling exponential computations safely

For tools like metastability calculators that use `e^x` with very large exponents
(e.g., x = T_res / τ can be 10–1000), clamp the exponent before calling `math.exp()`
to avoid `OverflowError` (which would produce an unhandled exception instead of a result):

```python
import math

log_mtbf = exponent - math.log(denominator)   # work in log space
mtbf = math.exp(min(log_mtbf, 700))           # cap at e^700 ≈ 10^304 before overflow

# For results requiring display, prefer log-domain representation
# when the value may exceed float max (~1.8e308):
if log_mtbf > 700:
    result["MTBF_note"] = f"MTBF > e^700 seconds (effectively infinite)"
```

Always work in log space first (`log_result = log_a - log_b + exponent`) and only convert
to linear (`math.exp(log_result)`) at the very end. This is standard practice for any
formula of the form `e^x / denom` where `x` can be large.

---

## Allowing R=0 in multi-segment RC networks

When a tool accepts a list of `[R, C]` segments representing an RC network, the **last
segment** often has R=0 (a pure load capacitance with no series resistance). Validate
using `r < 0` (reject negative) rather than `r <= 0` (reject zero):

```python
for i, seg in enumerate(segments):
    r, c = float(seg[0]), float(seg[1])
    if r < 0:       # NOT r <= 0: zero resistance is valid for load-only nodes
        raise ValueError(f"Segment {i}: R must be non-negative, got {r}")
    if c <= 0:      # C=0 is never physically meaningful
        raise ValueError(f"Segment {i}: C must be positive, got {c}")
```

---

## Dual-mode operation: fields.operation vs runtime argument

When a tool supports multiple operations, you have two choices for how the caller selects
the mode:

**Config-time dispatch (one tool per operation):** Set the mode via `"fields": {"operation": "..."}` in the JSON config. Each JSON entry becomes a separate tool with its own
name, description, and parameter list. The class reads `self.operation` from `__init__`.
This is the cleanest approach when operations have different parameters.

**Runtime dispatch (single tool, caller passes operation):** Expose `"operation"` as an
optional parameter in the JSON schema. Read it in `run()` with a fallback to `self.operation`:

```python
def __init__(self, tool_config):
    super().__init__(tool_config)
    self.operation = tool_config.get("fields", {}).get("operation", "solve_power")

def run(self, arguments):
    # Runtime arg overrides config-time default
    op = arguments.get("operation") or self.operation
    if op == "solve_power":
        ...
```

Use runtime dispatch when a single JSON tool entry covers all modes and the description
clearly explains all modes. Use config-time dispatch when different modes warrant different
parameter descriptions (e.g., `Circuit_dynamic_power` vs `Circuit_max_frequency`).

---

## Physical constants and preset lookup tables

Define physical constants and named preset tables at **module level** (not inside the
class), so they are available to helper functions and are easy to read and update:

```python
import math

# Physical constants
_MU0 = 4.0 * math.pi * 1e-7   # H/m — permeability of free space
_KB_EV = 8.617333e-5           # eV/K — Boltzmann constant

# Named preset table with physical values
_PACKAGE_THETA_JA: Dict[str, float] = {
    "sot-23":   200.0,   # °C/W
    "sot-223":   60.0,
    "to-220":    50.0,
    "tqfp-100":  35.0,
    "bga-256":   20.0,
}
```

In `run()`, resolve the parameter from: (1) explicit user value, (2) preset lookup, (3)
default. Always give a clear error if the preset name is unrecognised:

```python
def _resolve_theta(theta_ja, package):
    if theta_ja is not None:
        return float(theta_ja)
    if package is not None:
        key = package.lower().strip()
        if key in _PACKAGE_THETA_JA:
            return _PACKAGE_THETA_JA[key]
        raise ValueError(
            f"Unknown package '{package}'. Known: " + ", ".join(_PACKAGE_THETA_JA.keys())
        )
    raise ValueError("Provide theta_ja or a package name.")
```

Include the preset table in the `metadata` key of the return value so callers can
discover valid preset names without reading the source:

```python
return {
    "status": "success",
    "data": {...},
    "metadata": {
        "note": "Runs offline — no network request.",
        "package_presets": _PACKAGE_THETA_JA,
    },
}
```

---

## Required-parameter extraction helper

When a tool has several required parameters, a small helper avoids repetitive `None`
checks and gives a consistent error message:

```python
def _req_float(arguments: Dict[str, Any], key: str) -> float:
    v = arguments.get(key)
    if v is None:
        raise ValueError(f"Required parameter '{key}' is missing.")
    return float(v)

def _req_int(arguments: Dict[str, Any], key: str) -> int:
    v = arguments.get(key)
    if v is None:
        raise ValueError(f"Required parameter '{key}' is missing.")
    return int(float(v))   # accept "1000" or 1000.0 as well as 1000
```

Call these from `run()` inside the `try` block — they raise `ValueError` on missing
params, which is caught and returned as `{"status": "error", "message": ...}`:

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        current_A    = _req_float(arguments, "current_A")
        width_um     = _req_float(arguments, "width_um")
        num_stages   = _req_int(arguments, "num_stages")
        ...
    except ValueError as e:
        return {"status": "error", "message": str(e)}
```

---

## Significant-figure rounding for wide-range outputs

`round(x, N)` works well when the magnitude of `x` is known, but fails silently when
values can span many orders of magnitude — e.g., MTTF can range from milliseconds to
decades, and `round(0.00289, 1)` returns `0.0` (the value is lost entirely):

```python
>>> round(0.00289, 1)
0.0   # WRONG — looks like zero
```

For outputs that can span orders of magnitude, use a 4-significant-figure helper
instead of `round(x, N)`:

```python
import math

def _sig4(v: float) -> float:
    """Round to 4 significant figures; handles any magnitude."""
    if v == 0:
        return 0.0
    mag = math.floor(math.log10(abs(v)))
    return round(v, -int(mag) + 3)
```

```python
>>> _sig4(0.00289)
0.002887   # correct — 4 sig figs preserved
>>> _sig4(1234567)
1235000.0  # correct — 4 sig figs
>>> _sig4(26.088)
26.09      # correct
```

Use `_sig4()` for values like MTTF, inductance, safe current limits, and any other
quantity that could legitimately be anywhere from sub-nano to mega. Use `round(x, N)`
only when you know the output will always stay near a fixed scale.
