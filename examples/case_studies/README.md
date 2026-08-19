# Case studies: setup and reproduction

Runnable versions of the three case studies in
[Use Cases: Target Assessment, Druggability, and a Clinical Trial Reanalysis](https://aiscientist.tools/posts/tooluniverse-case-studies).

Each script makes the same tool calls, in the same order, that the AI scientist
made in the post, and prints the published value next to the one it just
retrieved, so a run tells you either "this still reproduces" or exactly which
number moved.

The post reports headline numbers; the supplementary note it condenses
("Step-by-step real-world case studies", in the ToolUniverse manuscript,
[arXiv:2509.23426](https://arxiv.org/abs/2509.23426)) reports the intermediate
ones. Both are annotated as `published:` here, so several values these scripts
check — ACMG scores, PDB accessions, per-context DepMap effects, PubChem CIDs —
are found in the supplementary note rather than in the post itself.

| Case | Question | Script |
|---|---|---|
| 1 | Is *BLM* a context-selective anticancer target, and is ML216 a developable lead? | [`case1_blm_target_assessment.py`](case1_blm_target_assessment.py) |
| 2 | Is *OXTR* druggable, and does its chemistry fit the autism hypothesis? | [`case2_oxtr_druggability.py`](case2_oxtr_druggability.py) |
| 3 | Is BCG vaccination associated with higher adverse-event severity? | [`case3_bcg_ae_severity.py`](case3_bcg_ae_severity.py) |

Cases 1 and 2 read live databases, so their numbers drift as those databases are
re-released. Case 3 runs on a frozen public dataset and reproduces exactly.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate    # or: uv venv .venv
pip install 'tooluniverse[ml]'                       # ml extra = ADMET-AI models

git clone https://github.com/mims-harvard/ToolUniverse.git
cd ToolUniverse/examples/case_studies
pip install -r requirements.txt
```

No API keys are needed. Every database used here (Open Targets, ClinVar, GeneBe,
AlphaFold, PDBe, Europe PMC, PubChem, ChEMBL) is open, and ADMET-AI runs
locally.

Two things worth knowing:

- Without the **`ml` extra**, the ADMET-AI steps in Cases 1 and 2 report
  `ADMETModel requires 'admet-ai' package`. The rest of both cases still runs.
- Case 3 calls `clinical_trial_ae_severity_test`, and that tool loads its
  implementation from the repository's `skills/` directory, resolved relative
  to the repo root. Outside a git clone it reports
  `Skill script not available`. The script therefore falls back to
  [`scripts/prepare_ae_cohort.py`](scripts/prepare_ae_cohort.py), bundled here,
  and prints which path it took. Both give identical results, on pandas 2 and
  pandas 3 alike:

  ```
  (running via: tool)             # git clone
  (running via: bundled script)   # pip install
  ```

## Running

```bash
cd examples/case_studies

python case1_blm_target_assessment.py     # ~2 min, mostly ADMET-AI model load
python case2_oxtr_druggability.py         # ~2 min

python download_bcg_data.py               # ~4 MB from Zenodo, CC0
python case3_bcg_ae_severity.py           # seconds
```

Cases 1 and 2 load 11 tool categories (146 tools) rather than the full ~2,700,
and Case 3 loads a single category, which keeps startup to a few seconds.

## What each case does

### Case 1 — *BLM* as a cancer risk gene and a possible target

Seven steps, ending in a conclusion neither half of the evidence supports on its
own. The germline genetics say *BLM* is a tumour suppressor to preserve; the
DepMap dependency screen says it is a selective vulnerability in a few defined
cancer contexts. The case holds both and concludes with a testable,
biomarker-defined hypothesis rather than a target.

Tools: `OpenTargets_multi_entity_search_by_query_string`,
`OpenTargets_get_target_gene_ontology_by_ensemblID`,
`OpenTargets_get_diseases_phenotypes_by_target_ensembl`,
`ClinVar_search_variants`, `GeneBe_classify_variant`,
`OpenTargets_get_target_depmap_essentiality`, `alphafold_get_summary`,
`PDBe_get_uniprot_structure_coverage`, `EuropePMC_search_articles`,
`OpenTargets_get_chemical_probes_by_target_ensemblID`,
`PubChem_get_CID_by_compound_name`, `PubChem_get_compound_properties_by_CID`,
`ADMETAI_predict_physicochemical_properties`, `ADMETAI_predict_toxicity`,
`ChEMBL_search_similar_molecules`.

### Case 2 — *OXTR* druggability and whether the chemistry fits

Six steps. The target passes every druggability check: experimental structures
in both the active and inactive states, nanomolar ligands, known agonists and
antagonists. The case turns on the last step, where nolasiban — drug-like and
predicted brain-penetrant, so a plausible repurposing candidate — turns out to
be an *antagonist*, the opposite of the mechanism a pro-social hypothesis needs.

Tools: `OpenTargets_multi_entity_search_by_query_string`,
`OpenTargets_get_target_gene_ontology_by_ensemblID`, `alphafold_get_summary`,
`PDBe_get_uniprot_structure_coverage`,
`OpenTargets_get_diseases_phenotypes_by_target_ensembl`,
`OpenTargets_get_target_tractability_by_ensemblID`,
`OpenTargets_get_associated_drugs_by_target_ensemblID`,
`OpenTargets_get_drug_mechanisms_of_action_by_chemblId`, `ChEMBL_search_targets`,
`ChEMBL_get_target_activities`, `EuropePMC_search_articles`,
`PubChem_get_CID_by_compound_name`, `PubChem_get_compound_properties_by_CID`,
`ADMETAI_predict_physicochemical_properties`, `ADMETAI_predict_BBB_penetrance`.

### Case 3 — BCG vaccination and adverse-event severity

One tool, `clinical_trial_ae_severity_test`, in three modes:

1. `prepare` — inner-join the adverse-event table onto demographics on
   `USUBJID`, reduce each subject to their maximum `AESEV` grade.
2. `chi-square` — unadjusted treatment-by-severity association.
3. `ordinal` — proportional-odds logistic regression adjusting for
   patient-interaction frequency (`patients_seen`, `expect_interact`,
   `work_hours`).

Data: [BCG-CORONA trial, Zenodo record 12737228](https://zenodo.org/records/12737228),
CC0-1.0. `download_bcg_data.py` fetches it.

One detail the script handles for you: the tool reports the odds ratio against
its own reference level. Treatment is encoded alphabetically (BCG=0,
Placebo=1), so the raw OR of **0.65** is Placebo vs BCG, and the published
**1.53** is its reciprocal. Reporting the raw number as though it were the
BCG effect would invert the finding.

## Expected output

Verified on 2026-08-17 against a fresh clone. Rows marked † are reported in the
supplementary note rather than in the post.

**Case 1** — every published value reproduced:

| Value | Published | Observed |
|---|---|---|
| *BLM* Ensembl gene | ENSG00000197299 | ENSG00000197299 |
| Disease associations | 464 | 464 |
| `c.520C>T` ACMG class | Pathogenic | Pathogenic |
| † ACMG score / transcript | 12 / NM_000057.4 | 12 / NM_000057.4 |
| DepMap cell lines | 1,258 | 1,258 |
| † Mean gene effect | −0.18 | −0.18 |
| † Lines dependent at < −0.5 | 94/1,258 (7.5%) | 94/1,258 (7.5%) |
| † Mature T/NK neoplasms | −0.47 (n=8) | −0.47 (n=8) |
| † Cutaneous SCC | −0.44 (n=5) | −0.44 (n=5) |
| † Peripheral nervous system | −0.33 (n=48) | −0.33 (n=48) |
| † AlphaFold model / length | AF-P54132-F1 / 1,417 | AF-P54132-F1 / 1,417 |
| † Helicase-core PDB entries | 7AUC, 4CGZ, 4O3M | all present |
| ML216 MW | 383 Da | 383.3 |
| † ML216 PubChem CID | 49852229 | 49852229 |
| QED / DILI / hERG / AMES | 0.66 / 0.99 / 0.56 / 0.16 | 0.657 / 0.988 / 0.564 / 0.160 |

**Case 2** — reproduced except the association count:

| Value | Published | Observed |
|---|---|---|
| *OXTR* Ensembl gene | ENSG00000180914 | ENSG00000180914 |
| Structures 7RYC / 6TPK | present | present |
| † Structure 7QVM, AF-P30559-F1, length 389 | present / 389 | present / 389 |
| Disease associations | 393 | **465** (drift, see below) |
| Known agents | 9 | 9 |
| oxytocin / atosiban mechanism | agonist / antagonist | AGONIST / ANTAGONIST |
| † nolasiban CID | 52947354 | 52947354 |
| nolasiban QED / BBB | 0.87 / 0.93 | 0.872 / 0.925 |
| nolasiban mechanism | antagonist | ANTAGONIST |

**Case 3** — exact:

| Value | Published | Observed |
|---|---|---|
| Evaluable subjects | 791 | 791 |
| † Severity distribution | {1:328, 2:402, 3:43, 4:18} | identical |
| Chi-square / dof / p | 10.12 / 3 / 0.018 | 10.12 / 3 / 0.018 |
| Adjusted OR (95% CI) | 1.53 (1.16–2.01) | 1.53 (1.16–2.01) |
| p | 0.0024 | 0.0024 |

## Why numbers drift, and which ones should not

- **Live database counts move.** *OXTR* disease associations were 393 when the
  post was written and are 465 now; Open Targets re-scores associations every
  release. The *BLM* count happens to be unchanged. Treat these as
  release-dependent, not as reproduction failures. The conclusions do not rest
  on them.
- **Stereochemistry changes ADMET-AI scores.** The scripts request PubChem's
  `SMILES` property (which carries stereochemistry) and fall back to
  `ConnectivitySMILES`. For nolasiban the flat form scores BBB 0.913 and the
  stereo form 0.925; the published 0.93 is the stereo form. ML216 has no
  stereocentre, so both agree.
- **Case 3 should never drift.** Frozen dataset, deterministic model, and
  identical output whether it runs through the tool or the bundled script, on
  pandas 2 or 3. If its numbers move, something in the environment changed.
- **ChEMBL's data API is down upstream.** Throughout verification
  `https://www.ebi.ac.uk/chembl/api/data/` failed on every request, in two
  modes: HTTP 500 after ~5 s, or no response at all. The fault is specific to
  that one service. Sampling five times each from the same machine:

  | Endpoint | Result |
  |---|---|
  | `/chembl/api/data/…` (ChEMBL data API) | 0/5 ok, avg 7.9 s, 500s and timeouts |
  | `/chembl/api/utils/…` (ChEMBL Beaker) | 5/5 ok, 0.4 s |
  | `/chembl/interface_api/…` (powers the ChEMBL website) | 5/5 ok, 0.5 s |
  | `/pdbe/api/…` | 5/5 ok, 0.4 s |
  | `/europepmc/webservices/…` | 5/5 ok, 0.5 s |

  Sibling services under the same prefix on the same host are healthy, so this
  is neither a network problem nor a ToolUniverse one: the base URL in
  `src/tooluniverse/chem_tool.py` is correct, the service behind it is not
  answering. It is a known upstream fault, reported in
  [chembl_webresource_client#144](https://github.com/chembl/chembl_webresource_client/issues/144)
  (open since 2026-06-23, no maintainer response). That report's workaround —
  appending any query parameter — no longer helps, so the service has degraded
  further since it was filed. Note the ChEMBL website stays up during this,
  because it runs on `interface_api` rather than the data API, so the outage is
  easy to miss.

  Consequently the two steps that depend on ChEMBL — Case 1's five-analog DILI
  comparison and Case 2's measured-affinity lookup — are the only ones **not**
  confirmed end-to-end against the live service. Their response parsing was
  written against the tool implementations in `src/tooluniverse/chem_tool.py`
  and checked on replayed payloads, but the published values (DILI 0.987-0.992;
  Ki as low as 3.2 nM) have not been re-observed. Both scripts report the step
  as unavailable and carry on rather than aborting. Check whether the service is
  back with:
  ```bash
  curl -o /dev/null -w '%{http_code}\n' https://www.ebi.ac.uk/chembl/api/data/status.json
  ```

## Source

The narrative and the step-by-step tool sequences come from the
[case-studies post](https://aiscientist.tools/posts/tooluniverse-case-studies),
which condenses the supplementary note "Step-by-step real-world case studies"
in the ToolUniverse manuscript,
[arXiv:2509.23426](https://arxiv.org/abs/2509.23426). Companion posts cover the
[LAB-Bench benchmark](https://aiscientist.tools/posts/labbench-benchmark) and the
[Tool Finder retrieval benchmark](https://aiscientist.tools/posts/tool-finder-benchmark).
