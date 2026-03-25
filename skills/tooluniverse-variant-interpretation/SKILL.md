---
name: tooluniverse-variant-interpretation
description: Systematic clinical variant interpretation from raw variant calls to ACMG-classified recommendations with structural impact analysis. Aggregates evidence from ClinVar, gnomAD, CIViC, UniProt, and PDB across ACMG criteria. Produces pathogenicity scores (0-100), clinical recommendations, and treatment implications. Use when interpreting genetic variants, classifying variants of uncertain significance (VUS), performing ACMG variant classification, or translating variant calls to clinical actionability.
---

# Clinical Variant Interpreter

Systematic variant interpretation using ToolUniverse - from raw variant calls to ACMG-classified clinical recommendations with structural impact analysis.

## Triggers

Use this skill when users:
- Ask about variant interpretation, classification, or pathogenicity
- Have VCF data needing clinical annotation
- Need ACMG classification for variants
- Want structural impact analysis for missense variants

## Key Principles

1. **ACMG-Guided** - Follow ACMG/AMP 2015 guidelines with explicit evidence codes
2. **Structural Evidence** - Use AlphaFold2 for novel structural impact analysis
3. **Population Context** - gnomAD frequencies with ancestry-specific data
4. **Actionable Output** - Clear recommendations, not just classifications
5. **English-first queries** - Always use English terms in tool calls; respond in user's language

---

## Workflow Overview

```
Phase 1: VARIANT IDENTITY        → Normalize HGVS, map gene/transcript/consequence
Phase 2: CLINICAL DATABASES       → ClinVar, gnomAD, OMIM, ClinGen, COSMIC, SpliceAI
Phase 2.5: REGULATORY CONTEXT     → ChIPAtlas, ENCODE (non-coding variants only)
Phase 3: COMPUTATIONAL PREDICTIONS → CADD, AlphaMissense, EVE, SIFT/PolyPhen
Phase 4: STRUCTURAL ANALYSIS      → PDB/AlphaFold2, domains, functional sites (VUS/novel)
Phase 4.5: EXPRESSION CONTEXT     → CELLxGENE, GTEx tissue expression
Phase 5: LITERATURE EVIDENCE      → PubMed, EuropePMC, BioRxiv, MedRxiv
Phase 6: ACMG CLASSIFICATION      → Evidence codes, classification, recommendations
```

---

## Phase 1: Variant Identity

Tools: `MyVariant_query_variants`, `EnsemblVar_get_variant_consequences`, `NCBIGene_search`, `VariantValidator_gene2transcripts`, `VariantValidator_validate_variant`

**VariantValidator_gene2transcripts**: Look up MANE Select and MANE Plus Clinical transcripts for a gene. Use this to identify the correct canonical transcript before variant annotation.
- Parameters: `gene_symbol` (e.g. "TP53"), `transcript_set` ("mane" | "refseq" | "ensembl" | "all"), `genome_build` ("GRCh38" default)
- Returns: Array of `{current_symbol, transcripts: [{reference, annotations: {mane_select, mane_plus_clinical}}]}`
- Aliases: `gene` and `gene_name` also accepted for `gene_symbol`

**VariantValidator_validate_variant**: Validate HGVS variant descriptions and get normalized notation with genomic/transcript/protein consequences.
- Parameters: `genome_build` ("GRCh37" | "GRCh38"), `variant_description` (HGVS, e.g. "NM_007294.4:c.5266dup"), `select_transcripts` (transcript or "all")
- Returns: Validated HGVS, protein consequence, genomic coordinates, gene IDs

Capture: HGVS notation (c. and p.), gene symbol, canonical transcript (MANE Select via VariantValidator), consequence type, amino acid change, exon/intron location.

## Phase 2: Clinical Databases

Tools: `clinvar_search_variants`, `gnomad_search_variants`, `gnomad_get_variant`, `OMIM_search`, `OMIM_get_entry`, `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_search_actionability`, `COSMIC_search_mutations`, `COSMIC_get_mutations_by_gene`, `DisGeNET_search_gene`, `DisGeNET_get_vda`, `SpliceAI_predict_splice`, `SpliceAI_get_max_delta`, `civic_get_variants_by_gene`, `civic_search_evidence_items`, `civic_search_assertions`

> **gnomAD two-step workflow**: `gnomad_search_variants` only accepts rsIDs or variant IDs (not gene names). Search by rsID first, then use the returned `variant_id` with `gnomad_get_variant` to get population allele frequencies.
>
> **CIViC**: Use `civic_get_variants_by_gene` to find clinical evidence for variants in a gene, then `civic_search_evidence_items` for actionability details.
>
> **OncoKB note**: Demo mode only supports BRAF, TP53, ROS1. For other genes, set `ONCOKB_API_TOKEN` environment variable.

Use SpliceAI for: intronic variants near splice sites, synonymous variants, exonic variants near splice junctions.

See `CODE_PATTERNS.md` for implementation details.

## Phase 2.5: Regulatory Context (Non-Coding Only)

Apply for intronic (non-splice), promoter, UTR, or intergenic variants near disease genes.

Tools: `ChIPAtlas_enrichment_analysis`, `ChIPAtlas_get_peak_data`, `ENCODE_search_experiments`, `ENCODE_get_experiment`

## Phase 2.9: Short-Circuit Check

Before full ACMG classification, check if the variant already has an expert panel classification in ClinVar. Use `MyVariant_query_variants` with the rsID or HGVS notation — the `clinvar` field in the response includes clinical significance, review status, and RCV records. If an expert panel has already classified the variant as Pathogenic or Benign, note this prominently and focus on confirming/contextualizing rather than de novo classification.

## Phase 3: Computational Predictions

**Primary approach:** `MyVariant_query_variants` with `fields=dbnsfp,clinvar,cadd,gnomad_genome` retrieves 15+ predictor scores (SIFT, PolyPhen, CADD, REVEL, AlphaMissense, MetaRNN, FATHMM, GERP, PhyloP, etc.) in a single call. This is usually sufficient.

**Individual tools** (when specific scores are needed): `CADD_get_variant_score` (PHRED 0-99), `AlphaMissense_get_variant_score` (0-1, needs UniProt ID), `EVE_get_variant_score` (0-1), `EnsemblVEP_annotate_hgvs` (VEP with colocated variants, HGMD cross-references, and ancestry-specific gnomAD frequencies)

Consensus: Run CADD (all variants) + AlphaMissense + EVE (missense). 2+ concordant damaging = strong PP3; 2+ concordant benign = strong BP4.

See `ACMG_CLASSIFICATION.md` for thresholds.

## Phase 4: Structural Analysis (VUS/Novel Missense)

Tools: `PDBe_get_uniprot_mappings`, `NvidiaNIM_alphafold2`, `alphafold_get_prediction` (param: `qualifier`, e.g., UniProt accession), `InterPro_get_protein_domains`, `UniProt_get_function_by_accession`

Workflow: Get structure -> map residue -> assess domain/functional site -> predict destabilization.

> **AlphaFold size limitation**: Very large proteins (>2,700 aa, e.g., BRCA2 at 3,418 aa) may not have AlphaFold predictions via the standard API. Fall back to published structural studies or `PDBe_get_uniprot_mappings` for experimental structures.

## Phase 4.5: Expression Context

Tools: `CELLxGENE_get_expression_data`, `CELLxGENE_get_cell_metadata`, `GTEx_get_median_gene_expression`

Confirms gene expression in disease-relevant tissues. Supports PP4 if highly restricted; challenges classification if not expressed in affected tissue.

## Phase 5: Literature Evidence

Tools: `PubMed_search_articles`, `EuropePMC_search_articles`, `BioRxiv_list_recent_preprints`, `MedRxiv_get_preprint`, `openalex_search_works`, `SemanticScholar_search_papers`

Always flag preprints as NOT peer-reviewed.

## Phase 6: ACMG Classification

Apply all relevant evidence codes (PVS1, PS1, PS3, PM1, PM2, PM5, PP3, PP5 for pathogenic; BA1, BS1, BS3, BP4, BP7 for benign). See `ACMG_CLASSIFICATION.md` for the complete algorithm.

---

## Special Scenarios

**Novel Missense VUS**: Check PM5 (other pathogenic at same residue), get AlphaFold2 structure, apply PM1/PP3 as appropriate.

**Truncating Variant**: Check LOF mechanism, NMD escape, alternative isoforms, ClinGen LOF curation. Apply PVS1 at appropriate strength.

**Splice Variant**: Run SpliceAI, assess canonical splice distance, in-frame skipping potential. Apply PP3/BP7 based on scores.

---

## Output Structure

```markdown
# Variant Interpretation Report: {GENE} {VARIANT}
## Executive Summary
## 1. Variant Identity
## 2. Population Data
## 3. Clinical Database Evidence
## 4. Computational Predictions
## 5. Structural Analysis
## 6. Literature Evidence
## 7. ACMG Classification
## 8. Clinical Recommendations
## 9. Limitations & Uncertainties
## Data Sources
```

File naming: `{GENE}_{VARIANT}_interpretation_report.md`

---

## Clinical Recommendations

**Pathogenic/Likely Pathogenic**: Enhanced screening, risk-reducing options, drug dosing adjustment, reproductive counseling, family cascade screening.

**VUS**: Do not use for medical decisions. Reinterpret in 1-2 years. Pursue functional studies and segregation data.

**Benign/Likely Benign**: Not expected to cause disease. No cascade testing needed.

---

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| Population frequency | gnomAD overall + at least 3 ancestry groups |
| Predictions | At least 3 computational predictors |
| Literature search | At least 2 search strategies |
| ACMG codes | All applicable codes listed |

---

## References

- `ACMG_CLASSIFICATION.md` - Evidence codes, classification algorithm, prediction thresholds, structural/regulatory impact tables
- `CODE_PATTERNS.md` - Reusable code patterns for each workflow phase
- `CHECKLIST.md` - Pre-delivery verification
- `EXAMPLES.md` - Sample interpretations
- `TOOLS_REFERENCE.md` - Tool parameters and fallbacks
