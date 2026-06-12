# JSON Tool Config Reference

## Minimal example

```json
[
  {
    "name": "MyAPI_search",
    "description": "...",
    "type": "BaseRESTTool",
    "fields": { "endpoint": "https://api.example.com/search" },
    "parameter": {
      "type": "object",
      "properties": {
        "q": { "type": "string", "description": "Search query" }
      },
      "required": ["q"]
    }
  }
]
```

## All fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique tool identifier. Convention: `ProviderName_action` (e.g., `MyAPI_search`) |
| `description` | Yes | What the tool does and returns. Be specific — the AI uses this to decide when to call the tool. |
| `type` | Yes | `"BaseRESTTool"` for workspace REST tools; or the class name string passed to `@register_tool("ClassName")` for plugin package tools |
| `fields.endpoint` | Yes (BaseRESTTool only) | The API endpoint URL. Only required when `"type"` is `"BaseRESTTool"`. |
| `parameter` | Yes | JSON Schema object for the tool's input parameters |
| `fields.method` | No | HTTP method: `"GET"` (default) or `"POST"` |
| `fields.headers` | No | Static headers as key-value pairs |
| `fields` | No (plugin) | Any key-value pairs passed to `__init__` as `tool_config["fields"]`. Commonly `"operation"` is used to route multiple tools from one class. |
| `test_examples` | No | List of example argument dicts — used automatically by `tu test <tool_name>` |
| `return_schema` | No | JSON Schema for the response data — validated automatically by `tu test` |
| `tags` | No | List of category tags (e.g., `["genomics", "search"]`) |

## Parameter types

```json
"properties": {
  "required_string":  { "type": "string",  "description": "..." },
  "optional_int":     { "type": ["integer", "null"], "description": "..." },
  "optional_string":  { "type": ["string", "null"],  "description": "..." },
  "optional_boolean": { "type": ["boolean", "null"], "description": "..." }
}
```

Mark optional params with `["type", "null"]` — omit them from `"required"`.

If a tool has no required parameters, use `"required": []` (not omitting the key):

```json
"parameter": {
  "type": "object",
  "properties": {
    "query": { "type": ["string", "null"], "description": "Optional search term" },
    "limit": { "type": ["integer", "null"], "description": "Max results" }
  },
  "required": []
}
```

## POST example

```json
{
  "name": "MyAPI_submit",
  "description": "Submit a job to the processing queue. Returns job_id.",
  "type": "BaseRESTTool",
  "fields": {
    "endpoint": "https://api.example.com/jobs",
    "method": "POST",
    "headers": { "Content-Type": "application/json" }
  },
  "parameter": {
    "type": "object",
    "properties": {
      "input": { "type": "string", "description": "Input data to process" },
      "priority": { "type": ["integer", "null"], "description": "Job priority 1-10" }
    },
    "required": ["input"]
  },
  "test_examples": [
    { "input": "sample data", "priority": 5 }
  ]
}
```

## Authentication

For APIs requiring API keys, add them as a header. Store the key value in `.tooluniverse/.env`, not the JSON:

```json
"fields": {
  "endpoint": "https://api.example.com/search",
  "headers": { "Authorization": "Bearer ${MY_API_KEY}" }
}
```

`.tooluniverse/.env`:
```
MY_API_KEY=your-actual-key-here
```

## return_schema

Describes the structure of `result["data"]`. `tu test` validates every result against this schema
automatically — no extra config needed. Use JSON Schema format.

**Critical:** The schema must match the type of what your `run()` puts under the `"data"` key —
not the full response dict. Most search tools return a list, so the top-level type is `"array"`:

```json
{
  "name": "MyAPI_search",
  ...
  "test_examples": [{"q": "test"}],
  "return_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "id":    { "type": "string" },
        "title": { "type": "string" },
        "score": { "type": "number" }
      },
      "required": ["id", "title"]
    }
  }
}
```

If `data` is a single object (e.g. `get` / `lookup` operations):

```json
"return_schema": {
  "type": "object",
  "properties": {
    "id":    { "type": "string" },
    "title": { "type": "string" }
  },
  "required": ["id"]
}
```

If the API can return multiple shapes (success vs error), use `oneOf`:

```json
"return_schema": {
  "oneOf": [
    {
      "type": "array",
      "items": { "type": "object" }
    },
    {
      "type": "object",
      "properties": { "error": { "type": "string" } },
      "required": ["error"]
    }
  ]
}
```

Note: `return_schema` validation only runs when `result["status"] == "success"`, so
error responses (which don't have a `"data"` key) are skipped automatically.

**Gotcha:** An empty array `[]` satisfies `"type": "array"` and passes schema validation. Make
sure `test_examples` use arguments that actually return non-empty results, otherwise a broken
tool will pass all tests silently.

**Gotcha (tools with multiple output shapes):** If your tool returns different fields depending
on the inputs (e.g., `filter_type: RC` returns `cutoff_frequency_Hz` but `filter_type: LC`
returns `resonant_frequency_Hz`), only `require` fields that are present in ALL execution paths.
Adding a field to `required` that only appears in some paths will cause schema validation to
fail for the other paths. Use a loose schema (no `required` list, or a minimal one) for
dispatch-style tools.

**Verify test_examples with Python before writing them.** Use `urllib` rather than `curl` — it
matches what the tool will actually do and handles edge cases like redirects more visibly:

```python
import urllib.request, json
with urllib.request.urlopen("https://api.example.com/search?q=test") as r:
    print(json.dumps(json.loads(r.read()), indent=2))
```

Some search APIs use `intitle`-style matching where all words must appear literally in a title
or name field — overly specific queries like `"I2C pull-up resistor value"` can return 0 results
even when the tool is working. Use 2-4 key words that reliably appear in real content
(e.g., `"pull-up resistor"` instead).

**Verify the URL is a real JSON endpoint.** Some URLs that look like REST APIs
(e.g., `https://certification.example.org/api/projects`) may redirect to a static HTML page.
A urllib fetch will show you the Content-Type and body immediately, before you write any code.

## Multiple tools in one file

```json
[
  { "name": "MyAPI_search", ... },
  { "name": "MyAPI_get_record", ... },
  { "name": "MyAPI_list_collections", ... }
]
```

## Offline tools with an operation parameter

For pure-computation tools that handle multiple operations in a single Python class,
you have two design choices:

**Choice A — Single tool, user passes `operation` as a parameter:**
The JSON config exposes `operation` as a parameter property. One tool, one JSON entry,
user chooses the mode at call time.

```json
{
  "name": "Circuit_wire_gauge",
  "type": "WireGaugeTool",
  "parameter": {
    "type": "object",
    "properties": {
      "operation": {
        "type": ["string", "null"],
        "description": "Operation: 'from_current' (default) or 'from_awg'."
      },
      "current_A": { "type": ["number", "null"], "description": "..." },
      "awg":       { "type": ["number", "null"], "description": "..." }
    },
    "required": []
  }
}
```

Use this when the operations share most parameters and the distinction is a simple mode switch.

**Choice B — Multiple tools, each backed by the same class via `fields.operation`:**
Each JSON entry is a separate tool with its own name, description, and parameters.
The Python class reads `self.operation = tool_config["fields"]["operation"]` in `__init__`.

```json
[
  { "name": "Circuit_wire_from_current", "type": "WireGaugeTool",
    "fields": {"operation": "from_current"}, "parameter": { ... only current_A, ambient_C ... } },
  { "name": "Circuit_wire_from_awg",     "type": "WireGaugeTool",
    "fields": {"operation": "from_awg"},     "parameter": { ... only awg, temp_C ... } }
]
```

Use this when the operations have very different parameters or descriptions — it gives the AI
cleaner, more targeted tool choices.

---

## Array-of-arrays parameters

When a tool accepts a list of structured items (e.g., RC network segments, waypoints,
coefficient lists), use `"type": ["array", "null"]` with an `"items"` schema:

```json
"segments": {
  "type": ["array", "null"],
  "description": "List of [R_i, C_i] pairs from driver to load. Each R_i in ohms, C_i in farads. Example: [[100, 50e-15], [200, 50e-15], [0, 100e-15]].",
  "items": {
    "type": "array",
    "items": { "type": "number" },
    "minItems": 2,
    "maxItems": 2
  }
}
```

Always include a concrete example in the description (e.g., `[[100, 50e-15], ...]`) — the AI
needs to see the expected format. Use `test_examples` that exercise a non-trivial list:

```json
"test_examples": [
  {"mode": "chain", "segments": [[100, 50e-15], [200, 50e-15], [0, 100e-15]]}
]
```

The final segment often has R=0 (pure load capacitance). In the Python class, validate
with `r < 0` (reject negative R) rather than `r <= 0` to allow load-only segments.
