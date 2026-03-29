---
name: tooluniverse-proteomics-analysis
description: Analyze mass spectrometry proteomics data including protein quantification, differential expression, post-translational modifications (PTMs), and protein-protein interactions. Processes MaxQuant, Spectronaut, DIA-NN, and other MS platform outputs. Performs normalization, statistical analysis, pathway enrichment, and integration with transcriptomics. Use when analyzing proteomics data, comparing protein abundance between conditions, identifying PTM changes, studying protein complexes, integrating protein and RNA data, discovering protein biomarkers, or conducting quantitative proteomics experiments.
---

# Proteomics Analysis

Comprehensive analysis of mass spectrometry-based proteomics data from protein identification through quantification, differential expression, post-translational modifications, and systems-level interpretation.

## When to Use This Skill

**Triggers**: User has proteomics MS output files, asks about protein abundance/expression, differential protein expression, PTM analysis, protein-RNA correlation, multi-omics integration involving proteomics, protein complex/interaction analysis, or proteomics biomarker discovery.

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Core Capabilities

- **Data Import**: MaxQuant, Spectronaut, DIA-NN, Proteome Discoverer, FragPipe outputs
- **Quality Control**: Missing value analysis, intensity distributions, sample clustering
- **Normalization**: Median, quantile, TMM, VSN — choice depends on experimental design (see Interpretation Framework)
- **Imputation**: MinProb (MNAR), KNN (MAR), QRILC for missing values
- **Differential Expression**: Limma, DEP, MSstats for statistical testing
- **PTM Analysis**: Phospho-site localization, PTM enrichment, kinase prediction
- **Protein-RNA Integration**: Correlation analysis, translation efficiency
- **Pathway Enrichment**: Over-representation and GSEA for protein sets
- **PPI Analysis**: Protein complex detection, interaction networks via STRING/IntAct

## Workflow Overview

```
Input: MS Proteomics Data
    |
Phase 1: Data Import & QC
Phase 2: Preprocessing (filter, impute, normalize)
Phase 3: Differential Expression Analysis
Phase 4: PTM Analysis (if applicable)
Phase 5: Functional Enrichment (GO, KEGG, Reactome)
Phase 6: Protein-Protein Interactions (STRING networks)
Phase 7: Multi-Omics Integration (optional, protein-RNA correlation)
Phase 8: Generate Report
```

See [PHASE_DETAILS.md](PHASE_DETAILS.md) for detailed procedures per phase.

## Integration with ToolUniverse

| Skill | Used For | Phase |
|-------|----------|-------|
| `tooluniverse-gene-enrichment` | Pathway enrichment | Phase 5 |
| `tooluniverse-protein-interactions` | PPI networks | Phase 6 |
| `tooluniverse-rnaseq-deseq2` | RNA-seq for integration | Phase 7 |
| `tooluniverse-multi-omics-integration` | Cross-omics analysis | Phase 7 |
| `tooluniverse-target-research` | Protein annotation | Phase 8 |

## Quantified Minimums

- At least 500 proteins quantified (human: 3,000+ is reasonable; 10,000+ is deep coverage)
- At least 3 biological replicates per condition (non-negotiable for reliable statistics)
- Filter to proteins with 2+ unique peptides (single-peptide IDs are not reported as DE)
- Statistical test: limma or t-test with Benjamini-Hochberg multiple testing correction
- Pathway enrichment: at least one method (GO, KEGG, or Reactome)
- Report must include: QC summary, DE results with volcano plot, pathway analysis, visualizations

## Interpretation Framework

### Starting Point: Experimental Design

Quantitative proteomics compares protein abundance. LOOK UP DON'T GUESS — always verify the experimental method, platform, and replicate count before choosing an analysis strategy.

**Quantification strategy decision tree:**
- Cell culture, high accuracy needed → **SILAC** (ratios within same MS run, most accurate, but culture-only)
- Multiple conditions, multiplexing needed → **TMT/iTRAQ** (up to 18-plex in one run; TMM/VSN normalization; beware ratio compression artifact that reduces observed fold-changes)
- Discovery study, flexible design → **Label-free (LFQ)** (intensity-based; median/quantile normalization; more missing values; wider dynamic range)
- **Replicates**: n < 3 = unreliable fold changes (variance cannot be estimated). Minimum n = 3 biological replicates; n >= 4 preferred for clinical samples. Never report significance from duplicates.
- **FDR cutoff**: Benjamini-Hochberg correction mandatory. FDR < 0.05 standard; FDR < 0.01 stringent. Never report unadjusted p-values alone.

### Protein Identification Reasoning

Protein identification from MS data follows a logical chain. LOOK UP DON'T GUESS — search UniProt and STRING for protein annotation rather than inferring function from name alone.

1. **Peptide mass fingerprinting (PMF)**: Intact protein digested → measured peptide masses compared against theoretical digest of all database proteins. A match requires >=4 peptides covering >=15% of the protein sequence. Single-peptide hits are unreliable (could match multiple proteins).
2. **Tandem MS (MS/MS)**: Fragment ion spectra matched to peptide sequences via search engines (Andromeda, SEQUEST, X!Tandem). Each peptide-spectrum match (PSM) scored; only PSMs above FDR threshold count. Unique peptides (mapping to one protein) are essential — shared peptides cannot distinguish between protein isoforms.
3. **Protein inference**: Multiple peptides → protein groups. When peptides are shared between homologs, report the protein group (not individual proteins). Use `proteins_api_search` or `uniprot_search_proteins` to resolve ambiguous protein groups.
4. **Coverage matters**: 2+ unique peptides is the minimum for a confident protein ID. Proteins identified by a single unique peptide should be flagged as tentative.

### Post-Translational Modification (PTM) Analysis Reasoning

PTMs (phosphorylation, ubiquitination, acetylation, glycosylation) add biological complexity beyond protein abundance.

1. **Site localization**: A phospho-site is confidently localized only if the localization probability > 0.75 (MaxQuant) or ptmRS score > 75 (Proteome Discoverer). Ambiguous sites should not be reported as specific residue modifications.
2. **Enrichment is required**: Without phospho-enrichment (TiO2, IMAC), only the most abundant phosphopeptides are detected (~1% of phosphoproteome). An absence of a phospho-site in non-enriched data does not mean it is absent biologically.
3. **Kinase prediction**: If phospho-sites are identified, predict upstream kinases using motif analysis. Cross-reference with `OpenTargets_get_target_safety_profile_by_ensemblID` for kinase-disease associations. LOOK UP kinase-substrate relationships in PhosphoSitePlus rather than guessing from sequence motif alone.
4. **Stoichiometry**: A protein can be 5% or 95% phosphorylated at a given site — this matters enormously for function but is hard to measure. Report whether data supports stoichiometry estimation or only site identification.

### Differential Expression Thresholds

- **Strong**: padj < 0.01, FC > 2.0, ≥5 unique peptides, <20% missing
- **Moderate**: padj 0.01-0.05, FC 1.5-2.0, 2-5 peptides, 20-50% missing
- **Weak/unreliable**: padj 0.05-0.1, FC 1.2-1.5, 1-2 peptides (single-peptide proteins are unreliable), >50% missing (imputation needed)

### Evidence Grading

- **T1**: Validated by orthogonal method (Western blot, PRM) + functional study
- **T2**: Significant DE (padj < 0.05, FC > 1.5) in 2+ biological replicates
- **T3**: Significant DE in 1 experiment, or significant but low FC
- **T4**: Identified but not quantified, or single peptide identification

### Synthesis Questions

1. **How many proteins are differentially expressed?** (>500 DE proteins suggests global perturbation; <50 suggests targeted effect)
2. **Are key pathway proteins concordantly regulated?** (all subunits of a complex changing = high confidence)
3. **Do proteomics results correlate with transcriptomics?** (low correlation is common — post-translational regulation)
4. **Are PTM changes driving the phenotype?** (check phosphoproteomics if available)
5. **What is the coverage relative to the expected proteome?** (human: ~10K quantified is good; <3K is limited)

---

## Limitations

- **Platform-specific**: Optimized for MS-based proteomics (not Western blot quantification)
- **Missing values**: High missing rate (>50% per protein) limits statistical power
- **PTM analysis**: Requires enrichment protocols for comprehensive PTM profiling
- **Absolute quantification**: Relative abundance only (unless TMT/SILAC used)
- **Protein isoforms**: Typically collapsed to gene level
- **Dynamic range**: MS has limited dynamic range vs mRNA sequencing

## References

**Methods**: MaxQuant (doi:10.1038/nbt.1511), Limma for proteomics (doi:10.1093/nar/gkv007), DEP workflow (doi:10.1038/nprot.2018.107)

**Databases**: [STRING](https://string-db.org), [PhosphoSitePlus](https://www.phosphosite.org), [CORUM](https://mips.helmholtz-muenchen.de/corum)

## Reference Files

- [PHASE_DETAILS.md](PHASE_DETAILS.md) - Detailed procedures for each analysis phase, including report template
