---
name: tooluniverse-adverse-outcome-pathway
description: >
  Map environmental/industrial chemicals to mechanistic adverse outcome pathways (AOPs) using
  AOPWiki, quantify toxicological hazard (PubChemTox GHS/carcinogen classification, LD50 values),
  and link chemical stressors to gene targets and disease endpoints via CTD for regulatory risk
  assessment. Use when asked about AOP stressor mapping, GHS hazard categories, LD50 data,
  IARC carcinogen classification, or mechanism-based risk assessment for non-drug chemicals.
---

# Adverse Outcome Pathway & Regulatory Risk Assessment

Distinct from drug safety (see tooluniverse-toxicology): this skill targets **environmental and
industrial chemicals** where the focus is AOP stressor mapping, GHS classification, LD50 hazard
quantification, and IARC carcinogen status — not FAERS signals or FDA drug labels.

## When to Use

Apply when researcher asks about:
- "What AOPs are associated with [pesticide/solvent/industrial chemical]?"
- "What is the GHS hazard classification for [compound]?"
- "What is the LD50 for [compound]?"
- "Is [compound] a carcinogen (IARC classification)?"
- "Which genes does [chemical] interact with (CTD)?"
- "Regulatory risk assessment for [environmental chemical]"
- "What diseases are associated with [chemical] exposure?"

Do NOT use for FDA-approved drugs with FAERS data — use `tooluniverse-toxicology` instead.

## Key Tools

| Tool | Purpose | Key Params |
|------|---------|-----------|
| `AOPWiki_list_aops` | Discover AOPs by keyword | `keyword` (organ, effect, or target name) |
| `AOPWiki_get_aop` | Full AOP details: MIE, key events, stressors | `aop_id` (int) |
| `PubChemTox_get_toxicity_summary` | Narrative toxicity overview | `cid` (PubChem CID) |
| `PubChemTox_get_ghs_classification` | GHS hazard category + pictograms | `cid` |
| `PubChemTox_get_carcinogen_classification` | IARC/NTP/EPA carcinogen status | `cid` |
| `PubChemTox_get_toxicity_values` | LD50/LC50 by route and species | `cid` |
| `PubChemTox_get_acute_effects` | Signs and symptoms of acute exposure | `cid` |
| `CTD_get_chemical_gene_interactions` | Chemical-gene molecular interactions | `input_terms` (name or MeSH ID) |
| `CTD_get_chemical_diseases` | Chemical-disease associations | `input_terms` |
| `PubChem_get_CID_by_compound_name` | Resolve compound name to PubChem CID | `name` |

## Workflow

### Phase 1: Compound Identity Resolution

Resolve chemical name to PubChem CID before all PubChemTox calls.

```
PubChem_get_CID_by_compound_name(name="benzo[a]pyrene")
-> cid: 9153 (use for all PubChemTox calls)
```

Note: CTD tools accept the chemical name directly (`input_terms` param) — no CID needed.

### Phase 2: AOP Discovery

Find relevant AOPs by searching organ targets and mechanism keywords.

```
AOPWiki_list_aops(keyword="lung")          # organ-level
AOPWiki_list_aops(keyword="DNA damage")    # mechanism-level
AOPWiki_list_aops(keyword="AhR")           # receptor-level
```

Select 2-4 candidate AOPs from results, then retrieve full details:

```
AOPWiki_get_aop(aop_id=58)  # returns MIE, key events, stressors, biological plausibility
```

Key fields in `AOPWiki_get_aop` response:
- `stressors`: list of chemicals that trigger this AOP (check if query compound is listed)
- `molecular_initiating_event`: the first molecular perturbation
- `key_events`: ordered chain of biological events
- `adverse_outcome`: apical regulatory endpoint

### Phase 3: Hazard Quantification (PubChemTox)

Run all four hazard queries in parallel using the resolved CID:

```
PubChemTox_get_ghs_classification(cid=9153)        # GHS category + pictogram
PubChemTox_get_carcinogen_classification(cid=9153)  # IARC Group 1/2A/2B/3
PubChemTox_get_toxicity_values(cid=9153)            # LD50 by route/species
PubChemTox_get_acute_effects(cid=9153)              # signs/symptoms
```

Note: `PubChemTox_get_target_organs` sometimes returns no data — treat as optional.

### Phase 4: Toxicogenomics (CTD)

Map chemical to gene targets and disease associations:

```
CTD_get_chemical_gene_interactions(input_terms="benzo[a]pyrene")
CTD_get_chemical_diseases(input_terms="benzo[a]pyrene")
```

Cross-reference CTD gene targets with AOP key event genes from Phase 2.

## Tool Parameter Reference

| Tool | Required | Optional | Notes |
|------|---------|---------|-------|
| `AOPWiki_list_aops` | `keyword` | — | Use organ ("liver"), effect ("apoptosis"), or receptor ("PPARalpha") |
| `AOPWiki_get_aop` | `aop_id` | — | Integer ID from list_aops output |
| `PubChemTox_get_toxicity_summary` | `cid` | — | PubChem CID integer |
| `PubChemTox_get_ghs_classification` | `cid` | — | Returns pictogram_labels e.g. "Health Hazard" |
| `PubChemTox_get_carcinogen_classification` | `cid` | — | IARC Group in `classifications[].classification` |
| `PubChemTox_get_toxicity_values` | `cid` | — | Values like "LD50 Rat oral 2400 mg/kg" |
| `PubChemTox_get_acute_effects` | `cid` | — | Sometimes sparse; not all compounds have data |
| `CTD_get_chemical_gene_interactions` | `input_terms` | — | Accepts name or MeSH ID (e.g., "D001564") |
| `CTD_get_chemical_diseases` | `input_terms` | — | Filter `DirectEvidence` = "marker/mechanism" for curated |
| `PubChem_get_CID_by_compound_name` | `name` | — | Returns CID + SMILES; required before PubChemTox calls |

## Common Patterns

```python
# Pattern: Confirm compound is a stressor in a specific AOP
aop = AOPWiki_get_aop(aop_id=58)
stressors = [s["name"] for s in aop["data"]["stressors"]]
# Check if query chemical appears in stressors list

# Pattern: Extract curated CTD disease associations only
diseases = CTD_get_chemical_diseases(input_terms="rotenone")
curated = [d for d in diseases["data"] if d.get("DirectEvidence")]

# Pattern: GHS carcinogen check
carcinogen = PubChemTox_get_carcinogen_classification(cid=9153)
iarc = [c for c in carcinogen["data"]["classifications"] if "IARC" in c.get("source", "")]
```

## Fallback Chains

| Primary | Fallback | When |
|---------|---------|------|
| `AOPWiki_list_aops` with specific keyword | Broader organ term | No results |
| `PubChemTox_get_target_organs` | `PubChemTox_get_toxicity_summary` | Returns empty |
| `CTD_get_chemical_diseases` | `CTD_get_gene_diseases` + gene from CTD interactions | Compound name not recognized |
