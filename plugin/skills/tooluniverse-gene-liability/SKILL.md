---
name: tooluniverse-gene-liability
description: Evaluate the human safety liability of knocking down, knocking out, degrading, or pharmacologically inhibiting a gene. Use for gene safety scoring, on-target toxicity assessment, essentiality and genetic-constraint review, critical-organ expression analysis, or deciding whether a target needs partial, transient, or tissue-specific modulation.
---

# Gene Liability Evaluation

Assess whether reducing a human gene's function is likely to be unsafe. Resolve the
gene, gather independent human and model-system evidence, calculate a transparent
0–100 liability score, and recommend an appropriate modulation strategy.

Higher scores mean greater predicted liability from the stated intervention. This is
a safety score, not a target-efficacy or druggability score.

## Required Input

Accept a gene symbol, name, Ensembl ID, or UniProt accession. Also capture:

- intervention modality: knockout, knockdown, degrader, irreversible inhibitor,
  reversible inhibitor, antibody, or unknown;
- intended tissue and indication, when supplied;
- desired inhibition depth and duration, when supplied.

If modality is absent, assess complete systemic loss of function and label that
assumption prominently. Do not silently generalize a knockout result to partial or
tissue-restricted pharmacology.

## Evidence Rules

- Look up the gene before reasoning. Do not score an ambiguous identifier.
- Use human causal evidence before animal models, screens, expression, or prediction.
- Treat absent data as unknown, never as evidence of safety.
- Cite every score-changing observation with the source and identifier.
- Separate germline loss of function, somatic loss, acute pharmacology, and chronic
  pharmacology.
- Treat DepMap as cancer-cell essentiality, not normal-tissue essentiality.
- Report contradictory evidence instead of averaging it away.

Grade evidence as:

- **T1**: human clinical outcome or replicated causal human genetics;
- **T2**: curated human evidence, mammalian knockout phenotype, or established drug
  class safety;
- **T3**: functional screen, tissue expression, or single experimental study;
- **T4**: computational prediction or catalog annotation.

## Workflow

### 1. Resolve the gene

Use `MyGene_query_genes` with `species="human"` and request symbol, name, Ensembl,
UniProt, and Entrez identifiers. Require an exact symbol or identifier match. If the
query maps to multiple loci, stop and ask for clarification.

Carry the approved symbol and Ensembl gene ID through every subsequent query.

### 2. Gather the five scoring dimensions

Run independent paths. A failed path must use its fallback or be marked unavailable.

| Dimension | Weight | Primary evidence | Fallback |
|---|---:|---|---|
| Human genetic constraint | 25 | `gnomad_get_gene_constraints(gene_symbol=...)` | ClinVar loss-of-function variants and literature |
| Mammalian knockout phenotype | 25 | `OpenTargets_get_biological_mouse_models_by_ensemblID(ensemblId=...)` | MGI-focused literature search |
| Critical-organ expression | 20 | `GTEx_get_median_gene_expression(operation="get_median_gene_expression", gencode_id=...)` | `HPA_get_comprehensive_gene_details_by_ensembl_id(..., include_expression=true)` |
| Observed on-target effects | 20 | `OpenTargets_get_target_safety_profile_by_ensemblID(ensemblId=...)` | `ClinVar_search_variants`, associated drugs, and literature |
| Cellular essentiality and redundancy | 10 | `DepMap_get_gene_dependencies(gene_symbol=...)` | pathway, paralog, and functional-screen literature |

Also query `OpenTargets_get_associated_drugs_by_target_ensemblID` to distinguish
observed target-class toxicity from hypothetical risk. Do not interpret the mere
existence of a drug as proof of safety.

For expression, inspect heart, central nervous system, liver, kidney, lung, immune or
marrow compartments, and reproductive tissues. Compare the gene across tissues;
do not compare raw TPM values between unrelated genes as if they shared one threshold.

### 3. Assign dimension points

Use only evidence actually retrieved.

#### Human genetic constraint — 0 to 25

- **25**: strong loss-of-function intolerance, such as pLI at least 0.9 together
  with LOEUF or observed/expected LoF at most 0.35;
- **15**: one strong constraint signal or intermediate LoF constraint;
- **5**: weak or conflicting constraint;
- **0**: credible tolerance to loss of function.

Use LOEUF when available; label observed/expected LoF as a proxy when LOEUF is absent.

#### Mammalian knockout phenotype — 0 to 25

- **25**: embryonic or perinatal lethality, or severe multisystem phenotype;
- **18**: reduced survival, organ failure, severe neurologic, immune, reproductive,
  or developmental phenotype;
- **8**: viable knockout with a consequential but organ-limited phenotype;
- **0**: replicated viable knockout without a consequential phenotype.

#### Critical-organ expression — 0 to 20

- **20**: broad high expression involving at least three critical organ systems;
- **12**: high expression in one or two critical organs or broad moderate expression;
- **6**: low-to-moderate critical-organ expression;
- **0**: credible restriction to the intended or noncritical tissue with negligible
  critical-organ expression.

#### Observed on-target effects — 0 to 20

- **20**: severe human disease from reduced function or consistent serious
  target-related toxicity;
- **12**: a credible human adverse phenotype or reproducible class effect;
- **5**: preclinical, isolated, or mechanistically plausible safety signal;
- **0**: human protective loss-of-function or well-tolerated target modulation with
  no serious on-target signal at relevant exposure.

Protective variants can reduce concern only when their direction, dosage, tissue,
and lifelong-versus-acute exposure are relevant to the proposed intervention.

#### Cellular essentiality and redundancy — 0 to 10

- **10**: broad common-essential signal with little credible redundancy;
- **5**: context-selective dependency or partial redundancy;
- **0**: reproducible non-essentiality or strong functional redundancy.

If DepMap returns only gene metadata without dependency scores, mark this dimension
unavailable. Never infer essentiality from a successful lookup alone.

### 4. Calculate score, coverage, and confidence

For available dimensions, calculate:

`liability score = 100 × points earned / available weight`

Report the available weight as evidence coverage. Do not assign zero points to a
missing dimension.

- **0–24**: low liability;
- **25–49**: moderate liability;
- **50–74**: high liability;
- **75–100**: very high liability.

Publish a categorical score only when coverage is at least 60%. Below 60%, report
“insufficient evidence” and list the experiments or datasets needed.

Assign confidence independently:

- **High**: at least 90% coverage with both T1 and independent T2 evidence;
- **Moderate**: at least 70% coverage with T1 or T2 evidence;
- **Low**: 60–69% coverage or evidence dominated by T3/T4;
- **Insufficient**: below 60% coverage.

### 5. Translate liability into a strategy

Do not stop at a risk label. Explain whether the evidence favors:

- partial rather than complete inhibition;
- reversible or transient rather than irreversible modulation;
- tissue-targeted delivery;
- isoform- or domain-selective modulation;
- biomarker-based exclusion or monitoring;
- deprioritization until a specific safety experiment closes the key gap.

## Required Output

Return these sections:

1. **Resolved gene and intervention assumption** — identifiers, modality, tissue,
   inhibition depth, and duration.
2. **Liability verdict** — score, band, evidence coverage, and confidence.
3. **Dimension table** — evidence, points, maximum weight, tier, citation, and
   conflicts for all five dimensions.
4. **Key red flags and protective evidence** — list both sides explicitly.
5. **Modulation recommendation** — full, partial, transient, tissue-specific, or
   no-go, with rationale.
6. **Data gaps and next experiments** — prioritize the missing evidence most likely
   to change the verdict.
7. **Sources** — database record links, study identifiers, and access dates.

End with: “This is a research risk assessment, not a clinical safety determination.”
