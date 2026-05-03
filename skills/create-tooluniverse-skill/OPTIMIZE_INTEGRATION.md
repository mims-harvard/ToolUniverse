# Integration with devtu-optimize-skills

How to apply the 10 pillars when creating new ToolUniverse skills.

## When to Reference devtu-optimize-skills

**Invoke or review** when: creating research report skills, need evidence grading, report optimization, completeness checking, or synthesis sections.

**Not needed** for: simple data retrieval, pure tool integration without reports.

## The 10 Pillars Applied

### 1. TEST FIRST (Always)

Create test script BEFORE documentation. Verify all tool parameters through actual API calls. Document discoveries. Only proceed to implementation after 100% tool verification.

**Lesson**: All 4 broken skills (DDI, Clinical Trial, Antibody, CRISPR) had 0-20% functionality because tools were never tested.

### 2. Verify Tool Contracts (Always)

Check params via `get_tool_info()`. Maintain corrections table. Don't trust function names.
Example: `drugbank_get_drug_by_name(query=...)` not `name=...`

### 3. Handle SOAP Tools (Always, if present)

Indicators: error about `operation` required, tool name includes IMGT/SAbDab/TheraSAbDab.
Fix: add `operation` parameter as first argument with method name.

### 4. Implementation-Agnostic Docs (Always)

SKILL.md has ZERO Python/MCP code. Separate python_implementation.py. QUICK_START.md equal treatment of both interfaces. Tool parameter table notes "applies to all implementations."

### 5. Foundation First (If aggregator exists)

Query comprehensive aggregators before specialized tools. Structure: Phase 0 (aggregator) then Phases 1-N (specialized). Example: Open Targets (foundation) then specialized databases (details).

### 6. Disambiguate Carefully (If ambiguous inputs)

Include disambiguation phase early. Support multiple ID types. Handle versioned IDs (e.g., GTEx requires versioned Ensembl). Document ID resolution strategy.

### 7. Implement Fallbacks (If external APIs)

Primary -> Fallback -> Default chains. Design fallback for each critical tool. Document in SKILL.md.
Example: DepMap_search_genes (primary) -> Pharos_get_target (fallback) -> continue with unvalidated genes (default).

### 8. Grade Evidence (If literature)

T1 (3 stars): Mechanistic study. T2 (2 stars): Functional study. T3 (1 star): Association. T4 (0 stars): Mention.
Apply when skills search literature, aggregate multi-source evidence, or make scientific claims.

### 9. Quantified Completeness (If multi-section)

Define numeric minimums per section. Example: ">=20 pathways OR explanation why fewer." Implement checks in code.

### 10. Synthesize (If research-oriented)

Include biological models and testable hypotheses, not just paper lists. Sections: Biological Model (3-5 paragraphs), Testable Hypotheses table, Suggested Experiments.

## Quick Reference: Which Pillars Apply

| Skill Type | Applicable Pillars |
|------------|-------------------|
| Research/Analysis | All 10 |
| Data Retrieval | 1-4, 6-7 |
| Multi-Database | 1-5, 7 |
| Specialized Analysis | 1-4, 7-9 |
| Simple Tool Wrapper | 1-4 |

## Integration Checklist

- [ ] Reviewed 10 pillars
- [ ] Identified which apply
- [ ] TEST FIRST (always)
- [ ] Verified tool contracts (always)
- [ ] Implementation-agnostic docs (always)
- [ ] Fallback strategies (if external APIs)
- [ ] Evidence grading (if literature)
- [ ] Quantified completeness (if multi-section)
- [ ] Synthesis (if research-oriented)
