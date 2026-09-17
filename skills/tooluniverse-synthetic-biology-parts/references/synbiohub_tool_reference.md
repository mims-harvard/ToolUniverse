# SynBioHub Tool Reference

Source: `src/tooluniverse/data/synbiohub_tools.json`. All three tools are
type `SynBioHubTool`. `test_examples` is empty `[]` in the JSON for all
three — there is no baked-in canned example, so `tu test <name>` reports
"No test_examples found" rather than exercising the tool; use `tu run`
with explicit arguments instead (see below).

## Current live status (verified, not assumed)

Tested on this date with no `SYNBIOHUB_API_TOKEN` set:

```
$ tu run SynBioHub_get_collections '{}'
Error: SynBioHub API HTTP error: 401 (login required). synbiohub.org now
requires an authenticated session for this endpoint (no SYNBIOHUB_API_TOKEN
is set). Log in at synbiohub.org, then set SYNBIOHUB_API_TOKEN to the
session token to retry.

$ tu run SynBioHub_search_parts '{"query": "GFP"}'
Error: SynBioHub API HTTP error: 401 (login required). synbiohub.org now
requires an authenticated session for this endpoint (no SYNBIOHUB_API_TOKEN
is set). Log in at synbiohub.org, then set SYNBIOHUB_API_TOKEN to the
session token to retry.

$ tu run SynBioHub_search_parts '{"query": "lac promoter", "limit": 5}'
Error: SynBioHub API HTTP error: 401 (login required). synbiohub.org now
requires an authenticated session for this endpoint (no SYNBIOHUB_API_TOKEN
is set). Log in at synbiohub.org, then set SYNBIOHUB_API_TOKEN to the
session token to retry.

$ tu run SynBioHub_get_part '{"display_id": "BBa_E0040"}'
Error: SynBioHub did not return SBOL/XML data for
'https://synbiohub.org/public/igem/BBa_E0040/1' (got non-XML content,
likely an HTML login or error page). The part may not exist, or
SynBioHub may now require authentication for this request.

$ tu run SynBioHub_get_part '{"part_uri": "https://synbiohub.org/public/igem/BBa_E0040/1"}'
Error: SynBioHub did not return SBOL/XML data for
'https://synbiohub.org/public/igem/BBa_E0040/1' (got non-XML content,
likely an HTML login or error page). The part may not exist, or
SynBioHub may now require authentication for this request.
```

This matches the warning already present in each tool's own JSON
`description` field ("SynBioHub anonymous REST access was disabled
upstream. Every /public/... read returns 401 'Login required'."), so the
tools' own authors were already aware of this at write time — it is a
known, documented upstream limitation, not a regression to fix here.

**Implication for this skill:** every documented parameter/response shape
below comes from reading the tool's JSON schema (`parameter` and
`return_schema`), NOT from a live successful response, because no live
successful response was obtainable without a token in this environment.
If a `SYNBIOHUB_API_TOKEN` becomes available, re-verify actual returned
field values before treating this reference as ground truth beyond field
*names* and *types*.

## SynBioHub_get_collections

- **Parameters:** none (`{}`).
- **Returns (per schema):** array of objects — `name`, `description`,
  `display_id`, `uri`, `version`, `member_count` (all nullable strings
  except `member_count`, an integer).
- **Purpose:** discover what part libraries exist (iGEM Registry, CIDAR
  Lab, Free Genes, organism-specific collections) before searching.

## SynBioHub_search_parts

- **Parameters:** `query` (string, required — gene name, function,
  BioBrick ID, or description); `offset` (int, optional, default 0);
  `limit` (int, optional, default 10, max 50).
- **Returns (per schema):** array of objects — `display_id`, `name`,
  `description`, `uri` (feed into `SynBioHub_get_part`'s `part_uri`),
  `version`, `sbol_type` (e.g. `ComponentDefinition`, `Sequence`), `role`
  (e.g. `promoter`, `CDS`, `terminator`, `RBS`).
- **Example queries from the tool's own description:** `"GFP"` (green
  fluorescent protein parts), `"lac promoter"` (lac operon regulatory
  parts), `"BBa_E0040"`, `"terminator"`, `"riboswitch"`, `"CRISPR"`,
  `"T7 promoter"`.

## SynBioHub_get_part

- **Parameters:** exactly one of `display_id` (string, e.g. `BBa_E0040`
  for iGEM BioBricks) or `part_uri` (string, full SynBioHub URI, e.g.
  `https://synbiohub.org/public/igem/BBa_E0040/1` — typically taken from
  a search result's `uri` field). Both are individually optional/nullable
  in the schema but at least one is needed for a meaningful lookup.
- **Returns (per schema):** object — `display_id`, `title`, `description`,
  `type` (SBOL biological type, e.g. `DnaRegion`), `role` (array of SO
  terms / iGEM part types), `sequence` (**first 500 characters only** —
  explicitly documented as truncated in the schema description),
  `sequence_length` (integer, the true full length), `created`,
  `modified` (dates), `derived_from` (original source URI, e.g. an iGEM
  registry page).
- **Known worked example from the tool's own description (unverified
  live, since auth blocked the call):** `BBa_E0040` is described as the
  GFP coding sequence, 720 bp.

## Cross-referenced but out-of-scope findings

- `src/tooluniverse/data/addgene_tools.json` defines `Addgene_search_plasmids`,
  `Addgene_get_plasmid`, `Addgene_search_depositors` for plasmid-level (not
  BioBrick-part-level) lookups. `tu list | grep -i addgene` returns no
  results with no `ADDGENE_API_KEY` set — **this is intentional, not a bug**:
  `execute_function.py`'s loader deliberately excludes any tool with a
  `required_api_keys` entry from `all_tools`/`tu list` until that key is
  present in the environment (verified: setting a dummy
  `ADDGENE_API_KEY=...` before `load_tools()` makes all 3 Addgene tools
  appear immediately). Set `ADDGENE_API_KEY` (free registration at
  https://developers.addgene.org/) to use Addgene lookups alongside this
  skill. SynBioHub's tools don't declare `required_api_keys` in their JSON,
  which is why they load unconditionally but fail at call time instead —
  a different (also legitimate) gating style for the same underlying
  problem.
- `tooluniverse-molecular-cloning` and `tooluniverse-primer-design` do not
  currently mention SynBioHub or Addgene by name (checked via grep) — this
  new skill is the first to document the SynBioHub tool family.
