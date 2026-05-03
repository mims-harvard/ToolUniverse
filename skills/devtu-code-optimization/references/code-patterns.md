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
