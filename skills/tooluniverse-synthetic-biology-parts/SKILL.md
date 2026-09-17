---
name: tooluniverse-synthetic-biology-parts
description: Look up synthetic biology genetic parts (promoters, RBS, CDS/genes, terminators, reporters, composite devices) from the SynBioHub repository, including the iGEM Registry of Standard Biological Parts. Use when someone asks to "find a genetic part", "look up a BioBrick", "search SynBioHub", "get the sequence for BBa_...", "browse iGEM part collections", "find a promoter/RBS/terminator for a genetic circuit", or "what parts are available for [organism/function]". NOT for plasmid backbone/vector lookup by catalog ID (use tooluniverse-molecular-cloning's Addgene coverage), NOT for primer design once a part sequence is chosen (use tooluniverse-primer-design). Honest: SynBioHub disabled anonymous public REST access upstream — every unauthenticated call currently returns 401/HTML-login-page, verified live. This skill explains that limitation plainly and how to unlock real access (SYNBIOHUB_API_TOKEN) rather than pretending the tools work with no setup.
disable-model-invocation: true
---

# Synthetic Biology Parts Lookup (SynBioHub)

Search and retrieve genetic parts — promoters, ribosome binding sites (RBS),
coding sequences, terminators, reporters, and composite genetic devices —
from SynBioHub, the standard synthetic-biology parts repository that hosts
the iGEM Registry of Standard Biological Parts (20,000+ BioBricks), CIDAR
Lab parts, Free Genes libraries, and other public SBOL collections.

## Honesty contract (read first) — verify auth status before promising results

**Live-verified as of this writing: every anonymous call to all 3 tools below
fails.** SynBioHub disabled anonymous access to its public REST endpoints
upstream. Confirmed by actually running each tool with no token set:

```
$ tu run SynBioHub_get_collections '{}'
Error: SynBioHub API HTTP error: 401 (login required). synbiohub.org now
requires an authenticated session for this endpoint (no SYNBIOHUB_API_TOKEN
is set). Log in at synbiohub.org, then set SYNBIOHUB_API_TOKEN to the
session token to retry.

$ tu run SynBioHub_search_parts '{"query": "GFP"}'
Error: SynBioHub API HTTP error: 401 (login required). ...

$ tu run SynBioHub_get_part '{"display_id": "BBa_E0040"}'
Error: SynBioHub did not return SBOL/XML data for
'https://synbiohub.org/public/igem/BBa_E0040/1' (got non-XML content, likely
an HTML login or error page). The part may not exist, or SynBioHub may now
require authentication for this request.
```

**Before using this skill, always try one call first** (e.g.
`SynBioHub_get_collections` with no arguments — cheapest possible check).
If it returns a 401/login-required error:

1. Tell the user plainly: SynBioHub now requires authentication for these
   reads; this is an upstream policy change, not a bug in the request.
2. Point them to create a free account at https://synbiohub.org, log in,
   and retrieve a session token, then set `SYNBIOHUB_API_TOKEN` in the
   environment before retrying.
3. **Never fabricate a part record, sequence, or collection list** to work
   around the error. If the token isn't available, say the lookup cannot
   be completed right now — do not guess a BioBrick's sequence from
   training-data memory and present it as a live SynBioHub result.

If a valid `SYNBIOHUB_API_TOKEN` is set and the call succeeds, proceed with
the workflow below using the real returned data.

## When to Use This Skill

Apply when users:
- Want to find a genetic part by function (promoter, RBS, terminator, CDS,
  reporter) or by keyword (gene name, biological description)
- Have a BioBrick ID (e.g. `BBa_E0040`) or a SynBioHub part URI and want its
  sequence, role, and provenance
- Want to browse what part collections/libraries exist on SynBioHub before
  searching (iGEM Registry, CIDAR Lab, Free Genes, organism-specific sets)
- Are assembling a genetic circuit and need to identify candidate parts
  (promoter + RBS + CDS + terminator) before moving to cloning/plasmid design

**NOT for** (route elsewhere):
- Plasmid backbone/vector catalog lookup by Addgene ID — the registry has
  `Addgene_search_plasmids`, `Addgene_get_plasmid`, `Addgene_search_depositors`
  (`src/tooluniverse/data/addgene_tools.json`) for this. These only appear in
  `tu list` once an `ADDGENE_API_KEY` environment variable is set (ToolUniverse
  deliberately hides any tool with unmet `required_api_keys` until the key is
  present — verified, not a bug); register for a free key at
  https://developers.addgene.org/ if it's missing.
- Cloning workflow steps (restriction sites, Gibson/Golden Gate assembly
  planning) once parts are chosen -> `tooluniverse-molecular-cloning`
- Primer design for amplifying a chosen part/sequence ->
  `tooluniverse-primer-design`

## Workflow

### 1. Browse available collections (optional starting point)

```
SynBioHub_get_collections {}
```

No parameters. Returns collection `name`, `description`, `display_id`,
`uri`, `version`, and `member_count` for every public collection (iGEM
Registry, CIDAR Lab parts, Free Genes, organism-specific sets, etc.) —
useful when the user wants to know what's searchable before committing to
a query.

### 2. Search for a part by keyword

```
SynBioHub_search_parts {"query": "<keyword>", "limit": <1-50, default 10>, "offset": <int, default 0>}
```

`query` accepts gene names, functional descriptions, or BioBrick IDs —
e.g. `"GFP"`, `"lac promoter"`, `"BBa_E0040"`, `"terminator"`,
`"riboswitch"`, `"CRISPR"`, `"T7 promoter"`. Returns an array of candidate
parts, each with `display_id`, `name`, `description`, `uri` (feed this
into step 3), `version`, `sbol_type` (e.g. `ComponentDefinition`), and
`role` (`promoter`, `CDS`, `terminator`, `RBS`, etc.).

When narrowing a search (e.g. by organism or exact function), refine the
query text itself — there is no separate organism/role filter parameter.
If the first query is too broad, tighten the keyword and re-search rather
than trying to filter client-side on an incomplete result page.

### 3. Get full detail for one part

```
SynBioHub_get_part {"display_id": "<BioBrick ID>"}
# or, for parts outside the iGEM collection:
SynBioHub_get_part {"part_uri": "<uri from step 2's search results>"}
```

Exactly one of `display_id` or `part_uri` should be supplied (`display_id`
for iGEM BioBricks like `BBa_E0040`, `part_uri` for anything else — take
the `uri` field straight from a `SynBioHub_search_parts` result). Returns
`title`, `description`, `type` (SBOL biological type, e.g. `DnaRegion`),
`role` (array of SO terms / iGEM part types), `sequence` (first 500 bp —
note this is truncated, not the full sequence, for long parts),
`sequence_length` (the true full length), `created`/`modified` dates, and
`derived_from` (original source URI, e.g. the iGEM registry page).

**`sequence` is capped at 500 characters.** For a part longer than that,
report `sequence_length` honestly and say the returned `sequence` field is
a prefix, not the complete sequence — do not imply completeness.

## Downstream Handoff

Once parts are identified: move to `tooluniverse-molecular-cloning` for
assembly planning (Gibson/Golden Gate/restriction-based cloning of the
chosen parts into a vector) and `tooluniverse-primer-design` for
amplification primers.

## Reference

- `references/synbiohub_tool_reference.md` — full parameter/response
  tables for all 3 tools, plus the exact live error text observed when
  testing this skill (for future maintainers to recognize the same
  failure mode).
