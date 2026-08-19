# Three research questions, answered end to end

Each script here takes a real research question and answers it the way the AI
scientist in [this write-up](https://aiscientist.tools/posts/tooluniverse-case-studies)
did: by choosing tools, chaining them across databases, structures, screens and
predictive models, and reasoning about what comes back.

You run one and watch the investigation unfold, step by step, with the evidence
printed as it arrives.

| | Question | Run |
|---|---|---|
| **1** | *BLM* loss causes cancer. Could blocking *BLM* still **treat** cancer? | [`case1_blm_target_assessment.py`](case1_blm_target_assessment.py) |
| **2** | *OXTR* is druggable. Does its chemistry actually fit the autism hypothesis? | [`case2_oxtr_druggability.py`](case2_oxtr_druggability.py) |
| **3** | Did BCG vaccination make adverse events more severe in a real trial? | [`case3_bcg_ae_severity.py`](case3_bcg_ae_severity.py) |

What makes these worth running is that in all three, the evidence disagrees with
itself. The interesting part is not retrieval — it is what the workflow does
when two valid results point opposite ways.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate    # or: uv venv .venv
pip install 'tooluniverse[ml]'                       # ml extra = ADMET-AI models

git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse/examples/case_studies
pip install -r requirements.txt
```

No API keys. Every database used here — Open Targets, ClinVar, GeneBe,
AlphaFold, PDBe, Europe PMC, PubChem, ChEMBL — is open, and ADMET-AI runs on
your machine.

```bash
python case1_blm_target_assessment.py     # ~2 min, mostly ADMET-AI model load
python case2_oxtr_druggability.py         # ~2 min

python download_bcg_data.py               # ~4 MB of trial tables from Zenodo, CC0
python case3_bcg_ae_severity.py           # seconds
```

## Case 1 — a tumour suppressor that might also be a target

*BLM* encodes a DNA-repair helicase. Losing it causes Bloom syndrome and raises
cancer risk across a broad spectrum, which is the textbook signature of a gene
you protect, not one you drug. The case asks whether the opposite can also be
true in specific tumours.

The first three steps build the case *against* inhibition: 464 disease
associations led by Bloom syndrome, and a patient variant that ClinVar and
GeneBe independently call pathogenic.

Step 4 is where it turns. The DepMap screen shows *BLM* is not broadly
essential — but the dependency is not evenly spread:

```
  mean gene effect: -0.18
  lines dependent at < -0.5: 94/1258 (7.5%)
  Most-dependent cancer types (mean gene effect, n>=5 lines):
    Mature T and NK Neoplasms          -0.47  (n=8)
    Cutaneous Squamous Cell Carcinoma  -0.44  (n=5)
```

So the genetics and the screen are both right and point opposite ways. The
workflow then looks for precedent, finds that *BLM*'s paralog WRN is already a
clinically validated synthetic-lethal target in exactly this kind of narrow
context, and lands on a biomarker-defined hypothesis rather than a target.

The last step triages the one available inhibitor, ML216, and finds a predicted
liver-injury signal that stays pinned near its maximum across every close
analog — a liability of the scaffold, not of one molecule.

## Case 2 — the compound that passes every filter and is still wrong

*OXTR* clears every druggability check the workflow applies: experimental
structures in both the active and inactive states, binding affinities into the
low nanomolar, nine known agents, and a receptor already drugged in both
directions.

Then it looks for something brain-penetrant, since the autism hypothesis needs
central exposure. Nolasiban fits: drug-like, high predicted blood-brain-barrier
penetrance. It looks like a repurposing candidate — until the mechanism check:

```
  nolasiban action type: ['ANTAGONIST']
  Read: brain-penetrant non-peptide OXTR chemistry is attainable,
  but this chemotype BLOCKS the receptor, and the pro-social
  hypothesis needs it ACTIVATED. Wrong direction.
```

A compound can satisfy every property filter you thought to apply and still act
in the opposite pharmacological direction. Checking affinity and BBB alone would
have produced a confident, wrong recommendation.

## Case 3 — statistics on a real trial, not a database lookup

The other two cases query databases. This one computes, on the raw tables of the
public [BCG-CORONA trial](https://zenodo.org/records/12737228) (CC0), using
`clinical_trial_ae_severity_test` in three modes: build the cohort, test the
unadjusted association, then fit an adjusted model.

It reaches a significant association between BCG and higher adverse-event
severity, holding after adjustment for how often participants saw patients:

```
  OR for higher severity with BCG: 1.53
  95% CI: (1.16, 2.01)
  p-value: 0.0024
```

Two things the script is careful about, and worth watching for:

- **Direction.** The tool reports the odds ratio against its own reference level
  (BCG=0, Placebo=1 alphabetically), so the raw **0.65** is Placebo-vs-BCG and
  the **1.53** above is its reciprocal. Reporting the raw number as the BCG
  effect would invert the finding.
- **What it supports.** The cohort is restricted to participants who had at
  least one adverse event, and severity is a derived per-subject maximum. That
  makes this a reproducible association from a secondary analysis, not evidence
  that vaccination changes severity.

## Reading the output

Every value the scripts print carries the number originally reported beside it:

```
  DILI (liver injury): 0.988   (published: 0.99)
```

So a run tells you at a glance whether the science still holds up against live
databases, and exactly which number moved if it doesn't. Values marked
`published:` come from the write-up or from the supplementary note it condenses
([arXiv:2509.23426](https://arxiv.org/abs/2509.23426)) — the note carries the
intermediate ones such as ACMG scores, PDB accessions and per-context DepMap
effects.

Expect some movement, and know which kind matters:

- **Live databases get re-scored.** *OXTR* disease associations were 393 at the
  time of writing and read 465 today; Open Targets re-scores every release. That
  is a release difference, not a failed reproduction, and no conclusion here
  rests on the count.
- **Case 3 should never move.** Frozen dataset, deterministic model, identical
  on pandas 2 and 3. If its numbers change, something in your environment did.
- **ChEMBL's data API is currently down** (HTTP 500 upstream, [known
  issue](https://github.com/chembl/chembl_webresource_client/issues/144)). The
  two steps that need it — Case 1's analog comparison and Case 2's measured
  affinities — report `[unavailable]` and the case carries on rather than
  failing. Everything else is unaffected.
