---
name: tu-run-tool
description: Execute a ToolUniverse tool with input validation, schema-aware retry, output parsing, and follow-up suggestions. Use instead of raw execute_tool when you want auto-correction of common parameter mistakes and a usable summary instead of raw API output.
argument-hint: "[tool_name] [arguments as JSON, or natural-language request]"
---

Execute the tool and return a usable result, not just the raw API blob: $ARGUMENTS

A direct `execute_tool` call is brittle: parameter name mistakes silently
fail, schema errors return cryptic messages, and the raw output is often
nested JSON the user has to dig through. Run the steps below.

## Process

### 1. Resolve the tool name

If the name in `$ARGUMENTS` is exact, proceed. If it's not in the registry
(case mismatch, typo, fuzzy guess), do NOT fail — call `find_tools` with the
intended topic and pick the closest match. Show the user what you matched
to before running it.

If the user gave a natural-language description instead of a tool name
("annotate this BRAF V600E variant"), pick the tool yourself via
`find_tools` then proceed.

### 2. Validate args BEFORE executing

Call `get_tool_info` on the resolved name. From the schema:
- Check every required param is present in the user's JSON.
- For each present param: type-coerce if the user passed a JSON-typed value
  that matches a string-shaped schema (a common mistake) — e.g.,
  `{"limit": "10"}` → `{"limit": 10}`.
- If the user passed an alias name (e.g., `gene` instead of `gene_symbol`),
  rename it. Common alias map: `gene↔gene_symbol`, `disease↔disease_name`,
  `id↔gene_id`, `query↔term`.
- If a required param is still missing AND the value is derivable from
  another arg the user passed (e.g., user passed `gene_symbol` but tool
  needs `ensembl_id`), call the upstream resolver tool first
  (`ensembl_lookup_gene` for this case), then retry.

### 3. Execute and handle outcomes

Call `execute_tool` with the cleaned args.

If the result has `status: "error"`:
- API key error → DO NOT retry. Tell the user the env var to set, suggest a
  fallback tool with no key requirement (use `find_tools` to identify one).
- Schema-validation error → re-read `get_tool_info`, re-clean the args once,
  retry once. After 1 retry, stop.
- Empty result for a known-good query → mention that the database returned
  nothing for this input; suggest a more permissive query (broaden a filter,
  drop a strict-match field).
- Transient/network error (5xx, timeout) → retry once with the same args.

### 4. Parse output, don't dump

Take the `data` field and produce a readable result, NOT the JSON blob.

For tabular results (mutation lists, drug lists, gene hits): present a
markdown table with the 3-5 most useful columns, plus a "from N total" note.

For single-record lookups (gene info, drug info): bullet-list the 5-10
most relevant fields. Include the IDs needed for follow-up calls.

For free-form text (literature abstracts, descriptions): include directly
but with a 200-word cap per item.

Always include the database name, query date if returned, and the count of
records returned.

### 5. Suggest follow-ups

End the response with 1-3 concrete next-tool suggestions based on what came
back. Examples:
- Got Ensembl IDs → "to expand, run `tu run ensembl_lookup_gene '{...}'`"
- Got disease IDs → "to find drug candidates, run `tu run DGIdb_get_drug_gene_interactions '{...}'`"
- Got an OMIM number → "for variants, run `tu run ClinVar_search_variants '{...}'`"

Skip this step if the user's request is clearly a one-shot factoid lookup.

## When to bypass this command

If the agent already knows the exact tool and exact args and just needs raw
output (e.g., inside a longer scripted pipeline), call `execute_tool` directly
or use `tu run` in Bash. This command earns its weight on ad-hoc calls where
the human is exploring.
