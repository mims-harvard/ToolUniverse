---
name: tooluniverse-functional-genomics-screens
description: Interpret results from CRISPR/shRNA genetic screens using DepMap essentiality data, constraint scores, pathway enrichment, protein networks, druggability assessment, and clinical evidence. Use for screen hit validation, gene essentiality analysis, DepMap exploration, functional genomics interpretation, and screen-to-target prioritization.
---

# Functional Genomics Screen Interpretation

Pipeline for validating and prioritizing hits from genetic screens (CRISPR-KO, CRISPRi, shRNA) by integrating essentiality (DepMap), constraint (gnomAD), pathways (Reactome, STRING), druggability (DGIdb), and clinical evidence (CIViC, COSMIC).

**Guiding principles**:
1. **Hits are hypotheses** -- screen results contain false positives; validate through orthogonal evidence
2. **Selectivity matters** -- pan-essential genes are poor drug targets; context-specific essentiality is high-value
3. **Pathway over gene** -- enriched pathways are more robust than individual hits
4. **Druggability is practical** -- prioritize chemically modulable targets
5. **English-first queries** -- use English gene names in tool calls

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Workflow

```
Phase 0: Input Processing → gene list, screen type, cell line, disease context
Phase 1: Hit Validation → DepMap dependency, gnomAD constraint, UniProt function
Phase 2: Pathway & Network → Reactome enrichment, STRING network, functional clusters
Phase 3: Druggability → DGIdb interactions, druggable categories, PharmacoDB
Phase 4: Clinical Evidence → CIViC, COSMIC mutations
Phase 5: Literature → PubMed for key hits
Phase 6: Prioritized Report → ranked target list with multi-dimensional scoring
```

---

## Phase Details

### Phase 1: Hit Validation

**Tools**:
- `DepMap_get_gene_dependencies(gene_symbol=...)` -- returns gene metadata only (NOT per-cell-line scores)
- `DepMap_search_cell_lines(query=...)` -- cell line metadata
- `gnomad_get_gene_constraints(gene_symbol=...)` -- pLI, LOEUF (may return "Service overloaded")
- `UniProt_get_function_by_accession(accession=...)` -- function summary

**Classification**: Pan-essential (>90% lines), Selectively essential (specific lineages), Context-specific (screen model only). Chronos < -0.5 = likely essential, < -1.0 = strongly essential.

**DepMap limitation**: Tool returns metadata only. For actual Chronos scores, download CRISPRGeneEffect.csv from depmap.org and analyze locally. Fallback: gnomAD constraint + `PubMed_search_articles(query="[gene] CRISPR screen [cancer]")`.

### Phase 2: Pathway & Network

- `ReactomeAnalysis_pathway_enrichment(identifiers="TP53 BRCA1 EGFR")` -- space-separated string
- `STRING_get_network(identifiers="GENE1\rGENE2\rGENE3", species=9606)` -- carriage-return separated
- `STRING_functional_enrichment(identifiers=..., species=9606)` -- GO/KEGG enrichment

### Phase 3: Druggability

- `DGIdb_get_drug_gene_interactions(genes=["EGFR","BRAF"])` -- drug-gene interactions
- `DGIdb_get_gene_druggability(genes=[...])` -- categories (kinase, GPCR, etc.)
- For high-priority hits, also search `search_clinical_trials` and PubMed for novel inhibitors not yet in DGIdb.

### Phase 4: Clinical Evidence

- `civic_search_evidence_items(molecular_profile=gene)` -- NOT `query`
- `COSMIC_get_mutations_by_gene(gene_name=...)` -- somatic mutation frequency

### Phase 6: Prioritized Report

**Scoring (0-18)**:

| Criterion | Score 3 | Score 0 |
|-----------|---------|---------|
| Selective essentiality | <-0.5 in disease AND >-0.2 elsewhere | >-0.2 (not essential) |
| Pathway convergence | 3+ hits same pathway | Isolated hit |
| Druggability | Approved drug exists | Not druggable |
| Clinical evidence | CIViC therapeutic | No clinical data |
| Constraint | pLI >0.9 | No data |
| Literature | Multiple validation studies | No publications |

**Tiers**: T1 (15-18) high-confidence, T2 (10-14) promising, T3 (5-9) speculative, T4 (<5) likely false positive.

---

## Edge Cases

- **gnomAD overloaded**: Retry once, proceed without, note gap
- **Gene not in DepMap**: Fall back to gnomAD + UniProt
- **Large hit lists (>500)**: Pathway enrichment on full list; per-gene analysis on top 50
- **Non-cancer screens**: DepMap less informative; weight constraint/pathway more
- **shRNA vs CRISPR**: Higher validation bar for shRNA (off-target effects)

## Limitations

- DepMap is cancer-centric (~1000 cancer lines)
- No raw screen analysis (use MAGeCK/BAGEL upstream)
- STRING interactions are associations, not causal
