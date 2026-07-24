# Code Patterns Reference

Reusable implementation patterns for ToolUniverse tool development.

## Schema Patterns

### return_schema with oneOf (required)

```json
{
  "return_schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "data": {"type": "object"},
          "metadata": {"type": "object"}
        }
      },
      {
        "type": "object",
        "properties": {
          "error": {"type": "string"}
        }
      }
    ]
  }
}
```

### Nullable fields

```json
{"type": ["array", "null"]}
{"type": ["string", "null"]}
```

## API Call Patterns

### Client-Side Filter (when API ignores params)

```python
results = api_call(base_params_only)
if interaction_types:
    results = [r for r in results if r.get("type") in interaction_types]
if sources:
    results = [r for r in results if r.get("source") in sources]
```

### Fallback Lookup

```python
precise = api_call(geneSymbol=gene_symbol)
if not precise:
    precise = api_call(name=gene_symbol)
```

### Client-Side Pagination (when API ignores size/page)

```python
all_items = api_call()
start = page * size
return all_items[start:start + size]
```

### PostgREST Join

```python
url = f"{base}/recommendation?select=*,drug(name)&genesymbol={_postgrest_eq(gene)}"
```

## Output Patterns

### Normalization Disclosure

```python
_norm_parts = []
if original != normalized:
    _norm_parts.append(f"'{original}' → '{normalized}' (reason)")
if _norm_parts:
    result["normalization_note"] = "Auto-normalized: " + "; ".join(_norm_parts)
```

### Truncation at Top Level

```python
response = {"status": "success", "data": data[:limit]}
if len(data) > limit:
    response["truncated"] = True
    response["truncation_note"] = (
        f"Returning {limit} of {len(data)}. "
        f"Pass max_results={len(data)} for full data."
    )
```

### No-Data vs Bad-Query

```python
if count == 0 and query:
    result["hint"] = f"No results for '{query}'. Try a broader term or check spelling."
elif count == 0:
    result["hint"] = "No data available for this entity."
```

## Hosted Model-API Tools (NVIDIA NIM-style)

### Async poll host = the invocation host
Poll a 202 job-status on the SAME gateway you POSTed to. NVCF biology NIMs invoke
**and** poll on `health.api.nvidia.com`; `integrate.api.nvidia.com` serves only the
OpenAI-compatible LLM endpoints and has **no** `/v1/status` route.

```python
host = urlparse(self.base_url).netloc          # e.g. health.api.nvidia.com
poll_url = f"https://{host}/v1/status/{req_id}"
```

### Route-existence probe (find/verify hosted endpoints)
Plain-text `404 page not found` = route does NOT exist; a structured
`{"status":404,...}` (or 400/422/200) = route exists. Use the live API to confirm a
model is hosted and to find the right slug before wrapping it.

### Unwrap JSON envelopes around the "raw" payload
Some endpoints return `{"pdbs": ["...ATOM..."]}` even when response_type is `pdb`.
Unwrap to the inner value so the field matches the schema (real PDB, not a JSON blob).

### HTTP 200 with an inner failure
A 200 can carry `{"status": "failed", ...}` (e.g. DiffDock with an unreadable
ligand). Surface it as an error — but only on explicit `failed/error/errored`; an
inner `status:"success"` must stay a success (don't over-match).

### 404 "not found for account" ≠ wrong path
A gated/unprovisioned model returns a 404 whose body says "Not found for account".
Report "model not available for your account" rather than "endpoint not found".

### Retry a longer poll window before declaring "broken"
A heavy async job can return 504 / `nvcf-status: errored` simply because
`NVCF-POLL-SECONDS` was shorter than its runtime. Only a *persistent* 400
`DEGRADED`/error across retries is a real outage. 5xx bodies are often empty —
surface `nvcf-status` / `nvcf-reqid` from the headers instead.

### Model-variant selection via templated endpoint
Expose multiple hosted sizes through one tool: a `{placeholder}` in the endpoint +
`fields.path_params` default, filled from the request arg (sanitized slug) and
stripped from the request body.

```python
# endpoint "arc/{model}/generate", path_params {"model": "evo2-40b"}
value = args.get(key) or default
if not re.fullmatch(r"[A-Za-z0-9._-]+", str(value)):  # no path injection
    value = default
endpoint = endpoint.replace("{" + key + "}", value)
```

## R-subprocess Tools

### Run a script file, not `Rscript -e <string>`
`Rscript -e` collapses one backslash level before R parses it, so a regex literal
like `sub("\\..*", ...)` becomes `sub("\..*", ...)` and R aborts with
`'\.' is an unrecognized escape`. Write the script to a temp `.R` file and run
`Rscript <file>` (parsed verbatim); always remove the temp file, incl. on timeout.

```python
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False)
try:
    tmp.write(r_script); tmp.close()
    return subprocess.run(["Rscript", tmp.name], capture_output=True, text=True, timeout=t)
finally:
    try: os.unlink(tmp.name)
    except OSError: pass
```

## try/except Indentation (Critical)

```python
# CORRECT
try:
    resp = requests.get(url)
    data = resp.json()
except Exception as e:
    return {"status": "error", "error": str(e)}

# WRONG — SyntaxError
try:
    resp = requests.get(url)
if resp.ok:        # ← same indent as try: → OUTSIDE try block
    data = resp.json()
except Exception:  # ← Python: "try without except"
    pass
```

Every `try:` must have `except:` at the **exact same indentation level**.

## Multi-Word Search Hint

```python
if result["count"] == 0 and name_q and " " in str(name_q):
    first_word = str(name_q).split()[0]
    result["multi_word_hint"] = (
        f"Search may not match multi-word phrases like '{name_q}'. "
        f"Try a single keyword: name='{first_word}'."
    )
```
