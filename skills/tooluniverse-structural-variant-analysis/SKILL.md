---
name: tooluniverse-structural-variant-analysis
description: Comprehensive structural variant (SV) analysis skill for clinical genomics. Classifies SVs (deletions, duplications, inversions, translocations), assesses pathogenicity using ACMG-adapted criteria, evaluates gene disruption and dosage sensitivity, and provides clinical interpretation with evidence grading. Use when analyzing CNVs, large deletions/duplications, chromosomal rearrangements, or any structural variants requiring clinical interpretation.
---

# Structural Variant Analysis Workflow

Systematic analysis of structural variants (deletions, duplications, inversions, translocations, complex rearrangements) for clinical genomics interpretation using ACMG-adapted criteria.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create SV_analysis_report.md FIRST, then populate progressively
2. **ACMG-style classification** - Pathogenic/Likely Pathogenic/VUS/Likely Benign/Benign with explicit evidence
3. **Evidence grading** - Grade all findings by confidence level (High/Moderate/Limited)
4. **Dosage sensitivity critical** - Gene dosage effects drive SV pathogenicity
5. **Breakpoint precision matters** - Exact gene disruption vs dosage-only effects
6. **Population context essential** - gnomAD SVs for frequency assessment
7. **English-first queries** - Always use English terms in tool calls (gene names, disease names), even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

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

**Tools**:
| Tool | Purpose |
|------|---------|
| `ensembl_lookup_gene` | Gene structure, coordinates, exons |
| `NCBIGene_search` | Official symbol, aliases, description |
| `Gene_Ontology_get_term_info` | Biological process, molecular function |
| `OMIM_search`, `OMIM_get_entry` | Disease associations, inheritance |
| `DisGeNET_search_gene` | Gene-disease association scores |

Classify genes as: **fully contained** (entire gene in SV), **partially disrupted** (breakpoint within gene), or **flanking** (within 1 Mb of breakpoints).

For implementation pseudocode, see `ANALYSIS_PROCEDURES.md` Phase 2.

---

## Phase 3: Dosage Sensitivity Assessment

**Goal**: Determine if affected genes are dosage-sensitive.

**Tools**:
| Tool | Purpose |
|------|---------|
| `ClinGen_search_dosage_sensitivity` | HI/TS scores (0-3, gold standard) |
| `ClinGen_search_gene_validity` | Gene-disease validity level |
| `gnomad_search_variants` | pLI scores for LoF intolerance |
| `ClinGen_search_dosage_sensitivity` | Developmental disorder cases |
| `OMIM_get_entry` | Inheritance pattern (AD suggests dosage sensitivity) |

Key thresholds: ClinGen HI/TS score 3 = definitive dosage sensitivity. pLI >= 0.9 = likely haploinsufficient. See `CLASSIFICATION_GUIDE.md` for full score interpretation tables.

---

## Phase 4: Population Frequency Context

**Goal**: Determine if SV is common (likely benign) or rare (supports pathogenicity).

**Tools**:
| Tool | Purpose |
|------|---------|
| `gnomad_search_variants` | Population SV frequencies |
| `ClinVar_search_variants` | Known pathogenic/benign SVs |
| `ClinGen_search_dosage_sensitivity` | Patient SVs with phenotypes |

Key thresholds: >=1% = BA1 (benign). 0.1-1% = BS1 (strong benign). <0.01% = PM2 (supporting pathogenic). Use >=70% reciprocal overlap to define "same" SV.

---

## Phase 5: Pathogenicity Scoring

**Goal**: Quantitative pathogenicity assessment on 0-10 scale.

Four components weighted: gene content (40%), dosage sensitivity (30%), population frequency (20%), clinical evidence (10%).

Score mapping: 9-10 = Pathogenic, 7-8 = Likely Pathogenic, 4-6 = VUS, 2-3 = Likely Benign, 0-1 = Benign.

For detailed scoring breakdowns and implementation, see `CLASSIFICATION_GUIDE.md` and `ANALYSIS_PROCEDURES.md` Phase 5.

---

## Phase 6: Literature & Clinical Evidence

**Goal**: Find case reports, functional studies, and clinical validation.

**Tools**:
| Tool | Purpose |
|------|---------|
| `PubMed_search_articles` | Peer-reviewed literature |
| `EuropePMC_search_articles` | European literature (additional coverage) |
| `ClinGen_search_dosage_sensitivity` | Patient case database |

Search strategies: gene-specific dosage sensitivity papers, SV-specific case reports, DECIPHER cohort phenotype analysis. See `ANALYSIS_PROCEDURES.md` Phase 6.

---

## Phase 7: ACMG-Adapted Classification

**Goal**: Apply ACMG/ClinGen criteria adapted for SVs.

Key pathogenic codes: PVS1 (deletion of HI gene), PS1 (matches known pathogenic SV), PS2 (de novo), PM2 (absent from controls), PP4 (phenotype match).

Key benign codes: BA1 (MAF >5%), BS1 (MAF >1%), BS3 (no functional effect).

Classification rules: Pathogenic = PVS1+PS1 or 2 Strong. Likely Pathogenic = 1 Very Strong + 1 Moderate, or 3 Moderate. VUS = criteria not met. Likely Benign = 1 Strong + 1 Supporting. Benign = BA1, or 2 Strong benign.

For complete evidence code tables and classification algorithm, see `CLASSIFICATION_GUIDE.md`.

---

## Output

Create report using the template in `REPORT_TEMPLATE.md`. Name files as:
```
SV_analysis_[TYPE]_chr[CHR]_[START]_[END]_[GENES].md
```

---

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| Gene content | All genes in SV region annotated |
| Dosage sensitivity | ClinGen scores for all genes (if available) |
| Population frequency | Check gnomAD SV + ClinVar + DGV |
| Literature search | >=2 search strategies (PubMed + DECIPHER) |
| ACMG codes | All applicable codes listed |

---

## Tools Reference

| Tool | Purpose | Required? |
|------|---------|-----------|
| `ClinGen_search_dosage_sensitivity` | HI/TS scores | **Required** |
| `ClinGen_search_gene_validity` | Gene-disease validity | **Required** |
| `ClinVar_search_variants` | Known pathogenic/benign SVs | **Required** |
| `ClinGen_search_dosage_sensitivity` | Patient cases, phenotypes | Highly recommended |
| `ensembl_lookup_gene` | Gene coordinates, structure | **Required** |
| `OMIM_search`, `OMIM_get_entry` | Gene-disease associations | **Required** |
| `DisGeNET_search_gene` | Additional disease associations | Recommended |
| `PubMed_search_articles` | Literature evidence | Recommended |
| `Gene_Ontology_get_term_info` | Gene function | Supporting |

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
- `CLASSIFICATION_GUIDE.md` - ACMG criteria tables, scoring system, evidence codes, special scenarios, clinical recommendations
- `REPORT_TEMPLATE.md` - Full report template with section structure and file naming
- `ANALYSIS_PROCEDURES.md` - Detailed implementation pseudocode for each phase

## External References

- ClinGen Dosage Sensitivity Map: https://www.ncbi.nlm.nih.gov/projects/dbvar/clingen/
- ACMG SV Guidelines: Riggs et al., Genet Med 2020 (PMID: 31690835)
- `tooluniverse-variant-interpretation` - For SNVs and small indels
