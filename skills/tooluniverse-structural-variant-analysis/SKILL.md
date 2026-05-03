---
name: tooluniverse-structural-variant-analysis
description: Comprehensive structural variant (SV) analysis skill for clinical genomics. Classifies SVs (deletions, duplications, inversions, translocations), assesses pathogenicity using ACMG-adapted criteria, evaluates gene disruption and dosage sensitivity, and provides clinical interpretation with evidence grading. Use when analyzing CNVs, large deletions/duplications, chromosomal rearrangements, or any structural variants requiring clinical interpretation.
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Structural Variant Analysis Workflow

Systematic analysis of structural variants (deletions, duplications, inversions, translocations, complex rearrangements) for clinical genomics interpretation using ACMG-adapted criteria.

**LOOK UP DON'T GUESS** - Always retrieve ClinGen HI/TS scores, gnomAD frequencies, and ClinVar evidence from tools. Do not infer dosage sensitivity from gene function alone.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create SV_analysis_report.md FIRST, then populate progressively
2. **ACMG-style classification** - Pathogenic/Likely Pathogenic/VUS/Likely Benign/Benign with explicit evidence
3. **Evidence grading** - Grade all findings by confidence level (High/Moderate/Limited)
4. **Dosage sensitivity critical** - Gene dosage effects drive SV pathogenicity
5. **Breakpoint precision matters** - Exact gene disruption vs dosage-only effects
6. **Population context essential** - gnomAD SVs for frequency assessment
7. **English-first queries** - Always use English terms in tool calls. Respond in the user's language

---

## Triggers

Use this skill when users:
- Ask about structural variant interpretation
- Have CNV data from array or sequencing
- Ask "is this deletion/duplication pathogenic?"
- Need ACMG classification for SVs
- Want to assess gene dosage effects
- Ask about chromosomal rearrangements
- Have large-scale genomic alterations requiring interpretation

---

## SV Pathogenicity Reasoning (Start Here)

Before any tool call, apply this reasoning to frame the analysis:

**SV pathogenicity depends on what the SV disrupts. A deletion removing an entire gene is likely pathogenic if the gene is haploinsufficient. A duplication is pathogenic if the gene is dosage-sensitive. An inversion is pathogenic only if it disrupts a coding region or regulatory element at the breakpoint.**

Work through these questions in order:

**1. What type is the SV, and what disruption mechanism does it cause?**
- **Deletion**: loss of one copy. Pathogenic if any contained gene is haploinsufficient (ClinGen HI score 3, pLI >= 0.9). A deletion of a dosage-insensitive gene in a gene-dense region may be benign even if large.
- **Duplication**: gain of one copy. Pathogenic if any contained gene is dosage-sensitive (ClinGen TS score 3). Duplications can also disrupt gene regulation if tandem (disrupts reading frame at junction) or if they separate a gene from its enhancer.
- **Inversion**: no copy number change. Pathogenic only at the breakpoints: if one breakpoint falls within an exon (truncation) or separates a gene from its regulatory element. Inversions entirely within gene-poor, regulatory-poor regions are often benign.
- **Translocation**: pathogenic if a breakpoint disrupts a coding region or creates a pathogenic fusion gene. Balanced translocations in parents of affected children warrant special scrutiny.
- **Complex rearrangements**: assess each segment and each breakpoint independently.

**2. Is the disrupted gene dosage-sensitive?**
- ClinGen HI score 3 = definitive haploinsufficiency (deletion of this gene is pathogenic)
- ClinGen HI score 2 = likely haploinsufficient
- pLI >= 0.9 = strong LoF intolerance (supporting haploinsufficiency)
- ClinGen TS score 3 = definitive triplosensitivity (duplication is pathogenic)
- If no ClinGen data: use OMIM inheritance (autosomal dominant = often dosage-sensitive) as weaker evidence

**3. Does the population frequency contextualize the SV?**
- >=1% frequency in gnomAD SV = BA1 (likely benign unless phenotype is extreme)
- <0.01% = supports pathogenicity (PM2)
- Present in unaffected parents = weak evidence against pathogenicity, but not conclusive

**4. Is there clinical precedent?**
- Identical SV in ClinVar as Pathogenic/Likely Pathogenic = strong evidence (PS1)
- De novo occurrence = strong evidence for pathogenicity (PS2)
- Phenotype match to known gene-disease association = supporting evidence (PP4)

Document this reasoning before computing the final score.

---

## Workflow Overview

```
Phase 1: SV IDENTITY & CLASSIFICATION
  Normalize coordinates (hg19/hg38), determine type (DEL/DUP/INV/TRA/CPX),
  calculate size, assess breakpoint precision

Phase 2: GENE CONTENT ANALYSIS
  Identify fully contained genes, partially disrupted genes (breakpoint within),
  flanking genes (within 1 Mb), annotate function and disease associations

Phase 3: DOSAGE SENSITIVITY ASSESSMENT
  ClinGen HI/TS scores, pLI scores, OMIM inheritance patterns,
  gene-disease validity levels

Phase 4: POPULATION FREQUENCY CONTEXT
  gnomAD SV database, ClinVar known SVs, DECIPHER patient cases,
  reciprocal overlap calculation (>=70% = same SV)

Phase 5: PATHOGENICITY SCORING
  Quantitative 0-10 scale: gene content (40%), dosage sensitivity (30%),
  population frequency (20%), clinical evidence (10%)

Phase 6: LITERATURE & CLINICAL EVIDENCE
  PubMed searches, DECIPHER cohort analysis, functional evidence

Phase 7: ACMG-ADAPTED CLASSIFICATION
  Apply SV-specific evidence codes, calculate final classification,
  generate clinical recommendations
```

---

## Phase 1: SV Identity & Classification

**Goal**: Standardize SV notation and classify type.

Capture: chromosome(s), coordinates (start/end in hg19/hg38), SV size, SV type (DEL/DUP/INV/TRA/CPX), breakpoint precision, inheritance pattern (de novo/inherited/unknown).

For SV type definitions, scoring tables, and ACMG code details, see `CLASSIFICATION_GUIDE.md`.

---

## Phase 2: Gene Content Analysis

**Goal**: Annotate all genes affected by the SV.

Tools:
- `ensembl_lookup_gene` - gene structure, coordinates, exons
- `NCBIGene_search` - official symbol, aliases, description
- `Gene_Ontology_get_term_info` - biological process, molecular function
- `OMIM_search`, `OMIM_get_entry` - disease associations, inheritance
- `DisGeNET_search_gene` - gene-disease association scores

Classify genes as: **fully contained** (entire gene in SV), **partially disrupted** (breakpoint within gene), or **flanking** (within 1 Mb of breakpoints).

For implementation pseudocode, see `ANALYSIS_PROCEDURES.md` Phase 2.

---

## Phase 3: Dosage Sensitivity Assessment

**Goal**: Determine if affected genes are dosage-sensitive.

Tools:
- `ClinGen_search_dosage_sensitivity` - HI/TS scores (0-3, gold standard)
- `ClinGen_search_gene_validity` - gene-disease validity level
- `gnomad_search_variants` - pLI scores for LoF intolerance
- `OMIM_get_entry` - inheritance pattern (AD suggests dosage sensitivity)

Interpret scores using the reasoning above. ClinGen HI/TS score 3 = definitive; score 2 = likely; score 1 = little evidence; score 0 = no evidence. Do not equate AD inheritance with haploinsufficiency without ClinGen support.

---

## Phase 4: Population Frequency Context

**Goal**: Determine if SV is common (likely benign) or rare (supports pathogenicity).

Tools:
- `gnomad_search_variants` - population SV frequencies
- `ClinVar_search_variants` - known pathogenic/benign SVs
- `ClinGen_search_dosage_sensitivity` - patient SVs with phenotypes

Use >=70% reciprocal overlap to define "same" SV for comparison. A frequency >=1% triggers BA1 unless there is very strong clinical evidence to override.

---

## Phase 5: Pathogenicity Scoring

**Goal**: Quantitative pathogenicity assessment on 0-10 scale.

Four components weighted: gene content (40%), dosage sensitivity (30%), population frequency (20%), clinical evidence (10%).

Score mapping: 9-10 = Pathogenic, 7-8 = Likely Pathogenic, 4-6 = VUS, 2-3 = Likely Benign, 0-1 = Benign.

For detailed scoring breakdowns and implementation, see `CLASSIFICATION_GUIDE.md` and `ANALYSIS_PROCEDURES.md` Phase 5.

---

## Phase 6: Literature & Clinical Evidence

**Goal**: Find case reports, functional studies, and clinical validation.

Tools:
- `PubMed_search_articles` - peer-reviewed literature
- `EuropePMC_search_articles` - additional coverage
- `ClinGen_search_dosage_sensitivity` - patient case database

Search strategies: gene-specific dosage sensitivity papers, SV-specific case reports, phenotype-gene associations. See `ANALYSIS_PROCEDURES.md` Phase 6.

---

## Phase 7: ACMG-Adapted Classification

**Goal**: Apply ACMG/ClinGen criteria adapted for SVs and generate a final classification with explicit evidence summary.

The LLM knows the ACMG criteria codes and combination rules. Apply them to the evidence gathered in Phases 1-6. Key points to verify with tool data:
- PVS1 applies to deletions of genes with ClinGen HI score >= 2 or pLI >= 0.9
- PS2 requires confirmed de novo status (check parental genotypes if available)
- PM2 requires absence from population databases at >=70% reciprocal overlap

For complete evidence code tables and classification algorithm, see `CLASSIFICATION_GUIDE.md`.

---

## Output

Create report using the template in `REPORT_TEMPLATE.md`. Name files as:
```
SV_analysis_[TYPE]_chr[CHR]_[START]_[END]_[GENES].md
```

---

## Required Tools Reference

- `ClinGen_search_dosage_sensitivity` - HI/TS scores (required for all deletions/duplications)
- `ClinGen_search_gene_validity` - gene-disease validity (required)
- `ClinVar_search_variants` - known pathogenic/benign SVs (required)
- `ensembl_lookup_gene` - gene coordinates, structure (required)
- `OMIM_search`, `OMIM_get_entry` - gene-disease associations (required)
- `gnomad_search_variants` - population frequency and pLI (required)
- `DisGeNET_search_gene` - additional disease associations (recommended)
- `PubMed_search_articles` - literature evidence (recommended)
- `Gene_Ontology_get_term_info` - gene function (supporting)

---

## When NOT to Use This Skill

- **Single nucleotide variants (SNVs)** - Use `tooluniverse-variant-interpretation`
- **Small indels (<50 bp)** - Use variant interpretation skill
- **Somatic variants in cancer** - Different framework needed
- **Mitochondrial variants** - Specialized interpretation required
- **Repeat expansions** - Different mechanism

Use this skill for **structural variants >=50 bp** requiring dosage sensitivity assessment and ACMG-adapted classification.

---

## Reference Files

- `EXAMPLES.md` - Sample SV interpretations with worked examples
- `CLASSIFICATION_GUIDE.md` - ACMG criteria, scoring system, evidence codes, special scenarios, clinical recommendations
- `REPORT_TEMPLATE.md` - Full report template with section structure and file naming
- `ANALYSIS_PROCEDURES.md` - Detailed implementation pseudocode for each phase

## External References

- ClinGen Dosage Sensitivity Map: https://www.ncbi.nlm.nih.gov/projects/dbvar/clingen/
- ACMG SV Guidelines: Riggs et al., Genet Med 2020 (PMID: 31690835)
- `tooluniverse-variant-interpretation` - For SNVs and small indels
