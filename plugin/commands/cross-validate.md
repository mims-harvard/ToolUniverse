---
name: cross-validate
description: Take a specific scientific claim and confirm or refute it across 3+ independent databases, then report concordance. Use before publishing, citing, or acting on a fact when you want to know how strongly it's supported. Forces multi-source verification that the agent doesn't naturally enforce.
argument-hint: "[a specific testable claim, e.g. 'BRAF V600E is FDA-approved indication for vemurafenib in melanoma' or 'TP53 mutations occur in >50% of breast cancers']"
---

Cross-validate this claim against independent databases: $ARGUMENTS

A single source for a high-stakes fact is fragile. Force 3+ sources from
DIFFERENT databases (not 3 tools that all wrap the same upstream API).

## Process

### 1. Decompose the claim into testable assertions

A claim like "BRAF V600E is FDA-approved indication for vemurafenib in
melanoma" has three independent assertions:
- (a) BRAF V600E exists as an annotated cancer variant
- (b) Vemurafenib is FDA-approved
- (c) The approved indication includes BRAF-V600E-positive melanoma

Each assertion can be confirmed/refuted separately. Write them out before
calling tools — this is the anchor for what you'll verify.

For a numeric claim ("X% of breast cancers carry TP53 mutations"), the
assertion is the value itself; cross-validate by getting the same number
from independent cohorts.

### 2. Pick 3 independent databases per assertion

"Independent" means different upstream maintainers, not different tools
wrapping the same API. Examples:

| Domain | Independent sources |
|---|---|
| Drug approvals | OpenFDA, ChEMBL, DrugBank — each maintains its own approval table |
| Variant pathogenicity | ClinVar (NIH), CIViC (academic crowd-sourced), OncoKB (MSKCC), gnomAD frequency (Broad) |
| Gene-disease association | OpenTargets (composite), DisGeNET, OMIM, GenCC |
| Mutation frequency in cancer | TCGA (GDC), COSMIC, IntOGen — each samples different cohorts |
| Clinical trial existence | ClinicalTrials.gov, EU CTR, ChiCTR |
| Protein function | UniProt, Reactome, KEGG |
| Pharmacology | DrugBank, ChEMBL, PharmGKB, FDA Label |

Pick 3. If the claim's domain only has 2 truly-independent sources, note that
in the report — don't fabricate a third.

### 3. Run each source independently

Use `tu run <tool>` per source. Don't shortcut to a compound tool that aggregates
multiple sources — that defeats the cross-validation point. Track each source's
verdict separately:

```
Source 1 (ClinVar): CONFIRMS — V600E listed as Pathogenic, condition: Melanoma
Source 2 (CIViC):   CONFIRMS — V600E linked to vemurafenib sensitivity in melanoma
Source 3 (OncoKB):  CONFIRMS — V600 variant Level 1 evidence for vemurafenib in melanoma
```

If a source returns "no record found", that's not the same as "refutes" —
mark it as `INDETERMINATE` and note possible reasons (different namespace,
absent in that database, query string mismatch).

If a source explicitly contradicts (e.g., gnomAD shows population frequency
suggesting it's a benign polymorphism), that's `REFUTES`.

### 4. Report concordance

Format:

```
## Claim
<verbatim claim>

## Verdict: <CONFIRMED | DISPUTED | UNSUPPORTED>

## Per-source results
| Source | Verdict | Evidence | Date |
|---|---|---|---|
| ClinVar | CONFIRMS | V600E Pathogenic for Melanoma | 2025-Q4 |
| CIViC | CONFIRMS | V600E + vemurafenib (Level A) | 2026-01 |
| OncoKB | CONFIRMS | Level 1: vemurafenib in BRAF V600 melanoma | 2026-Q1 |

## Concordance: 3/3 confirm

## Caveats
- All three databases share clinical-trial sourcing (overlapping evidence)
- (Or:) Sources disagree on dosing — ClinVar lists 240mg BID; OpenFDA label lists 960mg BID
```

The verdict logic:
- All sources confirm and none refute → **CONFIRMED**
- Sources split (some confirm, some refute) → **DISPUTED** (state the split)
- All sources indeterminate or absent → **UNSUPPORTED** (no contradictory evidence either)
- Any source explicitly refutes a CONFIRMS-from-others case → **DISPUTED**, prioritize naming the dissenter

### 5. Note the limits

End with a "Caveats" section flagging:
- Whether the 3 sources are truly independent or share upstream data
- Whether any source is regional/legacy (e.g., FDA label is US-only)
- Whether the claim's TIME-SENSITIVITY matters (drug approvals change; cite the date)
- Whether numeric claims have a stated tolerance ("> 50%" vs "exactly 53.7%")

## Stop conditions

- Can't find 3 independent sources for the domain → use what you have, state
  you couldn't reach 3, note which sources DO exist.
- A source returns API key error → mark as `UNREACHABLE`, replace with one
  alternate. Don't retry.
- 4+ tool calls per assertion without result → stop, report "INDETERMINATE
  across N attempted sources".
