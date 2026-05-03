---
name: tooluniverse-protein-modification-analysis
description: Analyze post-translational modifications (PTMs) of proteins — modification sites, types, proteoforms, functional effects at PTM sites, and PTM-dependent protein interactions. Integrates iPTMnet, ProtVar, UniProt, and STRING databases. Use when asked about protein phosphorylation, ubiquitination, acetylation, glycosylation, methylation, SUMOylation, or other PTMs; proteoform diversity; PTM-regulated interactions; or functional impact of PTM sites.
---

# Protein Post-Translational Modification Analysis

Comprehensive PTM analysis using iPTMnet (primary), ProtVar (functional context), UniProt (baseline), STRING (interactions), ELM (linear motifs), and MassIVE/ProteomeXchange (experimental data).

## LOOK UP DON'T GUESS

- PTM sites/enzymes: `iPTMnet_get_ptm_sites`
- Functional consequence: `ProtVar_get_function` + `iPTMnet_get_ptm_ppi`
- Proteoforms: `iPTMnet_get_proteoforms`
- Linear motifs: `ELM_get_instances`

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Domain Reasoning

PTMs are context-dependent: same phosphorylation site can activate or inhibit depending on kinase and effectors. Always check: which enzyme, what functional consequence, in what cell context.

---

## KEY PRINCIPLES

1. **Disambiguation first** -- resolve to UniProt accession before iPTMnet calls
2. **iPTMnet is SOAP-style** -- every call requires `operation` parameter
3. **Evidence-graded** -- distinguish experimental (T1) from predicted (T4)
4. **English-first queries**

---

## Workflow

```
Phase 0: Protein Disambiguation → UniProt accession
Phase 1: PTM Site Inventory → iPTMnet_get_ptm_sites
Phase 2: Proteoform Analysis → iPTMnet_get_proteoforms
Phase 3: PTM-Dependent Interactions → iPTMnet_get_ptm_ppi
Phase 4: Functional Context → ProtVar_get_function at key sites
Phase 4b: Linear Motif Context → ELM_get_instances for SLiM overlap
Phase 4c: Experimental Data → MassIVE/ProteomeXchange
Phase 5: Synthesis & Report
```

---

## Phase 0: Disambiguation

- `iPTMnet_search(operation="search", search_term="TP53", role="Substrate")` -- find UniProt IDs
- If user provides UniProt accession directly, use it
- Select human entry if multiple hits

## Phase 1: PTM Sites

`iPTMnet_get_ptm_sites(operation="get_ptm_sites", uniprot_id="P04637")` -- returns position, residue, modification type, enzyme, evidence. Group by modification type. Fallback: `UniProt_get_entry_by_accession` PTM annotations.

## Phase 2: Proteoforms

`iPTMnet_get_proteoforms(operation="get_proteoforms", uniprot_id=...)` -- distinct PTM combinations. Focus on those with functional/disease annotations if >20.

## Phase 3: PTM-Dependent Interactions

`iPTMnet_get_ptm_ppi(operation="get_ptm_ppi", uniprot_id=...)` -- interacting protein, PTM site, effect (enables/disrupts). Supplement with `STRING_get_interaction_partners(identifiers=gene, species=9606, required_score=700)`.

## Phase 4: Functional Context

`ProtVar_get_function(accession=..., position=N, variant_aa=AA)` -- domain, active site, binding site, conservation. Grade: active-site PTM > domain-core > disordered region.

## Phase 4b: Linear Motifs (ELM)

`ELM_get_instances(operation="get_instances", uniprot_id=..., motif_type="MOD")` -- MOD = modification sites, DEG = degradation signals. Cross-reference with Phase 1 PTM positions. `ELM_list_classes(operation="list_classes")` for motif details.

## Phase 4c: Experimental Data

`MassIVE_search_datasets(species="9606")`, `MassIVE_get_dataset(accession="MSV...")` for public MS datasets.

---

## Evidence Grading

| Tier | Criteria |
|------|----------|
| T1 | PTM at validated active/binding site with functional data |
| T2 | PTM in structured domain with ProtVar annotation |
| T3 | Correlation data only (mass spec detection) |
| T4 | Predicted, no experimental validation |

---

## Tool Parameter Reference

| Tool | Key Params |
|------|-----------|
| `iPTMnet_search` | `operation="search"`, `search_term`, `role` |
| `iPTMnet_get_ptm_sites` | `operation="get_ptm_sites"`, `uniprot_id` |
| `iPTMnet_get_proteoforms` | `operation="get_proteoforms"`, `uniprot_id` |
| `iPTMnet_get_ptm_ppi` | `operation="get_ptm_ppi"`, `uniprot_id` |
| `ELM_get_instances` | `operation="get_instances"`, `uniprot_id`, `motif_type` |
| `ELM_list_classes` | `operation="list_classes"` |
| `MassIVE_search_datasets` | `page_size`, `species` |

**Critical**: All iPTMnet and ELM tools require `operation` as first parameter (SOAP-style).

---

## Fallbacks

| Situation | Fallback |
|-----------|----------|
| Not in iPTMnet | UniProt PTM/processing annotations |
| No PTM-PPI data | STRING general PPI |
| No ProtVar data | UniProt domain annotations |
| No ELM data | Proceed with iPTMnet/UniProt only |

## Limitations

- iPTMnet biased toward well-studied proteins
- Proteoform data covers observed combinations only
- PTM-PPI: only PTM-specific evidence; more PPIs exist in STRING
