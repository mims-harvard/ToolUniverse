---
name: tooluniverse-rare-disease-diagnosis
description: Rare disease differential diagnosis from patient phenotype — HPO term matching to candidate diseases (Orphanet, OMIM), gene panel prioritization, ACMG variant interpretation, and structure-based variant analysis. Use for diagnostic odyssey assistance, phenotype-to-disease ranking, and genetic-counseling differential generation.
disable-model-invocation: true
---

# Rare Disease Diagnosis Advisor

Systematic diagnosis support for rare diseases using phenotype matching, gene panel prioritization, and variant interpretation across Orphanet, OMIM, HPO, ClinVar, and structure-based analysis.

**KEY PRINCIPLES**:
1. **Report-first** - Create report file FIRST, update progressively
2. **Phenotype-driven** - Convert symptoms to HPO terms before searching
3. **Multi-database triangulation** - Cross-reference Orphanet, OMIM, OpenTargets
4. **Evidence grading** - Grade diagnoses by supporting evidence strength
5. **English-first queries** - Always use English terms in tool calls

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Clinical Reasoning Framework (BEFORE Tools)

Apply these strategies to form a 3-5 candidate differential, then use tools to confirm/refute:

1. **Multi-system involvement** - Symptoms spanning 2+ organ systems = strongest rare disease signal. Ask: what single pathway explains ALL features?
2. **Regression question** - Losing abilities vs never acquired? Regression = neurodegenerative/metabolic storage. Stable = developmental/structural.
3. **Trigger question** - Episodic/triggered (fasting, illness, exercise) = metabolic disorder (often treatable). Constitutive = structural/degenerative.
4. **Rarest feature first** - Build differential from most specific finding, not most prominent. Check remaining features for consistency.
5. **Treatable-first** - Move treatable conditions to top for urgent workup (enzyme replacement, dietary, chelation, vitamin-responsive).
6. **Occupational/environmental exposure** - Latency up to 50 years. Asbestos/silica/heavy metals/solvents/farming. Always ask about PAST jobs.
7. **Autoimmune differential** - Which joints? Symmetric? Extra-articular? Serologic pattern? Organ under attack?
8. **Rare syndrome signals** - Named triads, common diagnoses failing to explain ALL findings, failed standard treatment, unusual lab findings.
9. **Tools verify, not generate** - Form hypothesis first, then use databases to confirm.

**Common pitfalls**: Felty's (RA+splenomegaly+neutropenia) mimics infection; SLE nephritis mimics PSGN (check ASO); occupational exposures trigger autoimmunity (silica→scleroderma/RA/SLE).

---

## Tool Parameter Corrections

| Tool | WRONG | CORRECT |
|------|-------|---------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblID` | `ensemblId` |
| `ClinVar_get_variant_details` | `variant_id` | `id` |
| `MyGene_query_genes` | `gene` | `q` |
| `gnomad_get_variant` | `variant` | `variant_id` |

---

## Workflow

```
Phase 0: Clinical Reasoning → 3-5 candidate differential
Phase 1: Phenotype → HPO terms (HPO_search_terms), core vs variable, onset, family history
Phase 2: Disease Matching → Orphanet_search_diseases, OMIM_search, DisGeNET_search_gene
Phase 3: Gene Panel → MARRVEL_get_gene (aggregated IDs) + MARRVEL_get_omim_phenotypes (OMIM disease+inheritance), ClinGen validation, GTEx expression, prioritization scoring
Phase 3.5: Expression Context → CELLxGENE, ChIPAtlas for tissue/cell-type confirmation
Phase 3.6: Pathway Analysis → KEGG, IntAct for convergent pathways
Phase 4: Variant Interpretation → FAVOR_annotate_variant (one-call: freq + CADD/SIFT/PolyPhen/AlphaMissense + ClinVar + conservation), then ClinVar, gnomAD frequency, EVE/SpliceAI, ACMG criteria
Phase 5: Structure Analysis → AlphaFold2, InterPro domains (for VUS)
Phase 6: Literature → PubMed, BioRxiv/MedRxiv, OpenAlex
Phase 7: Report Synthesis → Prioritized differential with next steps
```

### Key Phase Details

**Phase 2 - Disease Matching**: `Orphanet_search_diseases(operation="search_diseases", query=keyword)` then `Orphanet_get_genes(operation="get_genes", orpha_code=code)`. Score overlap: Excellent >80%, Good 60-80%, Possible 40-60%.

**Phase 3 - Gene Panel**: For each candidate gene, `MARRVEL_get_gene(symbol)` resolves OMIM/HGNC/Ensembl/Entrez/UniProt IDs in one call, and `MARRVEL_get_omim_phenotypes(symbol)` lists the Mendelian diseases linked to the gene with mode of inheritance — use the inheritance pattern to filter candidates against the pedigree (e.g. drop AR genes for a clearly dominant pedigree). Then ClinGen classification drives inclusion (Definitive/Strong/Moderate = include; Limited = flag; Disputed/Refuted = exclude). Scoring: Tier 1 (top disease gene +5), Tier 2 (multi-disease +3), Tier 3 (ClinGen Definitive +3), Tier 4 (tissue expression +2), Tier 5 (pLI >0.9 +1).

**Phase 3 - Clinical Testing Panels (PanelApp)**: Cross-check candidate genes against Genomics England PanelApp, the curated gene-panel source NHS and other genomic medicine services actually order testing from — a genuinely different signal from MARRVEL/ClinGen's disease-gene curation, since it reflects what a real diagnostic lab panel would include today.
- `PanelApp_search_panels(search=<phenotype/disease keyword>)` — find the relevant clinical panel(s) for the working differential, e.g. `search="intellectual disability"` returns panel id `285` ("Intellectual disability", disease group "Developmental disorders", versioned — panels are actively curated and re-versioned).
- `PanelApp_get_panel(panel_id=<id>)` — full gene list for that panel with each gene's confidence level: **3=green (diagnostic-grade, strong evidence)**, 2=amber (borderline), 1=red (low evidence, do not use for diagnostic reporting) — only report green genes as actionable findings; amber/red are candidates for research follow-up, not a diagnosis.
- `PanelApp_search_genes(gene_symbol=<symbol>)` — reverse lookup: which clinical panels (and at what confidence) already include a specific candidate gene, e.g. `PTEN` appears on 54 panels (cancer predisposition, overgrowth, macrocephaly panels, etc.) — a gene appearing on many panels at green confidence is a stronger candidate than one appearing nowhere.
Use PanelApp as a real-world-testing-relevance check alongside (not instead of) the MARRVEL/ClinGen tier scoring above: a green-confidence PanelApp hit that also has ClinGen Definitive classification is the strongest possible signal that a lab would both classify AND actually test for the gene.

**Phase 4 - Variants**: Start with `FAVOR_annotate_variant("chr-pos-ref-alt")` (GRCh38) for a single-call snapshot — population frequencies (gnomAD by ancestry, BRAVO), GENCODE consequence, CADD/SIFT/PolyPhen-2/AlphaMissense scores, conservation, and ClinVar significance — then drill into ClinVar/gnomAD/EVE/SpliceAI for detail. gnomAD frequency classes: ultra-rare <0.00001, rare <0.0001, low-freq <0.01. ACMG: PVS1 (null), PS1 (same AA), PM2 (absent pop), PP3 (computational), BA1 (>5% AF). 2+ concordant predictors strengthen PP3.

---

## Evidence Grading

| Tier | Criteria |
|------|----------|
| **T1** (High) | Phenotype match >80% + gene match |
| **T2** (Medium-High) | Phenotype match 60-80% OR likely pathogenic variant |
| **T3** (Medium) | Phenotype match 40-60% OR VUS in candidate gene |
| **T4** (Low) | Phenotype <40% OR uncertain gene |

---

## Fallback Chains

| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `get_joint_associated_diseases_by_HPO_ID_list` | `Orphanet_search_diseases` | PubMed phenotype search |
| `MARRVEL_get_omim_phenotypes` | `OMIM_search` | Orphanet gene-disease |
| `PanelApp_search_genes` | `PanelApp_search_panels` (browse by phenotype instead) | ClinGen validation only |
| `FAVOR_annotate_variant` | `ClinVar_get_variant_details` | `gnomad_get_variant` |
| `ClinVar_get_variant_details` | `gnomad_get_variant` | VEP annotation |
| `GTEx_get_expression_summary` | `HPA_search_genes_by_query` | Tissue-specific literature |

---

## Reference Files

- [DIAGNOSTIC_WORKFLOW.md](DIAGNOSTIC_WORKFLOW.md) - Code examples and algorithms per phase
- [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) - Report template and examples
- [CHECKLIST.md](CHECKLIST.md) - Interactive completeness checklist
- `scripts/clinical_patterns.py` - Clinical pattern lookup (syndromes, differentials, red flags, occupational exposures)
