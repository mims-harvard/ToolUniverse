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

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use This Skill

**Triggers**:
- "Annotate variant [GENE]:[protein_change]" (e.g., "TP53:p.R175H")
- "What is the functional impact of [variant]?"
- "ProtVar annotation for [HGVS or rsID]"
- "Population frequency of [variant]"
- "Is [variant] in a conserved domain?"
- "Structural context of [amino acid change]"

---

## Pathogenicity Reasoning Framework

Assessing variant pathogenicity requires building a converging case from four independent evidence dimensions. No single metric is sufficient — concordance across dimensions defines confidence.

**1. Conservation: Is the position evolutionarily constrained?**
If the residue has been maintained across vertebrates or all eukaryotes, mutation is likely to disrupt function. ProtVar's conservation score and GERP/PhastCons from OpenCRAVAT quantify this. High conservation at a position raises prior probability of pathogenicity, especially for missense variants. Low conservation suggests the position tolerates variation.

**2. Location: Is it in a functionally critical region?**
A variant in an annotated active site or binding site is mechanistically impactful regardless of its frequency. Domain membership matters: a variant in the DNA-binding domain of a transcription factor is more concerning than one in an unstructured linker. Secondary structure context from ProtVar (helix, sheet, loop) adds resolution — loop residues are typically less constrained. Post-translational modification sites (phosphorylation, ubiquitination) are also critical positions.

**3. Population frequency: Is it rare enough to be pathogenic?**
Highly penetrant pathogenic variants for rare diseases are almost always absent from population databases or present at very low frequency (gnomAD AF < 0.001). A variant present in 1% of the population is unlikely to cause a severe early-onset Mendelian disease. Note the max population AF (which ancestry has it highest) and the homozygote count — homozygotes in gnomAD argue against full penetrance for a recessive condition.

**4. Computational prediction: Do algorithms agree?**
CADD PHRED ≥ 30 puts the variant in the top 0.1% most predicted-deleterious changes. REVEL ≥ 0.75 and AlphaMissense ≥ 0.564 indicate likely pathogenic predictions. When multiple tools agree, confidence in the computational signal increases; when they disagree, weight experimental evidence more heavily. CADD ≥ 20 supports the PP3 ACMG criterion; CADD < 10 supports BP4.

**Synthesizing the four dimensions**: A variant that is highly conserved, located in an active site, absent from gnomAD, and predicted deleterious by CADD and REVEL represents a strong pathogenicity signal even before looking at ClinVar. Conversely, a variant at a non-conserved position in a disordered region, present in 0.1% of the population, and predicted benign is unlikely pathogenic even if a ClinVar submitter once classified it as VUS. ClinVar classifications (especially multi-star entries from expert panels) override computational predictions; ClinGen gene-disease validity sets the context for interpreting any variant in that gene.

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

- **T1**: ClinVar pathogenic with ≥3 submitters; ClinGen definitive gene-disease
- **T2**: ClinVar pathogenic 1-2 submitters; CADD PHRED >25; functional studies cited
- **T3**: Computational prediction (CADD 15-25, AlphaMissense, SIFT/PolyPhen); ProtVar structural flag
- **T4**: Population frequency annotation only; domain membership annotation

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
|   ClinVar_search_variants -> pathogenicity, review status, submitter count
|   ClinVar_get_variant_details -> full submission breakdown
|
+-- PHASE 5: Gene-Disease Validity (ClinGen)
|   ClinGen_search_gene_validity -> evidence classification for gene-disease pair
|
+-- SYNTHESIS: Integrated Annotation Report
    Structural context + population + deleteriousness + clinical + gene-disease
```

---

## Phase 0: Variant Notation Normalization

Accepted input forms: HGVS coding (`NM_000546.6:c.524G>A`), HGVS protein (`NP_000537.3:p.Arg175His`), gene + protein change (`TP53 R175H`), genomic (`chr17:7674220:G:A` hg38), or rsID. Expand shorthand to full three-letter notation for ProtVar (e.g., "TP53 R175H" → "TP53 Arg175His").

---

## Phase 1: ProtVar Protein-Level Annotation

`ProtVar_map_variant` takes `hgvs`, `genomic` (chr:pos:ref:alt), or `protein_variant` (GENE pAA#AA) — at least one is required. Extract `accession` (UniProt ID) and `position` from the result.

`ProtVar_get_function(accession, position)` returns conservation scores, domain membership, PTM sites, and functional impact annotations.

`ProtVar_get_population(accession, position)` returns gnomAD allele frequencies per ancestry from ProtVar's aggregation.

**Key fields to reason over**: `active_site` / `binding_site` flags are high-priority signals; `conservation_score` quantifies evolutionary constraint at this position; `domain` membership places the variant in biological context; `secondary_structure` (loop variants are typically less constrained than helix/sheet).

---

## Phase 2: Population Frequency (gnomAD)

`gnomad_get_variant` takes `variant_id` in the format `chrom-pos-ref-alt` (hg38, no "chr" prefix). Always report the global AF, the maximum population-specific AF, and the homozygote count. Use `gnomad_search_variants` as fallback when the exact variant ID is not known.

Absence from gnomAD is noteworthy but does not independently establish pathogenicity.

---

## Phase 3: Deleteriousness Scores (CADD)

`CADD_get_variant_score` takes `chrom` (without "chr" prefix), `pos`, `ref`, `alt`, `genome` (default "GRCh38"). CADD PHRED ≥ 30 is top 0.1% most deleterious; ≥ 20 is top 1-10%. Use `OpenCRAVAT_annotate_variant` with `annotators="cadd_exome"` as fallback if CADD is unavailable.

---

## Phase 3b: Multi-Source Annotation (OpenCRAVAT)

`OpenCRAVAT_annotate_variant` takes `chrom`, `pos` (1-based GRCh38), `ref_base`, `alt_base`, and an optional comma-separated `annotators` string. The `chrom` parameter auto-adds the "chr" prefix if missing.

For missense variants, use annotators `"clinvar,gnomad3,sift,polyphen2,revel,alphamissense,cadd_exome"`. For splice-region variants, add `"spliceai,dbscsnv"`. For non-coding variants, add `"gerp,phastcons,dann"`.

**When scores disagree**: If REVEL says benign but CADD says deleterious, weight REVEL more heavily for missense (it is specifically trained on missense). If multiple tools agree, the signal is more reliable. Document the concordance pattern in the report.

---

## Phase 4: Clinical Classification (ClinVar)

`ClinVar_search_variants(query="GENE protein_change")` returns pathogenicity classifications and review status. `ClinVar_get_variant_details(variant_id)` provides the full submission breakdown.

ClinVar review status (star ratings): 4 stars = practice guideline (highest confidence); 3 = expert panel reviewed; 2 = multiple submitters without conflict; 1 = single submitter; 0 = conflicting or not reviewed. Single-submitter VUS classifications carry limited weight; expert panel classifications override computational predictions.

If ClinVar is unavailable, use `OpenCRAVAT_annotate_variant` with `annotators="clinvar"` as a fallback.

---

## Phase 5: Gene-Disease Validity (ClinGen)

`ClinGen_search_gene_validity(gene_symbol, disease_label)` returns curated gene-disease evidence classifications. ClinGen classifications from strongest to weakest: Definitive → Strong → Moderate → Limited → Disputed → Refuted.

**Critical reasoning step**: If the gene-disease relationship is Disputed or Refuted, any pathogenic ClinVar variant in this gene must be interpreted with extreme caution — the clinical relevance is uncertain independent of variant-level evidence. Always report ClinGen classification before interpreting variant pathogenicity.

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
(gnomAD global AF, max population AF, homozygote count)

## 5. Deleteriousness Score [T3]
(CADD PHRED, REVEL, AlphaMissense — note concordance or discordance)

## 6. Clinical Classification [T1-T2]
(ClinVar significance, review stars, submitter count)

## 7. Gene-Disease Validity [T1]
(ClinGen classification for relevant disease)

## 8. Integrated Assessment
(Reasoning across all four dimensions: conservation, location, frequency, prediction)

## Data Gaps
(Any phase with no data; confidence caveats)
```

---

## Fallback Chains

- `ProtVar_map_variant` fails → try with genomic notation or `protein_variant` format
- `gnomad_get_variant` fails → use `gnomad_search_variants` by gene, or OpenCRAVAT `gnomad3` annotator
- `CADD_get_variant_score` unavailable → use OpenCRAVAT `cadd_exome` annotator
- `ClinVar_search_variants` returns empty → use OpenCRAVAT `clinvar` annotator
- `ClinGen_search_gene_validity` returns no data → note gene-disease relationship not curated by ClinGen

---

## Limitations

- **ProtVar**: Covers UniProt canonical isoforms only; alternative isoforms not mapped
- **gnomAD**: Based on gnomAD v4 (exomes + genomes); mitochondrial variants have separate AF
- **CADD**: Computational prediction only [T3]; does not replace experimental evidence
- **ClinVar**: Reflects submitter interpretations; star rating reflects concordance not accuracy
- **ProtVar structural coordinates**: Derived from AlphaFold2 where no experimental structure exists
