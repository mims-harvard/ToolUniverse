---
name: research
description: Conduct a multi-database scientific research investigation inline in the current chat. Same operating discipline as the /tooluniverse:researcher agent (look up specific claims, cross-validate, honest INDETERMINATE) — but runs in this conversation so you can watch each step, follow up, and refine, instead of receiving a single summary from a forked subagent. Use when you want to drive the research yourself with ToolUniverse rather than delegating to a subagent.
argument-hint: "[research question, e.g. 'FDA-approved indications of metformin' or 'KRAS G12C resistance mechanisms']"
---

Research the following using ToolUniverse: $ARGUMENTS

## Operating Rules

1. **Look up specific claims; don't guess them.** For exact counts, p-values, database records, drug approvals, variant annotations, pathway memberships — call a tool. Memory is only for textbook-level background.
2. **Don't search for tools you already have.** For the common tools in the "Anchor Tools" section below, call them directly. For anything else, run `find_tools("topic")` once, then `get_tool_info(name)` once. If those two steps don't surface a usable tool, stop searching and answer from sources you do have.
3. **Cross-validate high-stakes facts.** For claims someone will publish, cite, or act on, check at least 2 independent databases (different upstream maintainers, not different tools wrapping the same API). State agreement or disagreement explicitly.
4. **An honest "INDETERMINATE" beats a confident wrong answer.** If the question can't be settled from available sources, say so and explain what's missing. Don't fill gaps with plausible-sounding inferences the user may mistake for verified facts.
5. **For data-file analysis (CSV, TSV, h5ad, VCF, FASTA, tree files, etc.), route to the matching ToolUniverse skill before writing code:**

   ```
   Skill('tooluniverse')   # loads the router, which dispatches to the specialized skill
   ```

   The skills encode discovered analysis conventions (which library, which filter, which denominator) that ad-hoc code often gets wrong. Do not re-derive conventions inside this chat.

## Workflow

1. **Plan**: state which tools or skills you'll need before calling them.
2. **Execute**: call tools or skills directly. For batches of 5+ similar queries, use the Python SDK pattern (see below) — `subprocess.run(["tu", "run", ...])` per call reloads the registry every time.
3. **Analyze**: when post-processing is needed, write Python via Bash and read the output.
4. **Validate**: cross-check key findings against a second source.
5. **Report**: actual numbers, source databases cited, dates retrieved, and an INDETERMINATE verdict where the evidence won't settle.

The user is in this conversation and can interrupt — pause for clarification if a key step depends on a choice the user should make (e.g., which species, which disease subtype, which time window).

## Anchor Tools

Call these directly via `execute_tool`. For anything else, use `find_tools` once.

| Domain | Tool | Example arguments |
|---|---|---|
| Gene → all IDs (Ensembl/UniProt/NCBI/RefSeq/MGI) | `MyGene_query_genes` | `{"q": "BRAF", "species": "human"}` |
| Cancer drivers | `IntOGen_get_drivers` | `{"cancer_type": "BRCA"}` |
| Mutation freq (pan-cancer) | `GDC_get_mutation_frequency` | `{"gene_symbol": "TP53"}` |
| Drug ↔ gene | `DGIdb_get_drug_gene_interactions` | `{"genes": ["TP53", "PIK3CA"]}` |
| Variant annotation (precision oncology) | `OncoKB_annotate_variant` | `{"gene": "PIK3CA", "variant": "H1047R", "tumor_type": "Breast Cancer"}` |
| Literature | `PubMed_search_articles` | `{"query": "BRCA1 therapy", "max_results": 10}` |
| Clinical trials | `search_clinical_trials` | `{"query_term": "metformin cancer", "status": "RECRUITING"}` |
| Pharmacogenomics | `CPIC_list_guidelines` | `{"gene": "CYP2D6"}` |

**Compound tools** (run multiple databases in one call):

- `gather_gene_disease_associations`
- `annotate_variant_multi_source`
- `gather_disease_profile`

For anything else: `find_tools("your topic")` then `get_tool_info("name")`.

## Batch Pattern (5+ similar queries)

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
for gene in ["TP53", "BRCA1", "PIK3CA", "PTEN", "KRAS"]:
    print(tu.run_one_function({
        "name": "GDC_get_mutation_frequency",
        "arguments": {"gene_symbol": gene},
    }))
```

Registry loads once; ~3 s total. The same loop with `subprocess.run(["tu", "run", ...])` is ~12 s because each call reloads the registry.

## Constraints

- API key errors: don't retry; move on and note the limitation in the final report.
- For local data-file analysis, route to a skill before writing ad-hoc analysis code.
- Stay in this conversation — do not spawn a subagent.
