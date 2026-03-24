---
name: tooluniverse-variant-functional-annotation
description: >
  Comprehensive functional annotation of protein variants — pathogenicity, population frequency,
  structural context, and clinical significance. Integrates ProtVar (map_variant, get_function,
  get_population) for protein-level mapping and structural context, ClinVar for clinical classifications,
  gnomAD for population frequency with ancestry data, CADD for deleteriousness scores, and ClinGen
  for gene-disease validity. Produces a structured variant annotation report with evidence grading.
  Use when asked about protein variant impact, missense variant pathogenicity, ProtVar annotation,
  variant functional context, or combining population and structural evidence for a variant.
---

# Protein Variant Functional Annotation

Comprehensive functional annotation of protein variants by combining ProtVar structural/functional
context, ClinVar clinical classifications, gnomAD population frequencies, CADD deleteriousness
scoring, and ClinGen gene-disease validity.

**Differentiation from tooluniverse-variant-interpretation**: This skill focuses specifically on
**protein-level functional evidence** — structural mapping, residue context, protein domain impact,
and population allele frequencies. It does NOT produce full ACMG classifications or treatment
recommendations. Use `tooluniverse-variant-interpretation` for complete ACMG clinical classification.

## When to Use This Skill

**Triggers**:
- "Annotate variant [GENE]:[protein_change]" (e.g., "TP53:p.R175H")
- "What is the functional impact of [variant]?"
- "ProtVar annotation for [HGVS or rsID]"
- "Population frequency of [variant]"
- "Is [variant] in a conserved domain?"
- "Structural context of [amino acid change]"

**Use Cases**:
1. **Protein Structure Mapping**: Map variant to 3D structure coordinates via ProtVar
2. **Functional Context**: Residue conservation, domain membership, active/binding site proximity
3. **Population Frequency**: gnomAD allele frequency with ancestry breakdown
4. **Deleteriousness Scoring**: CADD PHRED score + AlphaMissense/SIFT/PolyPhen
5. **Multi-Source Annotation**: OpenCRAVAT 182+ annotators in a single call (ClinVar, gnomAD, REVEL, SpliceAI, etc.)
6. **Clinical Evidence**: ClinVar pathogenicity classifications and submitter counts
7. **Gene-Disease Validity**: ClinGen curated gene-disease evidence strength

---

## KEY PRINCIPLES

1. **ProtVar-first** — ProtVar provides the richest protein-level context; always start here
2. **Notation flexibility** — Accept HGVS (c./p.), genomic (chr:pos:ref:alt), rsID, or gene+AA change
3. **Population frequency mandatory** — Always report gnomAD AF and note ancestry-specific values
4. **Structural context required for missense** — Domain, active site, conservation
5. **Report-first approach** — Create report file FIRST, update progressively
6. **Evidence grading mandatory** — Grade all claims T1-T4

---

## Evidence Grading

| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | [T1] | ClinVar pathogenic with >=3 submitters; ClinGen definitive gene-disease |
| T2 | [T2] | ClinVar pathogenic 1-2 submitters; CADD PHRED >25; functional studies cited |
| T3 | [T3] | Computational prediction (CADD 15-25, AlphaMissense, SIFT/PolyPhen); ProtVar structural flag |
| T4 | [T4] | Population frequency annotation only; domain membership annotation |

---

## Workflow Overview

```
Variant Input (HGVS / genomic / rsID / gene+protein_change)
|
+-- PHASE 0: Variant Notation Normalization
|   Resolve to canonical HGVS and UniProt position; confirm gene/transcript
|
+-- PHASE 1: ProtVar Protein-Level Annotation
|   map_variant -> structural coordinates, residue info, domain, active site
|   get_function -> conservation, functional impact prediction
|   get_population -> minor allele frequencies per ancestry
|
+-- PHASE 2: Population Frequency (gnomAD)
|   gnomad_get_variant -> AF global + ancestry-specific; homozygote count
|
+-- PHASE 3: Deleteriousness Scores (CADD)
|   CADD_get_variant_score -> PHRED score; raw C-score
|
+-- PHASE 3b: Multi-Source Annotation (OpenCRAVAT)
|   OpenCRAVAT_annotate_variant -> 182+ annotators in one call
|   (ClinVar, gnomAD, SIFT, PolyPhen-2, REVEL, AlphaMissense, SpliceAI, etc.)
|
+-- PHASE 4: Clinical Classification (ClinVar)
|   clinvar_search_variants -> pathogenicity, review status, submitter count
|   clinvar_get_variant_details -> full submission breakdown
|
+-- PHASE 5: Gene-Disease Validity (ClinGen)
|   ClinGen_search_gene_validity -> evidence classification for gene-disease pair
|
+-- SYNTHESIS: Integrated Annotation Report
    Structural context + population + deleteriousness + clinical + gene-disease
```

---

## Phase 0: Variant Notation Normalization

**Objective**: Establish canonical notation before calling any tools.

Accepted input forms:
- HGVS coding: `NM_000546.6:c.524G>A`
- HGVS protein: `NP_000537.3:p.Arg175His`
- Gene + protein change: `TP53 R175H` or `TP53 p.Arg175His`
- Genomic: `chr17:7674220:G:A` (hg38)
- rsID: `rs28934578`

If input is a gene + protein change shorthand (e.g., "TP53 R175H"):
- Expand to full one-letter or three-letter notation for ProtVar: `TP53 Arg175His`
- Note the canonical transcript in report

---

## Phase 1: ProtVar Protein-Level Annotation

**Objective**: Map variant to protein structure and get residue-level functional context.

### Tools

**ProtVar_map_variant**:
- **Input**: `hgvs` (str) OR `genomic` (str, format: `chr:pos:ref:alt`) OR `protein_variant` (str, format: `GENE pAA#AA`)
- **Output**: Protein position, UniProt accession, residue, secondary structure, 3D coordinates, domain annotations, active/binding site flags
- **Critical**: Provide at least one of hgvs, genomic, or protein_variant — validation returns error if all are absent

**ProtVar_get_function**:
- **Input**: `accession` (str, UniProt ID from map_variant result), `position` (int)
- **Output**: Conservation scores, functional impact annotations, domain membership, post-translational modification sites

**ProtVar_get_population**:
- **Input**: `accession` (str), `position` (int)
- **Output**: Population allele frequencies per variant at this protein position from gnomAD

### Workflow

1. Call `ProtVar_map_variant` with best available notation
2. Extract `accession` (UniProt ID) and `position` (residue number) from result
3. Call `ProtVar_get_function(accession=..., position=...)` for conservation and domain data
4. Call `ProtVar_get_population(accession=..., position=...)` for population context

### Key Fields to Extract

- `secondary_structure`: helix/sheet/loop — loop variants often less constrained
- `domain`: domain name if in annotated domain
- `active_site` / `binding_site`: flag as critical if present
- `conservation_score`: higher = more evolutionarily constrained
- `af_population`: allele frequency values per ancestry group

---

## Phase 2: Population Frequency (gnomAD)

**Objective**: Get precise allele frequency with ancestry breakdown.

### Tools

**gnomad_get_variant**:
- **Input**: `variant_id` (str, format: `chrom-pos-ref-alt` in hg38, e.g., `17-7674220-G-A`)
- **Output**: Global AF, allele count, homozygote count, ancestry-specific frequencies, coverage

**gnomad_search_variants** (fallback if exact variant ID unknown):
- **Input**: `gene_id` (str, Ensembl gene ID) or `region` (str)
- **Output**: Variant list with frequencies

### Interpretation

| gnomAD AF | Interpretation |
|-----------|----------------|
| > 0.01 (1%) | Common; unlikely highly penetrant pathogenic variant |
| 0.001-0.01 | Low frequency; possible founder variant |
| < 0.001 | Rare; consistent with pathogenic variant |
| Not in gnomAD | Absent from gnomAD; very rare or de novo |

Always report: global AF, max population AF (which ancestry), homozygote count.
Absent from gnomAD = noteworthy; do not interpret as pathogenic alone.

---

## Phase 3: Deleteriousness Scores (CADD)

**Objective**: Quantify predicted deleteriousness with CADD PHRED score.

### Tools

**CADD_get_variant_score**:
- **Input**: `chrom` (str), `pos` (int), `ref` (str), `alt` (str), `genome` (str, default "GRCh38")
- **Output**: PHRED score (0-99), raw C-score

**CADD_get_position_scores** (for nearby variant context):
- **Input**: `chrom` (str), `pos` (int), `genome` (str)
- **Output**: Scores for all possible variants at this position

### Thresholds

| CADD PHRED | Interpretation |
|------------|----------------|
| >= 30 | Top 0.1% most deleterious — strong computational evidence |
| 20-29 | Top 1-10% — moderate computational evidence |
| 15-19 | Moderate |
| < 15 | Not strongly deleterious computationally |

CADD >= 20 supports PP3 (pathogenic criterion); CADD < 10 supports BP4 (benign criterion) in ACMG.

---

## Phase 3b: Multi-Source Annotation (OpenCRAVAT)

**Objective**: Obtain comprehensive variant annotation from 182+ sources in a single call, supplementing individual tool queries from Phases 2-3.

OpenCRAVAT aggregates scores and classifications from dozens of annotators. This phase is especially valuable when you need multiple prediction scores (REVEL, AlphaMissense, SpliceAI, DANN, FATHMM, etc.) beyond what CADD alone provides.

### Tools

**OpenCRAVAT_annotate_variant**:
- **Input**: `chrom` (str, e.g., `"chr17"`), `pos` (int, 1-based GRCh38), `ref_base` (str), `alt_base` (str), `annotators` (optional comma-separated string)
- **Output**: Gene name, amino acid change, consequence type, plus all requested annotator results
- **Note**: `chrom` accepts both `"chr17"` and `"17"` formats -- `chr` prefix is auto-added if missing

**Common annotator sets** (pass as comma-separated string in `annotators`):
- **Pathogenicity focus**: `"clinvar,gnomad3,sift,polyphen2,revel,alphamissense,cadd_exome"`
- **Splicing focus**: `"spliceai,dbscsnv,maxentscan"`
- **Conservation focus**: `"gerp,phastcons,phylop"`
- **Comprehensive**: `"clinvar,gnomad3,sift,polyphen2,revel,alphamissense,spliceai,cadd_exome,gerp,dann,fathmm,dbsnp"`

If `annotators` is omitted, only basic variant annotation (gene, consequence) is returned.

**OpenCRAVAT_list_annotators** (reference):
- **Input**: `category` (optional, e.g., `"annotator"`)
- **Output**: Full list of available annotators with names, titles, descriptions
- Use to discover available annotators before calling `annotate_variant`

### Workflow

1. Convert variant to GRCh38 genomic coordinates (from Phase 0)
2. Call `OpenCRAVAT_annotate_variant` with appropriate annotator set:
   - For missense: use pathogenicity + conservation annotators
   - For splice-region: include `spliceai,dbscsnv`
   - For non-coding: include `gerp,phastcons,dann`
3. Extract and compare scores across annotators:
   - REVEL >= 0.5 suggests pathogenic (strong at >= 0.75) [T3]
   - AlphaMissense >= 0.564 "likely pathogenic" [T3]
   - SpliceAI delta >= 0.5 suggests splice impact [T3]
4. Report concordance/discordance across prediction tools

### Integration with Other Phases

OpenCRAVAT results can **supplement or validate** findings from individual tools:
- Compare OpenCRAVAT ClinVar annotation with Phase 4 ClinVar direct query
- Compare OpenCRAVAT gnomAD data with Phase 2 gnomAD direct query
- Use REVEL/AlphaMissense from OpenCRAVAT alongside CADD from Phase 3
- If CADD is unavailable, OpenCRAVAT `cadd_exome` annotator provides an alternative

---

## Phase 4: Clinical Classification (ClinVar)

**Objective**: Retrieve existing pathogenicity classifications and review status.

### Tools

**clinvar_search_variants**:
- **Input**: `query` (str) — use gene + protein change, e.g., `"TP53 R175H"` or HGVS
- **Output**: Variant list with clinical significance, review status, submission count

**clinvar_get_variant_details**:
- **Input**: `variant_id` (str) — ClinVar variation ID from search result
- **Output**: Full submission breakdown, evidence types, date of last review

### Review Status Mapping

| Stars | Status | Interpretation |
|-------|--------|----------------|
| 4 | Practice guideline | Highest confidence |
| 3 | Expert panel reviewed | High confidence |
| 2 | Multiple submitters, no conflict | Good confidence |
| 1 | Single submitter | Lower confidence |
| 0 | Conflicting / not reviewed | Use with caution |

---

## Phase 5: Gene-Disease Validity (ClinGen)

**Objective**: Confirm the gene-disease relationship before interpreting variant pathogenicity.

### Tools

**ClinGen_search_gene_validity**:
- **Input**: `gene_symbol` (str) and/or `disease_label` (str)
- **Output**: Curated gene-disease pairs with evidence classification

### ClinGen Classifications

| Classification | Meaning |
|----------------|---------|
| Definitive | Strong human genetic evidence; gene causes disease |
| Strong | Consistent evidence across multiple families |
| Moderate | Limited but supportive evidence |
| Limited | Minimal evidence; uncertain relationship |
| Disputed | Conflicting evidence |
| Refuted | Evidence against gene-disease relationship |

If gene-disease pair is Disputed or Refuted, note this prominently — pathogenic ClinVar variants in this gene should be interpreted cautiously.

---

## Synthesis: Integrated Annotation Report

```
# Variant Functional Annotation: [GENE] [VARIANT]
**Generated**: YYYY-MM-DD
**Input**: [original user input]
**Canonical notation**: [HGVS c. and p.]

## Executive Summary
(2-3 sentences: structural context, population frequency, pathogenicity signal)

## 1. Variant Identity
(Canonical HGVS, gene, transcript, consequence type, amino acid change)

## 2. Protein Structural Context [T3-T4]
(From ProtVar: domain, secondary structure, active/binding site, 3D coordinates)

## 3. Functional Annotations [T3]
(Conservation, predicted impact, PTM proximity, domain function)

## 4. Population Frequency [T4]
(gnomAD global AF, max population AF, homozygote count, ProtVar population data)

## 5. Deleteriousness Score [T3]
(CADD PHRED, interpretation tier)

## 6. Clinical Classification [T1-T2]
(ClinVar significance, review stars, submitter count)

## 7. Gene-Disease Validity [T1]
(ClinGen classification for relevant disease)

## 8. Integrated Assessment
(Concordance table across evidence types; net interpretation)

## Data Gaps
(Any phase with no data; confidence caveats)
```

### Concordance Table

| Evidence Type | Value | Tier | Direction |
|---------------|-------|------|-----------|
| ClinVar | Pathogenic (3-star) | T1 | Pathogenic |
| gnomAD AF | 0.000008 | T4 | Rare (consistent) |
| CADD PHRED | 32 | T3 | Deleterious |
| ProtVar domain | DNA-binding domain | T3 | High-impact location |
| ProtVar active site | Yes | T3 | Critical residue |
| REVEL (OpenCRAVAT) | 0.85 | T3 | Pathogenic prediction |
| AlphaMissense (OpenCRAVAT) | 0.92 | T3 | Likely pathogenic |
| ClinGen | Definitive | T1 | Gene confirmed |

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `ProtVar_map_variant` (hgvs) | ProtVar with genomic notation | ProtVar with protein_variant |
| `gnomad_get_variant` | `gnomad_search_variants` by gene | `OpenCRAVAT_annotate_variant` with `gnomad3` annotator |
| `CADD_get_variant_score` | `OpenCRAVAT_annotate_variant` with `cadd_exome` annotator | Note CADD unavailable |
| `OpenCRAVAT_annotate_variant` | Individual tool calls (Phases 2-5) | Note OpenCRAVAT unavailable |
| `clinvar_search_variants` | `OpenCRAVAT_annotate_variant` with `clinvar` annotator | Note no ClinVar entry |
| `ClinGen_search_gene_validity` | Search by disease label | Note gene-disease not curated |

---

## Tool Parameter Reference (Critical)

| Tool | Parameter Notes |
|------|----------------|
| `ProtVar_map_variant` | Requires at least one of: `hgvs`, `genomic`, `protein_variant` |
| `ProtVar_get_function` | Needs `accession` (UniProt ID) + `position` (int) from map_variant |
| `ProtVar_get_population` | Same as get_function inputs |
| `gnomad_get_variant` | `variant_id` format: `chrom-pos-ref-alt` (hg38, no "chr" prefix) |
| `CADD_get_variant_score` | `chrom` without "chr" prefix; `genome` default is GRCh38 |
| `clinvar_search_variants` | Use gene + protein change as plain text query |
| `OpenCRAVAT_annotate_variant` | `chrom` (auto-adds "chr" prefix), `pos` (1-based GRCh38), `ref_base`, `alt_base`; `annotators` is comma-separated string |
| `OpenCRAVAT_list_annotators` | Optional `category` filter; returns 182+ annotator definitions |

---

## Limitations

- **ProtVar**: Covers UniProt canonical isoforms only; alternative isoforms not mapped
- **gnomAD**: Based on gnomAD v4 (exomes + genomes); mitochondrial variants have separate AF
- **CADD**: Computational prediction only [T3]; does not replace experimental evidence
- **ClinVar**: Reflects submitter interpretations; star rating reflects concordance not accuracy
- **ProtVar structural coordinates**: Derived from AlphaFold2 where no experimental structure exists

---

## References

- ProtVar: https://www.ebi.ac.uk/protvar
- gnomAD: https://gnomad.broadinstitute.org
- CADD: https://cadd.gs.washington.edu
- ClinVar: https://www.ncbi.nlm.nih.gov/clinvar
- ClinGen: https://clinicalgenome.org
- OpenCRAVAT: https://opencravat.org
