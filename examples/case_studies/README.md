# Three research questions, answered end to end

Each script takes a research question, chains tools across databases,
structures, screens and predictive models to answer it, and prints the evidence
as it arrives. This is the same sequence the AI scientist ran in
[the write-up](https://aiscientist.tools/posts/tooluniverse-case-studies).

Every case has the same shape:

```
input                    process                              output
─────────────────────    ──────────────────────────────────   ──────────────────
a question + an          N steps, each one or more tool       a verdict, with
identifier or a file     calls, each step's result feeding    every number
                         the next                             traceable to a call
```

| | Input | Process | Output |
|---|---|---|---|
| **[1](case1_blm_target_assessment.py)** | gene `BLM` | 7 steps, 15 tools | is it a target, and is ML216 developable? |
| **[2](case2_oxtr_druggability.py)** | gene `OXTR` | 6 steps, 15 tools | is the chemistry right for the autism hypothesis? |
| **[3](case3_bcg_ae_severity.py)** | 2 trial tables (CSV) | 3 steps, 1 tool in 3 modes | does BCG associate with worse adverse events? |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate    # or: uv venv .venv
pip install 'tooluniverse[ml]'                       # ml extra = ADMET-AI models

git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse/examples/case_studies
pip install -r requirements.txt
```

No API keys. Every database used — Open Targets, ClinVar, GeneBe, AlphaFold,
PDBe, Europe PMC, PubChem, ChEMBL — is open, and ADMET-AI runs locally.

```bash
python case1_blm_target_assessment.py     # ~2 min, mostly ADMET-AI model load
python case2_oxtr_druggability.py         # ~2 min

python download_bcg_data.py               # ~4 MB of trial tables from Zenodo, CC0
python case3_bcg_ae_severity.py           # seconds
```

---

## Case 1 — is *BLM* a target?

### Input

```
gene:     BLM          (a DNA-repair helicase; losing it causes cancer)
question: can blocking it nevertheless treat cancer,
          and is its inhibitor ML216 developable?
```

### Process

| Step | Tools | What it establishes |
|---|---|---|
| 1 Resolve the gene | `OpenTargets_multi_entity_search_by_query_string` `OpenTargets_get_target_gene_ontology_by_ensemblID` | it is a genome-maintenance helicase |
| 2 Cancer-risk genetics | `OpenTargets_get_diseases_phenotypes_by_target_ensembl` | 464 disease associations, led by Bloom syndrome |
| 3 Classify a variant | `ClinVar_search_variants` `GeneBe_classify_variant` | `c.520C>T` is pathogenic — evidence **against** inhibiting |
| **4 Dependency screen** | `OpenTargets_get_target_depmap_essentiality` | **the turn**: not pan-essential, but concentrated in specific tumours |
| 5 Structure | `alphafold_get_summary` `PDBe_get_uniprot_structure_coverage` | use experimental structures, not the mixed-confidence prediction |
| 6 Precedent | `EuropePMC_search_articles` | paralog WRN is already a validated synthetic-lethal target |
| 7 Triage the chemistry | `OpenTargets_get_chemical_probes_by_target_ensemblID` `PubChem_*` `ADMETAI_*` `ChEMBL_search_similar_molecules` | ML216 is drug-like but carries a liability |

Step 4 is why the case exists — it contradicts step 3:

```
  mean gene effect: -0.18
  lines dependent at < -0.5: 94/1258 (7.5%)
  Most-dependent cancer types (mean gene effect, n>=5 lines):
    Mature T and NK Neoplasms          -0.47  (n=8)
    Cutaneous Squamous Cell Carcinoma  -0.44  (n=5)
```

### Output

Not a target — a **biomarker-defined hypothesis**. The germline genetics say
protect *BLM*; the screen says it is a selective vulnerability in defined
contexts. Both are right, so the workflow returns the contexts worth testing
rather than a yes/no. ML216 is a probe, not a lead: its predicted liver-injury
signal stays near maximum across every close analog, implicating the scaffold
rather than the molecule.

---

## Case 2 — does *OXTR* chemistry fit the hypothesis?

### Input

```
gene:     OXTR         (oxytocin receptor, a GPCR)
question: is it druggable, and does its pharmacology offer a
          starting point for the emerging autism association?
```

### Process

| Step | Tools | What it establishes |
|---|---|---|
| 1 Resolve + structure | `OpenTargets_multi_entity_search_by_query_string` `OpenTargets_get_target_gene_ontology_by_ensemblID` `alphafold_get_summary` `PDBe_get_uniprot_structure_coverage` | active and inactive experimental structures both exist |
| 2 Disease landscape | `OpenTargets_get_diseases_phenotypes_by_target_ensembl` | reproductive indications, plus an emerging autism link |
| 3 Tractability + drugs | `OpenTargets_get_target_tractability_by_ensemblID` `OpenTargets_get_associated_drugs_by_target_ensemblID` | druggable GPCR, 9 known agents, approved ones are peptides |
| 4 Mechanism | `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | already drugged in both directions |
| 5 Measured affinity | `ChEMBL_search_targets` `ChEMBL_get_target_activities` | nanomolar ligands exist |
| **6 CNS + mechanism** | `EuropePMC_search_articles` `PubChem_*` `ADMETAI_predict_BBB_penetrance` `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | **the turn**: the brain-penetrant candidate acts the wrong way |

Nolasiban passes every property filter — then fails the one that matters:

```
  nolasiban action type: ['ANTAGONIST']
  Read: brain-penetrant non-peptide OXTR chemistry is attainable,
  but this chemotype BLOCKS the receptor, and the pro-social
  hypothesis needs it ACTIVATED. Wrong direction.
```

### Output

Tractable target, wrong chemotype. The objective is stated precisely instead of
a repurposing suggestion: a brain-penetrant **agonist** or positive allosteric
modulator, selective over the vasopressin receptors. Screening on affinity and
brain penetrance alone would have produced a confident, wrong recommendation.

---

## Case 3 — did BCG worsen adverse events?

Unlike the others, this one computes on raw data rather than querying databases.

### Input

```
data:     TASK008_BCG-CORONA_DM.csv   demographics, 1000 subjects
          TASK008_BCG-CORONA_AE.csv   adverse events, 2694 records
          (public BCG-CORONA trial, Zenodo 12737228, CC0 — download_bcg_data.py fetches it)
question: is BCG associated with higher adverse-event severity,
          after adjusting for how often participants saw patients?
```

### Process

One tool, `clinical_trial_ae_severity_test`, in three modes:

| Step | Mode | What it does |
|---|---|---|
| 1 | `prepare` | inner-join AE onto DM by `USUBJID`, reduce each subject to their max `AESEV` → 791 evaluable subjects |
| 2 | `chi-square` | unadjusted treatment × severity association |
| 3 | `ordinal` | proportional-odds regression adjusting for `patients_seen`, `expect_interact`, `work_hours` |

### Output

```
  evaluable subjects: 791
  chi-square: 10.12   dof: 3   p-value: 0.018
  OR for higher severity with BCG: 1.53
  95% CI: (1.16, 2.01)
  p-value: 0.0024
```

A significant association that survives adjustment. Two things the script is
careful about, and you should be too:

- **Direction.** The tool reports the odds ratio against its own reference level
  (BCG=0, Placebo=1 alphabetically), so the raw **0.65** is Placebo-vs-BCG and
  the **1.53** above is its reciprocal. Reporting the raw number as the BCG
  effect would invert the finding.
- **What it supports.** The cohort is restricted to participants with at least
  one adverse event, and severity is a derived per-subject maximum. That makes
  this a reproducible association from a secondary analysis — not evidence that
  vaccination changes severity.

---

## Reading the output

Every value prints with the originally reported number beside it:

```
  DILI (liver injury): 0.988   (published: 0.99)
```

So a run tells you at a glance whether the science still holds against live
databases, and exactly which number moved if it doesn't. Values marked
`published:` come from the write-up or from the supplementary note it condenses
([arXiv:2509.23426](https://arxiv.org/abs/2509.23426)) — the note carries the
intermediate ones such as ACMG scores, PDB accessions and per-context DepMap
effects.

Expect some movement, and know which kind matters:

- **Live databases get re-scored.** *OXTR* disease associations were 393 at the
  time of writing and read 465 today; Open Targets re-scores every release. That
  is a release difference, not a failed reproduction, and no conclusion rests on
  the count.
- **Case 3 should never move.** Frozen dataset, deterministic model, identical
  on pandas 2 and 3. If its numbers change, something in your environment did.
- **ChEMBL's data API is currently down** (HTTP 500 upstream, [known
  issue](https://github.com/chembl/chembl_webresource_client/issues/144)). The
  two steps that need it — Case 1's analog comparison and Case 2's measured
  affinities — print `[unavailable]` and the case carries on rather than
  failing. Everything else is unaffected.
