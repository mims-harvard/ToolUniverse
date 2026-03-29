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

## LOOK UP, DON'T GUESS

When asked about a variant's significance, query ClinVar/gnomAD/CIViC FIRST. Never classify a variant without checking databases. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

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

Tools: `ClinVar_search_variants`, `gnomad_search_variants`, `gnomad_get_variant`, `OMIM_search`, `OMIM_get_entry`, `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_search_actionability`, `COSMIC_search_mutations`, `COSMIC_get_mutations_by_gene`, `DisGeNET_search_gene`, `DisGeNET_get_vda`, `SpliceAI_predict_splice`, `SpliceAI_get_max_delta`, `civic_get_variants_by_gene`, `civic_search_evidence_items`, `civic_search_assertions`

> **gnomAD two-step workflow**: `gnomad_search_variants` only accepts rsIDs or variant IDs (not gene names). Search by rsID first, then use the returned `variant_id` with `gnomad_get_variant` to get population allele frequencies.
>
> **CIViC**: Use `civic_search_genes(query="<gene_symbol>")` to find the CIViC gene ID dynamically (do NOT rely on a hardcoded lookup table). Then use `civic_get_variants_by_gene(gene_id=<id>)` and `civic_search_evidence_items` for actionability details. If `civic_search_genes` returns no results, the gene may not be curated in CIViC — note this gap.
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

**REVEL/AlphaMissense fallback**: If `MyVariant_query_variants` returns no `dbnsfp` block, use the dedicated tool:
1. **`MyVariant_get_pathogenicity_scores`** (PREFERRED FALLBACK) — returns REVEL, AlphaMissense, SIFT, PolyPhen2, MetaRNN, GERP, PhyloP, and more in a single call with pre-configured dbnsfp fields. Input: `variant_id` (rsID or HGVS genomic).
2. `CADD_get_variant_score` (PHRED 0-99) — works for most variants
3. `AlphaMissense_get_variant_score` (0-1, needs UniProt ID) — missense only
4. `EVE_get_variant_score` (0-1) — missense only
5. `EnsemblVEP_annotate_hgvs` (VEP with colocated variants) — includes SIFT/PolyPhen
6. If REVEL is still unavailable, note this as a limitation and rely on CADD + SIFT + PolyPhen consensus. REVEL absence does not prevent classification.

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

### Gene-Specific Population Frequency Thresholds

BS1 (allele frequency too high for disorder) requires gene-specific calibration, not a universal cutoff:
- **High-penetrance genes** (BRCA1, TP53): BS1 threshold ~0.0001
- **Moderate-penetrance genes** (PALB2, ATM, CHEK2): BS1 threshold ~0.001
- **Low-penetrance/common disease genes**: BS1 threshold higher, depends on disease prevalence
- **Formula**: BS1 threshold = (disease prevalence × max allelic contribution × max genetic contribution) / penetrance
- When in doubt, compare the variant's AF to the highest AF of any known pathogenic variant in the same gene — if it exceeds that, BS1 is likely applicable.

### Handling Conflicting Evidence: Functional vs Epidemiological

This is one of the most challenging scenarios in variant interpretation. When a biochemical assay shows damage but population/epidemiological data shows no disease association:

1. **Epidemiological data generally trumps in-vitro assays** for clinical classification. A variant found at ~0.1% frequency with no disease association in 40K+ cases is unlikely to be clinically significant, even if it reduces protein function in a tube.
2. **Apply PS3/BS3 carefully**: ClinGen's SVI recommends that PS3 (functional evidence for pathogenicity) requires the assay to be validated against known pathogenic AND known benign controls. A single biochemical study without such validation is PS3_Supporting at best.
3. **Hypomorphic variants**: Some variants genuinely reduce protein function (detectable in sensitive assays) but not enough to cause disease. This is biologically real and does not make them pathogenic.
4. **Document the conflict explicitly** in the report. State: "Biochemical assay X shows [result], but case-control study Y with N cases found no significant disease association. Per ACMG guidelines, the epidemiological evidence is weighted more heavily for clinical classification."

### Bayesian ACMG Point System (Tavtigian et al. 2018)

Modern clinical labs use a point-based system instead of the original rule-counting approach:

| Evidence Level | Pathogenic Points | Benign Points |
|---|---|---|
| Very Strong (PVS1) | +8 | -- |
| Strong (PS1-PS4) | +4 each | -4 each (BS1-BS4) |
| Moderate (PM1-PM6) | +2 each | -- |
| Supporting (PP1-PP5) | +1 each | -1 each (BP1-BP7) |
| Stand-alone (BA1) | -- | -8 |

**Classification by total points**:
- Pathogenic: >= 10 points
- Likely Pathogenic: 6-9 points
- VUS: -5 to 5 points
- Likely Benign: -6 to -9 points
- Benign: <= -10 points

This system handles conflicting evidence naturally — a variant with PS3 (+4) and BS1 (-4) and BP4 (-1) nets -1, which is VUS. The original rule-based approach struggles with this scenario.

**Computational procedure: ACMG Bayesian classification**

```python
# Automated ACMG point calculation
# Input: dict of evidence codes with their applied strength

def classify_acmg(evidence: dict) -> dict:
    """
    Classify a variant using the Bayesian ACMG point system.

    Args:
        evidence: dict mapping ACMG codes to strength levels.
            Pathogenic codes: 'very_strong', 'strong', 'moderate', 'supporting'
            Benign codes: 'stand_alone', 'strong', 'supporting'

    Example:
        evidence = {
            'BS1': 'strong',       # AF too high
            'BS3': 'supporting',   # Epidemiological evidence against pathogenicity
            'BP6': 'supporting',   # ClinVar benign consensus
            'PP3': 'supporting',   # Computational predictors say damaging
        }
    """
    pathogenic_points = {
        'very_strong': 8, 'strong': 4, 'moderate': 2, 'supporting': 1
    }
    benign_points = {
        'stand_alone': -8, 'strong': -4, 'supporting': -1
    }

    total = 0
    details = []
    for code, strength in evidence.items():
        if code.startswith(('PVS', 'PS', 'PM', 'PP')):
            pts = pathogenic_points.get(strength, 0)
        elif code.startswith(('BA', 'BS', 'BP')):
            pts = benign_points.get(strength, 0)
        else:
            pts = 0
        total += pts
        details.append(f"{code} ({strength}): {pts:+d}")

    if total >= 10:
        classification = "Pathogenic"
    elif 6 <= total <= 9:
        classification = "Likely Pathogenic"
    elif -5 <= total <= 5:
        classification = "VUS"
    elif -9 <= total <= -6:
        classification = "Likely Benign"
    else:
        classification = "Benign"

    return {
        'classification': classification,
        'total_points': total,
        'evidence_breakdown': details
    }

# Example: PALB2 c.2816T>G (from test case)
result = classify_acmg({
    'BS1': 'strong',       # gnomAD AF 0.00105 exceeds threshold
    'BS3': 'supporting',   # Case-control study shows no association
    'BP6': 'supporting',   # ClinVar 13 submitters say benign/likely benign
})
# Output: Likely Benign, total_points=-6, evidence: BS1(strong):-4, BS3(supporting):-1, BP6(supporting):-1
```

Use this procedure after collecting all evidence from Phases 1-5 to compute the final classification.

### Gene-Specific VCEP Criteria

ClinGen Variant Curation Expert Panels (VCEPs) publish gene-specific ACMG modifications. Before classifying, check if a VCEP exists:
- `ClinGen_search_gene_validity(gene="<gene_symbol>")` — if validity is "Definitive" or "Strong", a VCEP likely exists
- Common VCEPs: BRCA1/2 (Enigma), TP53, PTEN, CDH1, PALB2, RASopathies, Lynch syndrome genes
- VCEP criteria override generic ACMG criteria (e.g., PALB2 VCEP has specific PM1 hotspot regions)

### Predictor Weighting

Not all computational predictors are equal. For missense variants:
- **REVEL** (AUC ~0.95) — best single meta-predictor; weight highest
- **AlphaMissense** (AUC ~0.94) — strong, structure-aware
- **CADD** (AUC ~0.85) — good for all variant types, but less specific for missense
- **SIFT/PolyPhen** (AUC ~0.80) — legacy tools; useful for consensus but not individually decisive

When predictors disagree: if REVEL says tolerated but SIFT/PolyPhen say damaging, lean toward REVEL. If REVEL is unavailable, require 3+ concordant predictions for PP3/BP4.

### Tool Failure Fallbacks

If a primary tool fails, use these alternatives:
- **ClinVar_search_variants returns 0 results**: Use `MyVariant_query_variants` with rsID or HGVS — the `clinvar` field in MyVariant is more reliable for variant lookup than NCBI Entrez search
- **gnomAD_search_variants fails**: Use `EnsemblVEP_annotate_hgvs` which includes gnomAD frequency via colocated variants
- **CADD_get_variant_score fails**: CADD PHRED is also available in the `dbnsfp` block from MyVariant
- **AlphaFold prediction unavailable** (large proteins >2700aa): Use `PDBe_get_uniprot_mappings` for experimental structures

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

## Cross-Skill References

For amino acid properties at variant position, run: `python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --code X`

---

## References

- `ACMG_CLASSIFICATION.md` - Evidence codes, classification algorithm, prediction thresholds, structural/regulatory impact tables
- `CODE_PATTERNS.md` - Reusable code patterns for each workflow phase
- `CHECKLIST.md` - Pre-delivery verification
- `EXAMPLES.md` - Sample interpretations
- `TOOLS_REFERENCE.md` - Tool parameters and fallbacks
