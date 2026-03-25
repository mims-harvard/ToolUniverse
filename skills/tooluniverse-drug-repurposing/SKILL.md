---
name: tooluniverse-drug-repurposing
description: Identify drug repurposing candidates using ToolUniverse for target-based, compound-based, and disease-driven strategies. Searches existing drugs for new therapeutic indications by analyzing targets, bioactivity, safety profiles, and literature evidence. Use when exploring drug repurposing opportunities, finding new indications for approved drugs, or when users mention drug repositioning, off-label uses, or therapeutic alternatives.
---

# Drug Repurposing with ToolUniverse

Systematically identify and evaluate drug repurposing candidates using multiple computational strategies.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

---

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
- `drugbank_get_drug_name_and_description_by_target_name` - Drugs by target
- `drugbank_get_drug_name_and_description_by_indication` - Drugs by indication
- `DGIdb_get_drug_gene_interactions` - Drug-gene interactions
- `ChEMBL_search_drugs` / `ChEMBL_get_drug_mechanisms` - Drug search and MOA

**Drug Information**:
- `drugbank_get_drug_basic_info_by_drug_name_or_id` - Basic info
- `drugbank_get_indications_by_drug_name_or_drugbank_id` - Approved indications
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Pharmacology
- `drugbank_get_targets_by_drug_name_or_drugbank_id` - Drug targets

**Safety**:
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA warnings
- `FAERS_search_reports_by_drug_and_reaction` - Adverse events
- `FAERS_count_death_related_by_drug` - Serious outcomes
- `drugbank_get_drug_interactions_by_drug_name_or_id` - Interactions

**Property Prediction**:
- `ADMETAI_predict_physicochemical_properties` / `ADMETAI_predict_toxicity` - ADMET and toxicity

**Pathway & Network Analysis**:
- `ReactomeAnalysis_pathway_enrichment` - Pathway enrichment for target gene sets
- `STRING_get_network` - Protein interaction networks for target validation
- `CTD_get_gene_diseases` - Curated gene-disease associations

**Literature & Clinical Trials**:
- `PubMed_search_articles` / `EuropePMC_search_articles` - Literature search
- `search_clinical_trials` - ClinicalTrials.gov search. Use `condition` for disease name. The `intervention` filter is strict and may miss trials — use `query_term` for broader drug-name matching as fallback.

> **CNS diseases note**: For neurological indications (ALS, Alzheimer's, Parkinson's), prioritize BBB-penetrant candidates. Use ChEMBL molecular properties (MW < 500, PSA < 90) as BBB proxy since `ADMETAI_predict_BBB_penetrance` may require the `tooluniverse[ml]` extra. Consider route of administration (oral preferred for patients with swallowing difficulty) and sex-specific effects from preclinical models.

---

## Scoring Criteria

| Category | Points | Breakdown |
|----------|--------|-----------|
| **Target Association** | 0-40 | Strong genetic: 40, Moderate: 25, Pathway-level: 15, Weak: 5 |
| **Safety Profile** | 0-30 | FDA approved: 20, Phase III: 15, Phase II: 10, No black box: +10 |
| **Literature Evidence** | 0-20 | Clinical trials: 5 each (max 15), Preclinical: 1 each (max 10) |
| **Drug Properties** | 0-10 | High bioavailability: 5, BBB penetration (CNS): 5, Low toxicity: 5 |

---

## Best Practices

1. **Start broad**: Query multiple databases (DrugBank, ChEMBL, DGIdb)
2. **Validate targets**: Confirm target-disease associations in OpenTargets
3. **Safety first**: Prioritize approved drugs with known safety profiles
4. **Literature mining**: Search for existing clinical/preclinical evidence
5. **Consider mechanism**: Evaluate biological plausibility
6. **Batch operations**: Use `tu.run_batch()` for parallel queries

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
