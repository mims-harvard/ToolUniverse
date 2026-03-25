---
name: tooluniverse-multiomic-disease-characterization
description: Comprehensive multi-omics disease characterization integrating genomics, transcriptomics, proteomics, pathway, and therapeutic layers for systems-level understanding. Produces a detailed multi-omics report with quantitative confidence scoring (0-100), cross-layer gene concordance analysis, biomarker candidates, therapeutic opportunities, and mechanistic hypotheses. Uses 80+ ToolUniverse tools across 8 analysis layers. Use when users ask about disease mechanisms, multi-omics analysis, systems biology of disease, biomarker discovery, or therapeutic target identification from a disease perspective.
---

# Multi-Omics Disease Characterization Pipeline

Characterize diseases across multiple molecular layers (genomics, transcriptomics, proteomics, pathways) to provide systems-level understanding of disease mechanisms, identify therapeutic opportunities, and discover biomarker candidates.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Disease disambiguation FIRST** - Resolve all identifiers before omics analysis
3. **Layer-by-layer analysis** - Systematically cover all omics layers
4. **Cross-layer integration** - Identify genes/targets appearing in multiple layers
5. **Evidence grading** - Grade all evidence as T1 (human/clinical) to T4 (computational)
6. **Tissue context** - Emphasize disease-relevant tissues/organs
7. **Quantitative scoring** - Multi-Omics Confidence Score (0-100)
8. **Druggable focus** - Prioritize targets with therapeutic potential
9. **Biomarker identification** - Highlight diagnostic/prognostic markers
10. **Mechanistic synthesis** - Generate testable hypotheses
11. **Source references** - Every statement must cite tool/database
12. **Completeness checklist** - Mandatory section showing analysis coverage
13. **English-first queries** - Always use English terms in tool calls. Respond in user's language

---

## When to Use This Skill

Apply when users:
- Ask about disease mechanisms across omics layers
- Need multi-omics characterization of a disease
- Want to understand disease at the systems biology level
- Ask "What pathways/genes/proteins are involved in [disease]?"
- Need biomarker discovery for a disease
- Want to identify druggable targets from disease profiling
- Ask for integrated genomics + transcriptomics + proteomics analysis
- Need cross-layer concordance analysis
- Ask about disease network biology / hub genes

**NOT for** (use other skills instead):
- Single gene/target validation -> Use `tooluniverse-drug-target-validation`
- Drug safety profiling -> Use `tooluniverse-adverse-event-detection`
- General disease overview -> Use `tooluniverse-disease-research`
- Variant interpretation -> Use `tooluniverse-variant-interpretation`
- GWAS-specific analysis -> Use `tooluniverse-gwas-*` skills
- Pathway-only analysis -> Use `tooluniverse-systems-biology`

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **disease** | Yes | Disease name, OMIM ID, EFO ID, or MONDO ID | `Alzheimer disease`, `MONDO_0004975` |
| **tissue** | No | Tissue/organ of interest | `brain`, `liver`, `blood` |
| **focus_layers** | No | Specific omics layers to emphasize | `genomics`, `transcriptomics`, `pathways` |

---

## Pipeline Overview

The pipeline runs 9 phases sequentially. Each phase uses specific tools documented in detail in `tool-reference.md`.

### Phase 0: Disease Disambiguation (ALWAYS FIRST)
Resolve disease to standard identifiers (MONDO/EFO) for all downstream queries.
- Primary tool: `OpenTargets_get_disease_id_description_by_name`
- Get description, synonyms, therapeutic areas, disease hierarchy, cross-references
- **CRITICAL**: Disease IDs use underscore format (e.g., `MONDO_0004975`), NOT colon
- If ambiguous, present top 3-5 options and ask user to select

### Phase 1: Genomics Layer
Identify genetic variants, GWAS associations, and genetically implicated genes.
- Tools: `gwas_search_associations` (use `efo_id` for precision, not free-text `disease_trait`), `gwas_get_snps_for_gene`, ClinVar, OpenTargets associated targets
- `gnomad_get_gene_constraints` — gene constraint metrics (pLI, oe_lof) to interpret whether LoF variants are tolerated vs. haploinsufficient
- Get top 10-15 genes with genetic evidence scores; track Ensembl IDs for downstream phases

### Phase 2: Transcriptomics Layer
Identify differentially expressed genes, tissue-specific expression, and expression-based biomarkers.
- `GTEx_get_expression_summary` — baseline expression across 54 tissues (accepts `gene_symbol` directly)
- Tools: Expression Atlas, HPA (tissue expression), EuropePMC scores
- Check expression in disease-relevant tissues for top genes from Phase 1

### Phase 3: Proteomics & Interaction Layer
Map protein-protein interactions, identify hub genes, and characterize interaction networks.
- `UniProt_get_function_by_accession` — protein function narrative (essential for mechanistic context)
- Tools: `STRING_get_network` (param: `identifiers`, `species`=9606), `intact_get_interactions`, HumanBase
- Build PPI network from top 15-20 genes; identify hub genes by degree centrality

### Phase 4: Pathway & Network Layer
Identify enriched biological pathways and cross-pathway connections.
- `ReactomeAnalysis_pathway_enrichment` — identifiers are **newline-separated** (`\n`), NOT space-separated
- `enrichr_gene_enrichment_analysis` — param: `gene_list` (array), `libs` (array). NOTE: `data` field is a JSON string that needs parsing
- `kegg_search_pathway` — pathway keyword search

### Phase 5: Gene Ontology & Functional Annotation
Characterize biological processes, molecular functions, and cellular components.
- Tools: Enrichr (GO libraries), QuickGO, GO annotations, OpenTargets GO
- Run GO enrichment for all 3 aspects (BP, MF, CC)

### Phase 6: Therapeutic Landscape
Map approved drugs, druggable targets, repurposing opportunities, and clinical trials.
- `DGIdb_get_drug_gene_interactions` — drug interactions by gene (param: `genes` as array). Often more comprehensive than OpenTargets for drug-gene data.
- OpenTargets drugs/tractability (use **EFO IDs** like `EFO_0000384` for Crohn's, not MONDO — MONDO IDs may return null for drug queries)
- `search_clinical_trials` — `query_term` is REQUIRED

### Phase 7: Multi-Omics Integration
Integrate findings across all layers. See `integration-scoring.md` for full details.
- Cross-layer gene concordance: count layers per gene, score multi-layer hub genes
- Direction concordance: genetics + expression agreement
- Biomarker identification: diagnostic, prognostic, predictive
- Mechanistic hypothesis generation

### Phase 8: Report Finalization
Write executive summary, calculate confidence score, verify completeness.
- See `integration-scoring.md` for quality checklist and scoring formula

---

## Key Tool Parameter Notes

These are the most common parameter pitfalls:
- `OpenTargets` disease IDs: underscore format (`MONDO_0004975`), NOT colon
- `STRING` `protein_ids`: must be **array** (`['APOE']`), not string
- `enrichr` `libs`: must be **array** (`['KEGG_2021_Human']`)
- `HPA_get_rna_expression_by_source`: ALL 3 params required (`gene_name`, `source_type`, `source_name`)
- `humanbase_ppi_analysis`: ALL params required (`gene_list`, `tissue`, `max_node`, `interaction`, `string_mode`)
- `expression_atlas_disease_target_score`: `pageSize` is REQUIRED
- `search_clinical_trials`: `query_term` is REQUIRED even if `condition` is provided

For full tool parameters and per-phase workflows, see `tool-reference.md`.

---

## Reference Files

All detailed content is in reference files in this directory:

| File | Contents |
|------|----------|
| `tool-reference.md` | Full tool parameters, inputs/outputs, per-phase workflows, quick reference table |
| `report-template.md` | Complete report markdown template with all sections and checklists |
| `integration-scoring.md` | Confidence score formula (0-100), evidence grading (T1-T4), integration procedures, quality checklist |
| `response-formats.md` | Verified JSON response structures for key tools |
| `use-patterns.md` | Common use patterns, edge case handling, fallback strategies |
