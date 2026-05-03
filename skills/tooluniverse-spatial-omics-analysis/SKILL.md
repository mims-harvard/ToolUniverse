---
name: tooluniverse-spatial-omics-analysis
description: Computational analysis framework for spatial multi-omics data integration. Given spatially variable genes (SVGs), spatial domain annotations, tissue type, and disease context from spatial transcriptomics/proteomics experiments (10x Visium, MERFISH, DBiTplus, SLIDE-seq, etc.), performs comprehensive biological interpretation including pathway enrichment, cell-cell interaction inference, druggable target identification, immune microenvironment characterization, and multi-modal integration. Produces a detailed markdown report with Spatial Omics Integration Score (0-100), domain-by-domain characterization, and validation recommendations. Uses 70+ ToolUniverse tools across 9 analysis phases. Use when users ask about spatial transcriptomics analysis, spatial omics interpretation, tissue heterogeneity, spatial gene expression patterns, tumor microenvironment mapping, tissue zonation, or cell-cell communication from spatial data.
---

# Spatial Multi-Omics Analysis Pipeline

Comprehensive biological interpretation of spatial omics data. Transforms spatially variable genes (SVGs), domain annotations, and tissue context into actionable biological insights.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Domain-by-domain analysis** - Characterize each spatial region independently before comparison
3. **Gene-list-centric** - Analyze user-provided SVGs and marker genes with ToolUniverse databases
4. **Biological interpretation** - Go beyond statistics to explain biological meaning of spatial patterns
5. **Disease focus** - Emphasize disease mechanisms and therapeutic opportunities when disease context is provided
6. **Evidence grading** - Grade all evidence as T1 (human/clinical) to T4 (computational)
7. **Multi-modal thinking** - Integrate RNA, protein, and metabolite information when available
8. **Validation guidance** - Suggest experimental validation approaches for key findings
9. **Source references** - Every statement must cite tool/database source
10. **English-first queries** - Always use English terms in tool calls

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use This Skill

Apply when users:
- Provide spatially variable genes from spatial transcriptomics experiments
- Ask about biological interpretation of spatial domains/clusters
- Need pathway enrichment of spatial gene expression data
- Want to understand cell-cell interactions from spatial data
- Ask about tumor microenvironment heterogeneity from spatial omics
- Need druggable targets in specific spatial regions
- Ask about tissue zonation patterns (liver, brain, kidney)
- Want to integrate spatial transcriptomics + proteomics data

**NOT for**: Single gene interpretation (use target-research), variant interpretation, drug safety, bulk RNA-seq, GWAS analysis.

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **svgs** | Yes | Spatially variable genes | `['EGFR', 'CDH1', 'VIM', 'MYC', 'CD3E']` |
| **tissue_type** | Yes | Tissue/organ type | `brain`, `liver`, `lung`, `breast` |
| **technology** | No | Spatial omics platform | `10x Visium`, `MERFISH`, `DBiTplus` |
| **disease_context** | No | Disease if applicable | `breast cancer`, `Alzheimer disease` |
| **spatial_domains** | No | Domain -> marker genes dict | `{'Tumor core': ['MYC','EGFR']}` |
| **cell_types** | No | Cell types from deconvolution | `['Epithelial', 'T cell']` |
| **proteins** | No | Proteins detected (multi-modal) | `['CD3', 'PD-L1', 'Ki67']` |
| **metabolites** | No | Metabolites (SpatialMETA) | `['glutamine', 'lactate']` |

---

## Spatial Omics Integration Score (0-100)

**Data Completeness (0-30)**: SVGs (5), Disease context (5), Spatial domains (5), Cell types (5), Multi-modal (5), Literature (5)

**Biological Insight (0-40)**: Pathway enrichment FDR<0.05 (10), Cell-cell interactions (10), Disease mechanism (10), Druggable targets (10)

**Evidence Quality (0-30)**: Cross-database validation 3+ DBs (10), Clinical validation (10), Literature support (10)

| Score | Tier | Interpretation |
|-------|------|----------------|
| 80-100 | Excellent | Comprehensive characterization, strong insights, druggable targets |
| 60-79 | Good | Good pathway/interaction analysis, some therapeutic context |
| 40-59 | Moderate | Basic enrichment, limited domain comparison |
| 0-39 | Limited | Minimal data, gene-level annotation only |

### Evidence Grading

| Tier | Criteria | Examples |
|------|----------|----------|
| [T1] | Direct human/clinical evidence | FDA-approved drug, validated biomarker |
| [T2] | Experimental evidence | Validated spatial pattern, known L-R pair |
| [T3] | Computational/database evidence | PPI prediction, pathway enrichment |
| [T4] | Annotation/prediction only | GO annotation, text-mined association |

---

## Analysis Phases Overview

### Phase 0: Input Processing & Disambiguation (ALWAYS FIRST)
Resolve tissue/disease identifiers, establish analysis context. Get MONDO/EFO IDs for disease queries.
- Tools: `OpenTargets_get_disease_id_description_by_name`, `OpenTargets_get_disease_description_by_efoId`, `HPA_search_genes_by_query`

### Phase 1: Gene Characterization
Resolve gene IDs, annotate functions, tissue specificity, subcellular localization.
- Tools: `MyGene_query_genes`, `UniProt_get_function_by_accession`, `HPA_get_subcellular_location`, `HPA_get_rna_expression_by_source`, `HPA_get_comprehensive_gene_details_by_ensembl_id`, `HPA_get_cancer_prognostics_by_gene`, `UniProtIDMap_gene_to_uniprot`

### Phase 2: Pathway & Functional Enrichment
Identify enriched pathways globally and per-domain. Filter FDR < 0.05.
- Tools: `STRING_functional_enrichment` (PRIMARY), `ReactomeAnalysis_pathway_enrichment`, `GO_get_annotations_for_gene`, `kegg_search_pathway`, `WikiPathways_search`

### Phase 3: Spatial Domain Characterization
Characterize each domain biologically, assign cell types from markers, compare domains.
- Tools: Phase 2 tools + `HPA_get_biological_processes_by_gene`, `HPA_get_protein_interactions_by_gene`

### Phase 4: Cell-Cell Interaction Inference
Predict communication from spatial patterns. Check ligand-receptor pairs across domains.
- Tools: `STRING_get_interaction_partners`, `STRING_get_protein_interactions`, `intact_search_interactions`, `Reactome_get_interactor`, `DGIdb_get_drug_gene_interactions`

### Phase 5: Disease & Therapeutic Context
Connect to disease mechanisms, identify druggable targets, find clinical trials.
- Tools: `OpenTargets_get_associated_targets_by_disease_efoId`, `OpenTargets_get_target_tractability_by_ensemblID`, `OpenTargets_get_associated_drugs_by_target_ensemblID`, `search_clinical_trials`, `DGIdb_get_gene_druggability`, `civic_search_genes`

### Phase 6: Multi-Modal Integration
Integrate protein/RNA/metabolite data. Compare spatial RNA with protein detection.
- Tools: `HPA_get_subcellular_location`, `HPA_get_rna_expression_in_specific_tissues`, `Reactome_map_uniprot_to_pathways`, `kegg_get_pathway_info`

### Phase 7: Immune Microenvironment (Cancer/Inflammation only)
Classify immune cells, check checkpoint expression, assess Hot vs Cold vs Excluded patterns.
- Tools: `STRING_functional_enrichment`, `OpenTargets_get_target_tractability_by_ensemblID`, `iedb_search_epitopes`

### Phase 8: Literature & Validation Context
Search published evidence, suggest validation experiments (smFISH, IHC, PLA).
- Tools: `PubMed_search_articles`, `openalex_literature_search`

### Data Discovery: HuBMAP Spatial Atlas Tools

Use HuBMAP tools to find published spatial biology reference datasets for comparison, validation, or cross-study analysis.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `HuBMAP_search_datasets` | Search published spatial datasets by organ/assay/keyword | `organ` (code: "LK"=Kidney, "BR"=Brain, "LU"=Lung, etc.), `dataset_type` ("RNAseq", "CODEX", "MALDI"), `query`, `limit` |
| `HuBMAP_list_organs` | List all available organs with codes and UBERON IDs | (no required params) |
| `HuBMAP_get_dataset` | Get detailed metadata for a specific HuBMAP dataset | `hubmap_id` (e.g. "HBM626.FHJD.938") |

**When to use**: Phase 0 (find reference datasets for the tissue), Phase 8 (cross-reference findings with published HuBMAP atlas data).

See **phase-procedures.md** for detailed workflows, decision logic, and tool parameter specifications per phase.

---

## Report Structure

Create file: `{tissue}_{disease}_spatial_omics_report.md`

```
# Spatial Multi-Omics Analysis Report: {Tissue Type}
**Report Generated**: {date} | **Technology**: {platform}
**Tissue**: {tissue_type} | **Disease**: {disease or "Normal tissue"}
**Total SVGs**: {count} | **Spatial Domains**: {count}
**Spatial Omics Integration Score**: (calculated after analysis)

## Executive Summary
## 1. Tissue & Disease Context
## 2. Spatially Variable Gene Characterization
  - 2.1 Gene ID Resolution
  - 2.2 Tissue Expression Patterns
  - 2.3 Subcellular Localization
  - 2.4 Disease Associations
## 3. Pathway Enrichment Analysis
  - 3.1 STRING, 3.2 Reactome, 3.3-3.5 GO (BP, MF, CC)
## 4. Spatial Domain Characterization (per-domain + comparison)
## 5. Cell-Cell Interaction Inference
  - 5.1 PPI, 5.2 Ligand-Receptor, 5.3 Signaling Pathways
## 6. Disease & Therapeutic Context
  - 6.1 Disease Gene Overlap, 6.2 Druggable Targets, 6.3 Drug Mechanisms, 6.4 Trials
## 7. Multi-Modal Integration (if data available)
## 8. Immune Microenvironment (if relevant)
## 9. Literature & Validation Context
## Spatial Omics Integration Score (breakdown table)
## Completeness Checklist
## References (tools used, database versions)
```

See **report-template.md** for full template with table structures.

---

## Completeness Checklist

- [ ] Gene ID resolution complete
- [ ] Tissue expression patterns analyzed (HPA)
- [ ] Subcellular localization checked (HPA)
- [ ] Pathway enrichment complete (STRING + Reactome)
- [ ] GO enrichment complete (BP + MF + CC)
- [ ] Spatial domains characterized individually
- [ ] Domain comparison performed
- [ ] PPI analyzed (STRING)
- [ ] Ligand-receptor pairs identified
- [ ] Disease associations checked (OpenTargets)
- [ ] Druggable targets identified
- [ ] Multi-modal integration performed (if data available)
- [ ] Immune microenvironment characterized (if relevant)
- [ ] Literature search completed
- [ ] Validation recommendations provided
- [ ] Integration Score calculated
- [ ] Executive summary written
- [ ] All sections have source citations

---

## Common Use Cases

1. **Cancer Spatial Heterogeneity**: Visium with tumor/stroma/immune domains -> pathways, immune infiltration, druggable targets, checkpoints
2. **Brain Tissue Zonation**: MERFISH with neuronal subtypes -> synaptic signaling, receptors, hippocampal zonation
3. **Liver Metabolic Zonation**: Periportal vs pericentral -> CYP450, Wnt gradient, drug metabolism enzymes
4. **Tumor-Immune Interface**: DBiTplus RNA+protein -> checkpoint L-R pairs, immune exclusion, multi-modal concordance
5. **Developmental Patterns**: Morphogen gradients (Wnt, BMP, FGF, SHH), TF patterns, cell fate genes
6. **Disease Progression**: Disease gradient -> inflammatory response, neuronal loss, therapeutic windows

---

## Reference Files

- **phase-procedures.md** - Detailed phase workflows, decision logic, tool usage per phase
- **tool-reference.md** - Tool parameter names, response formats, fallback strategies, limitations
- **reference-data.md** - Cell type markers, ligand-receptor pairs, immune checkpoint reference
- **report-template.md** - Full report template with all table structures
- **test_spatial_omics.py** - Test suite

---

## Summary

**Spatial Multi-Omics Analysis** provides:
1. Gene characterization (ID resolution, function, localization, tissue expression)
2. Pathway & functional enrichment (STRING, Reactome, GO, KEGG)
3. Spatial domain characterization (per-domain and cross-domain)
4. Cell-cell interaction inference (PPI, ligand-receptor, signaling)
5. Disease & therapeutic context (disease genes, druggable targets, trials)
6. Multi-modal integration (RNA-protein concordance, metabolic pathways)
7. Immune microenvironment (cell types, checkpoints, immunotherapy)
8. Literature context & validation recommendations

**Outputs**: Markdown report with Spatial Omics Integration Score (0-100)
**Uses**: 70+ ToolUniverse tools across 9 analysis phases
**Time**: ~10-20 minutes depending on gene list size
