---
name: tu-find-tools
description: Multi-hop tool discovery for a research goal. Decomposes the goal into sub-questions, searches the catalog for each, follows tool-to-tool links, and returns a structured toolkit ready to use. Use when you need ALL the tools to answer a research question, not just a keyword match.
argument-hint: "[research goal, e.g. 'drug candidates for Alzheimer's', 'BRAF V600E precision oncology pipeline']"
---

Discover the complete toolkit needed to answer this research goal: $ARGUMENTS

A single `find_tools` keyword search is rarely enough. Real research goals need
tools across multiple databases, and the right tool often shares no vocabulary
with the question. Run a discovery PROCESS, not a one-shot search.

## Process (do all five steps)

### 1. Decompose the goal into 2-5 sub-questions

For "drug candidates for Alzheimer's", sub-questions might be:
- What targets are validated for Alzheimer's? (gene-disease association)
- What drugs hit those targets? (drug-target interactions)
- What clinical trials are running? (trials registry)
- What safety signals exist? (adverse events)
- What pathways do these drugs perturb? (pathway enrichment)

Write the sub-questions out before searching.

### 2. Search the catalog for each sub-question independently

Run `find_tools` (MCP) once per sub-question with topic-specific terms — NOT
the original goal verbatim. Use synonyms a database author would pick:

```
find_tools("disease gene association")
find_tools("drug target interaction")
find_tools("clinical trial search")
find_tools("adverse event drug")
find_tools("pathway enrichment gene list")
```

If a search returns <3 hits, try a related concept (e.g., "drug indication"
instead of "drug repurposing"). If it returns >20 hits, narrow with a
specifier (e.g., "drug target interaction TCRD").

### 3. Multi-hop: follow tool-to-tool links

After collecting candidates, read their `description` fields via
`get_tool_info`. Many descriptions reference companion tools — e.g.,
"returns Ensembl IDs (use ensembl_lookup_gene to expand)" or "for clinical
significance see ClinVar_search_variants". Follow those references and add
the linked tools to your candidate set even if the keyword search missed them.

Repeat once: read the description of each newly-added tool to find their
companions. Stop after this second hop — diminishing returns beyond that.

### 4. Cross-check: does each candidate actually return what's needed?

Before adding a tool to the final toolkit:
- Read its `parameters` — are the required inputs available, or do you need
  another tool to produce them first? (e.g., a tool needing Ensembl ID needs
  `ensembl_lookup_gene` upstream)
- Read its `return_schema` — does it return the FACT type the sub-question
  asks for, or does it return raw data that needs more processing?
- Drop tools that are wrappers for the same API as another candidate (keep
  the more general one).

### 5. Output: structured toolkit grouped by sub-question

Don't dump a flat list. Format like this so the user can act on it:

```
## Sub-question 1: <text>
| Tool | API | Required input | Returns | Order |
|---|---|---|---|---|
| tool_A | OpenTargets | gene_symbol | ranked diseases | 1st |
| tool_B | DisGeNET | disease_name | gene list | 2nd (alternate) |

## Sub-question 2: <text>
...

## Suggested call order
1. `tool_A` with the disease name → list of targets
2. For each target: `tool_C` → drug list
3. `tool_D` per drug → trials
...
```

If the user only wanted a flat list (e.g., "what tools mention pathway"),
the keyword-search shortcut is fine and you can skip steps 1, 4, 5. But the
default behavior of this command is the full discovery process — that's its
value over plain `find_tools`.

## Stop conditions

- Stop adding sub-questions after 5 — beyond that, the user should
  re-run the command with a tighter goal.
- Stop multi-hop expansion after 2 hops.
- If `find_tools` returns no relevant hits across 3 different keyword sets
  for a sub-question, mark that sub-question as "no tool coverage" in the
  output — don't fabricate.
