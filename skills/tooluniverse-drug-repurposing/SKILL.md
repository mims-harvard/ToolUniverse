---
name: tooluniverse-drug-repurposing
description: Identify drug repurposing candidates using ToolUniverse for target-based, compound-based, and disease-driven strategies. Searches existing drugs for new therapeutic indications by analyzing targets, bioactivity, safety profiles, and literature evidence. Use when exploring drug repurposing opportunities, finding new indications for approved drugs, or when users mention drug repositioning, off-label uses, or therapeutic alternatives.
---

# Drug Repurposing with ToolUniverse

Systematically identify and evaluate drug repurposing candidates using multiple computational strategies.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

---

## Reasoning Before Searching

Start by asking: WHY might this drug work for a new disease? Three strategies:

- **(a) Same target**: The drug's primary target is also involved in the new disease. This is the strongest hypothesis — use OpenTargets to check if the target has genetic evidence in both diseases before any other search.
- **(b) Off-target activity**: The drug has secondary targets or off-target effects that are relevant to the new disease. Check ChEMBL bioactivity data for all known targets of the drug, not just its primary one.
- **(c) Shared pathways**: The original indication and new disease share molecular pathways, even if the target itself is not genetically linked. Use Reactome and STRING to compare pathway overlap between diseases.

Each strategy uses different tools and has different evidentiary weight. Identify which strategy applies FIRST, then choose the corresponding workflow below. Do not run all three strategies blindly — reason about which is most plausible given the drug's mechanism.

**LOOK UP DON'T GUESS**: Never assume a drug hits a target, never assume a target is disease-relevant, never assume pathway overlap. Verify each link with tool calls.

## Core Strategies

1. **Target-Based**: Disease targets -> Find drugs that modulate those targets
2. **Compound-Based**: Approved drugs -> Find new disease indications
3. **Disease-Driven**: Disease -> Targets -> Match to existing drugs

---

## Workflow Overview

```
Phase 1: Disease & Target Analysis
  Get disease info (OpenTargets), find associated targets, get target details

Phase 2: Drug Discovery
  Search DrugBank, DGIdb, ChEMBL for drugs targeting disease-associated genes
  Get drug details, indications, pharmacology

Phase 3: Safety & Feasibility Assessment
  FDA warnings, FAERS adverse events, drug interactions, ADMET predictions

Phase 4: Literature Evidence
  PubMed, Europe PMC, clinical trials for existing evidence

Phase 5: Scoring & Ranking
  Composite score: target association + safety + literature + drug properties
```

See: PROCEDURES.md for detailed step-by-step procedures and code patterns.

---

## Quick Start

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Step 1: Get disease targets
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="rheumatoid arthritis")
# Response nests ID at data.search.hits[0].id
disease_id = disease_info['data']['search']['hits'][0]['id']
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id, limit=10)

# Step 2: Find drugs for each target
# Response nests targets at data.disease.associatedTargets.rows
rows = targets['data']['disease']['associatedTargets']['rows']
for target in rows[:5]:
    gene = target['target']['approvedSymbol']
    drugs = tu.tools.DGIdb_get_drug_gene_interactions(genes=[gene])
```

---

## Key ToolUniverse Tools

**Disease & Target**:
- `OpenTargets_get_disease_id_description_by_name` - Disease lookup
- `OpenTargets_get_associated_targets_by_disease_efoId` - Disease targets
- `UniProt_get_entry_by_accession` - Protein details

**Drug Discovery**:
- `drugbank_get_drug_name_and_description_by_target_name` - Drugs by target. **Param: `query=` (NOT `target_name=`)**
- `drugbank_get_drug_name_and_description_by_indication` - Drugs by indication. **Param: `query=` (NOT `indication=`)**
- `DGIdb_get_drug_gene_interactions` - Drug-gene interactions. Response path: `data.data.genes.nodes[0].interactions`
- `ChEMBL_search_drugs` / `ChEMBL_get_drug_mechanisms` - Drug search and MOA

**Drug Information** (ALL DrugBank tools use `query=` as the search parameter, plus `case_sensitive=False`, `exact_match=False`, `limit=N`):
- `drugbank_get_drug_basic_info_by_drug_name_or_id` - Basic info. **Param: `query="drug_name"`**
- `drugbank_get_indications_by_drug_name_or_drugbank_id` - Approved indications. **Param: `query="drug_name"`**
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Pharmacology. **Param: `query="drug_name"`**
- `drugbank_get_targets_by_drug_name_or_drugbank_id` - Drug targets. **Param: `query="drug_name"`**

**Safety**:
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA warnings
- `FAERS_search_reports_by_drug_and_reaction` - Adverse events. **Param: `medicinalproduct=` (NOT `drug_name=`)**
- `FAERS_count_death_related_by_drug` - Serious outcomes. **Param: `medicinalproduct=` (NOT `drug_name=`)**
- `drugbank_get_drug_interactions_by_drug_name_or_id` - Interactions

**Property Prediction**:
- `ADMETAI_predict_physicochemical_properties` / `ADMETAI_predict_toxicity` - ADMET and toxicity

**Pathway & Network Analysis**:
- `ReactomeAnalysis_pathway_enrichment` - Pathway enrichment. **Param: `identifiers="SOD1\nTARDBP\nFUS"` (newline-separated string, NOT array)**
- `STRING_get_network` - Protein interaction networks. **Param: `identifiers="SOD1\rTARDBP\rFUS"` (CR-separated string), `species=9606`**
- `CTD_get_gene_diseases` - Curated gene-disease associations. **Param: `input_terms="gene_symbol"` (NOT `gene_symbol=`)**

**Literature & Clinical Trials**:
- `PubMed_search_articles` / `EuropePMC_search_articles` - Literature search
- `search_clinical_trials` - ClinicalTrials.gov search. Use `condition` for disease name. The `intervention` filter is strict and may miss trials — use `query_term` for broader drug-name matching as fallback.

> **CNS diseases note**: For neurological indications (ALS, Alzheimer's, Parkinson's), prioritize BBB-penetrant candidates. Use ChEMBL molecular properties (MW < 500, PSA < 90) as BBB proxy since `ADMETAI_predict_BBB_penetrance` may require the `tooluniverse[ml]` extra. Consider route of administration (oral preferred for patients with swallowing difficulty) and sex-specific effects from preclinical models.

---

## Scoring & Decision Framework

### Repurposing Viability Score (0-100)

| Category | Points | How to Score |
|----------|--------|-----------|
| **Target Association** | 0-40 | **40**: Target has genetic evidence in disease (GWAS, rare variants); **25**: Target is in a disease-associated pathway (Reactome, KEGG); **15**: Target is differentially expressed in disease tissue; **5**: Target shares a GO term with disease genes |
| **Safety Profile** | 0-30 | **30**: FDA-approved drug, no black box warning, established safety record; **20**: FDA-approved with manageable warnings; **10**: Phase II+ data, acceptable safety; **0**: Preclinical only or serious safety signals |
| **Literature Evidence** | 0-20 | **20**: Phase II+ trial for the new indication exists; **15**: Case reports or retrospective studies show efficacy; **10**: Preclinical in-vivo evidence (animal models); **5**: In-vitro evidence only; **0**: No prior evidence |
| **Drug Properties** | 0-10 | **10**: Oral, good bioavailability, IP available; **5**: Injectable or narrow therapeutic window; **0**: Poor PK or formulation challenges |

**Classification**:
- **80-100**: Strong candidate — proceed to clinical evaluation
- **60-79**: Promising — worth preclinical validation or retrospective study
- **40-59**: Speculative — needs significant additional evidence
- **<40**: Weak — likely not worth pursuing without new mechanistic insight

### Evidence Grading for Repurposing

| Grade | Definition | Action |
|-------|-----------|--------|
| **E1 (Clinical)** | Existing clinical trial for new indication (any phase) | High priority — check trial results |
| **E2 (Epidemiological)** | Retrospective/observational data showing benefit | Moderate priority — design prospective study |
| **E3 (Preclinical)** | Animal model evidence for new indication | Standard priority — validate mechanism |
| **E4 (Computational)** | Target overlap, network proximity, or molecular similarity only | Low priority — needs experimental validation |

### How to Interpret and Combine Results

After running Phases 1-4, synthesize by answering:

1. **Is the target validated for this disease?** Check OpenTargets association score (>0.5 = strong). Cross-reference with genetic evidence (GWAS hits, rare variant studies). If target association is only pathway-level, the repurposing hypothesis is speculative.

2. **Does the drug actually hit the target at achievable doses?** Check ChEMBL IC50/Ki values. If the drug's affinity for the new target is >10x weaker than for its original target, clinical efficacy is unlikely at safe doses.

3. **What's the safety margin?** Compare the dose needed for the new indication to the approved dose. If higher doses are needed, safety data from the original indication may not apply.

4. **Is there prior clinical evidence?** A Phase II trial for the new indication (even failed) is more informative than 100 computational predictions. Check `search_clinical_trials` first.

5. **What's the competitive landscape?** If better drugs already exist for the disease, repurposing offers little value. Check DrugBank indications for approved therapies.

---

## Best Practices

1. **Check clinical trials FIRST**: `search_clinical_trials(condition="[disease]", intervention="[drug]")` — if a trial already exists, start there
2. **Validate targets with genetics**: Genetic evidence (GWAS, rare variants) is the strongest predictor of successful drug development
3. **Safety first**: Prioritize approved drugs with known safety profiles
4. **Dose matters**: A drug that hits a disease target at 100x its approved dose is not a repurposing candidate
5. **Mechanism over correlation**: Network proximity alone is insufficient — explain WHY the drug should work
6. **Consider IP and formulation**: Generic drugs are easier to repurpose but harder to fund trials for

### Computational Procedure: Drug-Target Dose Feasibility Check

A drug that hits a new target only at 100x its approved dose is NOT a viable repurposing candidate. Use this procedure after identifying drug-target pairs:

```python
# Drug-target dose feasibility analysis
# Uses ChEMBL bioactivity data from ToolUniverse
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

def check_dose_feasibility(drug_name, original_target, new_target):
    """
    Compare drug's potency at original vs new target.
    If new_target IC50 > 10x original_target IC50, flag as unlikely feasible.
    """
    # Get bioactivity for original target
    orig = tu.run_one_function({
        'name': 'ChEMBL_get_bioactivities',
        'arguments': {
            'molecule_chembl_id': drug_name,  # or search first
            'target_chembl_id': original_target,
            'limit': 10
        }
    })

    # Get bioactivity for new target
    new = tu.run_one_function({
        'name': 'ChEMBL_get_bioactivities',
        'arguments': {
            'molecule_chembl_id': drug_name,
            'target_chembl_id': new_target,
            'limit': 10
        }
    })

    # Extract IC50/Ki values and compare
    # If new target requires >10x concentration → NOT FEASIBLE at safe doses
    # If new target is within 3x → PROMISING
    # If new target is within 1x → STRONG candidate
    pass  # Parse actual values from results

# Alternative: Quick Cmax check
# If published Cmax at approved dose < IC50 for new target → NOT FEASIBLE
# Cmax data can be found in:
#   - DrugBank pharmacology section
#   - DailyMed clinical pharmacology section
#   - PubMed PK studies
```

**Key principle**: The most common reason repurposing fails is insufficient drug exposure at the new target. Always check whether the drug's concentration at approved doses reaches the IC50 for the new target.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Disease not found | Try synonyms or EFO ID lookup |
| No drugs for target | Check HUGO nomenclature, expand to pathway-level, try similar targets |
| Insufficient literature | Search drug class instead, check preclinical/animal studies |
| Safety data unavailable | Drug may not be US-approved, check EMA or clinical trial safety |

---

## Reference Files

- **REFERENCE.md** - Detailed reference documentation
- **EXAMPLES.md** - Sample repurposing analyses
- **PROCEDURES.md** - Step-by-step procedures with code
- **REPORT_TEMPLATE.md** - Output report template
- Related skills: disease-intelligence-gatherer, chemical-compound-retrieval, tooluniverse-sdk
