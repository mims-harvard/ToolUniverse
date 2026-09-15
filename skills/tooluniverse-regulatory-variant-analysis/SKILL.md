---
name: tooluniverse-regulatory-variant-analysis
description: Non-coding/regulatory variant interpretation — GWAS association lookup, eQTL evidence (GTEx), chromatin state (ENCODE), regulatory variant scoring (RegulomeDB, CADD), TF-binding disruption, and sequence-based deep-learning prediction (AlphaGenome/AlphaGenome Atlas) for when annotation databases are silent. Use for non-coding GWAS hit interpretation, eQTL-based gene assignment, and regulatory mechanism reasoning. Distinct from coding-variant tools.
disable-model-invocation: true
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Regulatory Variant Analysis Skill

Systematic regulatory variant interpretation: discover trait associations from GWAS, map eQTL effects, annotate chromatin context, assess regulatory element overlap, predict direct sequence-level effects with AlphaGenome/AlphaGenome Atlas, and produce evidence-graded functional impact predictions for non-coding variants.

## When to Use

- "What GWAS associations exist for rs12913832?"
- "Find eQTLs for the APOE locus in brain tissue"
- "What regulatory elements overlap this variant region?"
- "Which SNPs are associated with type 2 diabetes from GWAS?"
- "Is this intronic variant in an active enhancer?"
- "What is the RegulomeDB score for rs429358?"
- "Find ENCODE histone marks at the BRCA1 promoter region"
- "Map trait ontology terms for 'blood pressure' to EFO IDs"
- "This variant has no GWAS/eQTL/ENCODE hits at all — does a sequence model predict any effect?"
- "Scan this candidate regulatory region to find which single base change matters most"

**NOT for** (use other skills instead):
- Coding variant pathogenicity -> Use `tooluniverse-variant-interpretation`
- Full clinical variant classification (ACMG) -> Use `tooluniverse-variant-interpretation`
- Gene-disease associations (not variant-specific) -> Use `tooluniverse-gene-disease-association`
- Pharmacogenomic variant annotation -> Use `tooluniverse-pharmacogenomics`
- Epigenomics data processing (BED/narrowPeak files) -> Use `tooluniverse-epigenomics`

---

## Non-Coding Variant Impact Reasoning

When evaluating a non-coding variant, build evidence across five questions. The first four are annotation-based (what's already known to be at this position, in this population); the fifth is model-based (what the sequence itself predicts, whether or not anything is annotated there yet) — they answer different questions and should corroborate, not substitute for, each other.

**1. Is the variant in a regulatory element?**
Use RegulomeDB to assess whether the variant overlaps TF binding sites, chromatin accessibility peaks, or known regulatory annotations. A low RegulomeDB score (categories 1a-2a) indicates strong evidence that the position is functionally active. Confirm with ENCODE histone marks: H3K27ac signals active enhancers and active promoters; H3K4me1 alone marks poised enhancers; H3K4me3 marks active promoters; H3K27me3 marks silenced regions.

**2. Does it alter a transcription factor binding site?**
Check RegulomeDB's TF binding evidence and ENCODE TF ChIP-seq experiments. A variant that falls within a TF footprint and disrupts the consensus motif is mechanistically actionable, especially if the TF is known to be relevant in the disease tissue.

**3. Is there eQTL evidence linking it to a gene?**
Query GTEx to determine whether the variant (or variants in tight LD) modulates expression of a nearby gene in a tissue-specific or ubiquitous manner. A tissue-specific eQTL suggests cell-type-specific regulation; a ubiquitous eQTL suggests a core regulatory element. The direction of the NES (positive = alternative allele increases expression, negative = decreases) and effect size matter for interpretation.

**4. Is there GWAS evidence for trait association?**
Search the GWAS Catalog for the rsID or the surrounding locus. Genome-wide significant associations (p < 5×10⁻⁸) in relevant traits anchor the variant's biological importance. Cross-reference with OpenTargets for locus-to-gene mapping from multiple GWAS studies.

**5. What does a sequence-based model predict directly?**
Run `AlphaGenome_atlas_lookup_variant` for a near-instant AVI_SCORE (a unified AlphaGenome + AlphaMissense impact estimate; precomputed, so it costs nothing to check on every candidate SNV up front, even before the annotation phases below). A high AVI_SCORE with no other evidence is exactly the "variant with no obvious job" case — it means the annotation databases haven't caught up, not that the variant is inert. When the AVI_SCORE is high, or the position is an indel/synthetic sequence Atlas can't cover, escalate to the live model: `AlphaGenome_score_variant` for a per-track effect breakdown, or `AlphaGenome_score_ism_variants` to scan the surrounding window and identify which exact base change (and which biological readout — expression, splicing, chromatin) drives the effect. This is the only one of the five questions that gives a *mechanistic* answer (e.g., "this substitution creates a transcription-factor binding motif that wasn't there before") rather than a correlational one.

**Synthesizing the evidence**: Build a multi-layer case. A variant with GWAS significance + eQTL evidence + RegulomeDB score 1a-2a + active chromatin (H3K27ac) in the relevant tissue represents high-confidence regulatory impact — and a concordant AVI_SCORE or ISM result strengthens that case further, since it comes from an independent, causal-mechanism source rather than more correlational annotation. Two or three converging lines of evidence (e.g., eQTL plus active enhancer) constitute moderate confidence. A single line, or a variant only in a poised but not active regulatory context, represents lower confidence — but see the AlphaGenome-only case below before calling it "no evidence."

---

## Workflow Overview

```
Input (rsID, genomic coordinates, trait/disease, gene)
  |
  v
Phase 0: Variant/Trait Resolution
  Resolve rsIDs, map trait names to EFO/MONDO IDs via OLS
  |
  v
Phase 0.5: Sequence-Based Triage (AlphaGenome Atlas)
  Instant AVI_SCORE per candidate SNV -- cheap, run before the annotation phases
  |
  v
Phase 1: GWAS Association Lookup
  GWAS Catalog associations, p-values, effect sizes, study metadata
  |
  v
Phase 2: eQTL Analysis
  GTEx tissue-specific eQTLs, target gene identification
  |
  v
Phase 3: Regulatory Element Annotation
  ENCODE histone marks, RegulomeDB scores, chromatin state
  |
  v
Phase 4: OpenTargets GWAS Integration
  OpenTargets GWAS study aggregation, locus-to-gene mapping
  |
  v
Phase 4.5: Sequence-Based Deep-Dive (if Phases 1-4 are silent, or the Phase 0.5
  AVI_SCORE was high and needs a mechanism) -- live AlphaGenome scan
  |
  v
Phase 5: Functional Impact Synthesis
  Integrate all evidence, assign regulatory impact level
  |
  v
Phase 6: Report
  Evidence-graded regulatory variant report
```

---

## Phase 0: Variant/Trait Resolution

Use `ols_search_terms` to resolve trait names to ontology IDs before GWAS queries. Restrict to `ontology="efo"` for GWAS traits; OpenTargets prefers MONDO IDs (e.g., MONDO_0005148 for type 2 diabetes rather than EFO_0001360). Use `EnsemblVEP_annotate_rsid` (param is `variant_id`, not `rsid`) for initial consequence annotation and nearest gene identification.

---

## Phase 0.5: Sequence-Based Triage (AlphaGenome Atlas)

Once you have genomic coordinates for the variant (chromosome, position, reference/alternate bases), run `AlphaGenome_atlas_lookup_variant` before spending calls on the annotation phases below. It's a precomputed database read covering essentially all possible human SNVs, so it's worth running as a default first step rather than a last resort: it returns `AVI_SCORE`, a single number fusing AlphaGenome's regulatory prediction with AlphaMissense's coding-impact model, comparable across coding and non-coding variants alike.

Treat the result as a prior, not a verdict: a high AVI_SCORE with weak annotation evidence means "look harder here, the databases haven't caught up" (see Phase 4.5); a low AVI_SCORE alongside strong GWAS/eQTL evidence is worth a second look at whether the causal variant is actually a different one in LD. Atlas only covers single-nucleotide substitutions — for an indel, skip straight to `AlphaGenome_score_variant` (live model) instead.

---

## Phase 1: GWAS Association Lookup

`gwas_search_associations` is the primary tool: accepts `disease_trait` (free text), `efo_id` (preferred for precision), `rs_id`, and `p_value` threshold. Use `p_value=5e-8` for genome-wide significance. For locus-level discovery, `gwas_get_variants_for_trait` retrieves all SNPs for a trait. `gwas_get_snps_for_gene` finds GWAS-cataloged SNPs mapped to a specific gene.

**Reasoning tip**: When GWAS Catalog returns empty for a free-text trait, switch to the `efo_id` parameter — the catalog uses controlled vocabulary and free-text matching is imprecise.

---

## Phase 2: eQTL Analysis

`GTEx_query_eqtl` accepts a gene symbol (auto-resolved to GENCODE ID) or Ensembl gene ID. It returns tissue-specific SNP-gene associations with NES (normalized effect size) and p-value per tissue.

When interpreting results, ask: does the eQTL effect occur in the tissue most relevant to the disease? A brain-specific eQTL for a neurodegenerative disease variant is more compelling than a ubiquitous one. Use `GTEx_get_median_gene_expression` to confirm that the target gene is actually expressed in the relevant tissue before placing weight on eQTL evidence.

**Note**: GTEx API uses v8 data; gtex_v10 endpoints may return empty for some queries.

---

## Phase 3: Regulatory Element Annotation

`RegulomeDB_query_variant` (param: `rsid`) returns a regulatory score and feature annotations. Scores in categories 1a–2a indicate strong regulatory evidence (eQTL overlap + TF binding + chromatin accessibility). Scores 3a–6 represent progressively weaker evidence.

`ENCODE_search_histone_experiments` accepts `histone_mark` (e.g., "H3K27ac") and `biosample_term_name` (tissue or cell line name — NOT a disease name; ENCODE uses biological sample names like "liver" or "breast epithelium"). Use `assay_title="TF ChIP-seq"` (not just "ChIP-seq") when querying TF binding data.

**Reasoning tip**: RegulomeDB aggregates ENCODE, Roadmap, and other data. If ENCODE doesn't have the specific biosample, RegulomeDB may still have aggregate evidence from related cell types.

When you have the variant as a GRCh38 coordinate, `FAVOR_annotate_variant(variant="chr-pos-ref-alt")` returns a regulatory annotation block (plus conservation, frequency, and CADD) in one call — use it to quickly confirm whether the position falls in an annotated regulatory element before drilling into RegulomeDB/ENCODE.

---

## Phase 4: OpenTargets GWAS Integration

`OpenTargets_search_gwas_studies_by_disease` takes `diseaseIds` as an array of MONDO IDs. It provides locus-to-gene (L2G) scores from multiple GWAS studies, which go beyond simple proximity to incorporate colocalisation, eQTL, and chromatin data. Use `OpenTargets_multi_entity_search_by_query_string` or `OpenTargets_get_disease_id_description_by_name` to resolve disease names to MONDO/EFO IDs first.

---

## Phase 4.5: Sequence-Based Deep-Dive (conditional)

Run this phase when either condition holds: (a) Phases 1-4 came back empty or weak — the classic "no obvious job" variant — or (b) Phase 0.5's AVI_SCORE was high and the report needs an actual mechanism, not just a number.

- `AlphaGenome_score_variant`: the recommended per-track ref-vs-alt effect for the variant, when you already know which modality matters (expression, splicing, accessibility, a specific histone mark).
- `AlphaGenome_score_ism_variants`: scans every possible substitution across a short window (≤500 bp) around the variant and ranks them by effect. Use this when you don't yet know *which* base matters, only that something in the region does — e.g. confirming a variant sits inside a motif by checking whether neighboring positions show the same disruption pattern.
- `AlphaGenome_predict_interval`: full track profile across a wider window (up to 1 Mb) when you need the broader regulatory landscape, not just the single-variant delta.

A concordant result across two or three tracks (e.g., a histone mark for enhancer activity plus expression, both shifting the same direction) is stronger evidence than a single-track hit — the same logic Phase 5 already applies to annotation evidence.

---

## Phase 5: Functional Impact Synthesis

After collecting evidence, reason through the layers:

- **High impact**: GWAS genome-wide significant + eQTL with meaningful NES + RegulomeDB score ≤ 2 + active chromatin (H3K27ac) in relevant tissue. Multiple independent lines converge on the same locus and gene — a concordant AlphaGenome/AVI_SCORE result adds a mechanistic line on top of this, but isn't required for high confidence when the annotation evidence already converges.
- **Moderate impact**: Two to three lines of evidence (e.g., eQTL + active enhancer overlap, or GWAS significant + RegulomeDB ≤ 3) without full convergence.
- **Low impact**: Single line of evidence, or only computational annotation (VEP consequence category) without functional data.
- **Sequence-model-supported, annotation-silent**: No GWAS/eQTL/ENCODE/RegulomeDB evidence, but Phase 4.5 shows a high AVI_SCORE and/or a clear multi-track mechanism (e.g., a created transcription-factor motif, a disrupted splice junction). Treat this as its own tier, not as "no evidence" — it means the variant is plausibly functional but too novel or too rare for existing databases to have caught up, not that nothing is happening. State the confidence honestly: this is a strong hypothesis from an independent, well-validated model, not the multi-source convergence of the tiers above.
- **No evidence**: No regulatory annotations in any source, and Phase 4.5 (if run) shows a low AVI_SCORE / no strong sequence effect either. The variant may be in a non-functional region.

---

## Fallback Strategies

- **GWAS Catalog returns empty**: Switch from free-text `disease_trait` to `efo_id`; broaden the trait term.
- **GTEx eQTL empty for gene**: Verify gene symbol spelling; try Ensembl ID; increase `size` parameter.
- **RegulomeDB returns no data**: Query ENCODE directly, or run `FAVOR_annotate_variant` (GRCh38 coordinate) for its regulatory + conservation annotation; the variant may lack regulatory annotations in available data.
- **OpenTargets GWAS returns None**: Verify MONDO/EFO ID format; try `OpenTargets_multi_entity_search_by_query_string` first to confirm the correct ID.
- **ENCODE tissue not found**: ENCODE uses specific biosample names; RegulomeDB aggregates data from many cell types and may cover the gap.
- **All of Phases 1-4 return empty/weak**: Don't conclude "no evidence" yet — run Phase 4.5. AlphaGenome predicts directly from sequence and doesn't depend on the variant (or anything nearby) having been studied before, so it's the one evidence source that still works when the databases have nothing.
- **Variant is an indel, not a single-nucleotide substitution**: `AlphaGenome_atlas_lookup_variant`/`atlas_scan_interval` are SNV-only; use the live `AlphaGenome_score_variant` instead.

---

## Example Workflows

### GWAS Variant Functional Annotation (rs429358 / APOE)

```
Step 1: gwas_search_associations(rs_id="rs429358")
  -> All trait associations (Alzheimer's disease, LDL cholesterol, etc.)

Step 2: GTEx_query_eqtl(gene_symbol="APOE")
  -> Tissue-specific eQTL evidence; note effect in brain vs liver

Step 3: RegulomeDB_query_variant(rsid="rs429358")
  -> Regulatory score and TF binding annotations

Step 4: ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name="brain")
  -> Active enhancer context near the variant

Step 5: Synthesize: does GWAS significance + eQTL + active chromatin converge on one gene?
```

### Non-Coding Variant Assessment (Intronic/UTR Variant)

```
Step 1: EnsemblVEP_annotate_rsid(variant_id="rs12345678")
  -> Confirm non-coding consequence, identify nearest gene

Step 2: RegulomeDB_query_variant(rsid="rs12345678")
  -> Is this position in a regulatory context?

Step 3: gwas_search_associations(rs_id="rs12345678")
  -> Any GWAS associations in relevant traits?

Step 4: GTEx_query_eqtl(gene_symbol=nearest_gene)
  -> Does this variant or nearby variants modulate expression?

Step 5: ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name=relevant_tissue)
  -> Active chromatin confirmation

Step 6: Classify impact based on convergence of evidence lines
```

### Annotation-Silent Variant Resolved via Sequence Prediction

The pattern behind real cases like the GREGoR Consortium's use of AlphaGenome Atlas to solve an unsolved epilepsy case through a deep intronic *DNM1* variant: no exonic hit, no GWAS association, nothing for the annotation phases to find — until a sequence model is asked directly.

```
Step 1: AlphaGenome_atlas_lookup_variant(chromosome=..., position=..., reference_bases=..., alternate_bases=...)
  -> High AVI_SCORE despite the variant being deep intronic

Step 2: gwas_search_associations, GTEx_query_eqtl, RegulomeDB_query_variant, ENCODE_search_histone_experiments
  -> All empty or weak -- nothing here for standard annotation to catch

Step 3: AlphaGenome_score_ism_variants(chromosome=..., start=..., end=..., output_type="SPLICE_SITES")
  -> Scan the surrounding window; identify that this substitution creates a cryptic splice site

Step 4: Synthesize: high AVI_SCORE + a concrete, mechanistic splice-site prediction, despite zero
  annotation-database hits -> classify as "sequence-model-supported, annotation-silent", not
  "no evidence". Recommend experimental validation (e.g., a minigene splicing assay) rather than
  treating the model output as a final answer.
```

---

## Limitations

- GWAS Catalog covers published GWAS only; unpublished studies are not included.
- GTEx eQTL data is from v8; v10 endpoints may return empty.
- RegulomeDB annotations depend on available ENCODE/Roadmap data for the specific cell type.
- eQTL analysis identifies correlation, not causation; fine-mapping is needed to identify causal variants.
- RegulomeDB scores are heuristic; a score of 1a does not guarantee functional impact.
- GWAS associations are population-level; individual variant effects depend on genetic background.
- AlphaGenome/AVI_SCORE predictions are model estimates, not experimental measurements — they corroborate annotation evidence or generate a hypothesis worth validating, but a high score alone is not equivalent to a confirmed functional impact. `AlphaGenome_score_ism_variants` is capped at a 500 bp window and `atlas_scan_interval` at 10,000 bp per call — scope the region before calling either.
