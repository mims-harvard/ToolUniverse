# Drug Repurposing: Strategies, Patterns, and Advanced Techniques

Complete code implementations for all repurposing strategies.

---

## Phase 1: Disease & Target Analysis

```python
# 1.1 Get disease information
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="[disease_name]")

# 1.2 Find associated targets
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_info['data']['id'], limit=20
)

# 1.3 Get target details
for target in targets['data'][:10]:
    details = tu.tools.UniProt_get_entry_by_accession(accession=target['uniprot_id'])
```

---

## Phase 2: Drug Discovery

```python
for target in targets['data'][:10]:
    drugbank_results = tu.tools.drugbank_get_drug_name_and_description_by_target_name(
        target_name=target['gene_symbol'])
    dgidb_results = tu.tools.DGIdb_get_drug_gene_interactions(gene_name=target['gene_symbol'])
    chembl_results = tu.tools.ChEMBL_search_drugs(query=target['gene_symbol'], limit=10)

# Get drug details
for drug_name in unique_drugs:
    drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(drug_name_or_drugbank_id=drug_name)
    indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(drug_name_or_drugbank_id=drug_name)
    pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(drug_name_or_drugbank_id=drug_name)
```

---

## Phase 3: Safety & Feasibility

```python
for drug in top_candidates:
    warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(drug_name=drug['name'])
    adverse_events = tu.tools.FAERS_search_reports_by_drug_and_reaction(drug_name=drug['name'], limit=100)
    interactions = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(drug_name_or_id=drug['name'])
    if 'smiles' in drug:
        admet = tu.tools.ADMETAI_predict_physicochemical_properties(smiles=drug['smiles'], use_cache=True)
```

---

## Phase 4: Literature Evidence

```python
for drug in top_candidates:
    query = f"{drug['name']} AND {disease_name}"
    pubmed_results = tu.tools.PubMed_search_articles(query=query, max_results=50)
    pmc_results = tu.tools.EuropePMC_search_articles(query=query, limit=50)
    trials = tu.tools.search_clinical_trials(condition=disease_name, intervention=drug['name'])
```

---

## Phase 5: Scoring

```python
def score_repurposing_candidate(drug, target_score, safety_data, literature_count):
    """Score drug repurposing candidate (0-100)."""
    score = 0
    score += min(target_score * 40, 40)  # Target association (0-40)
    if drug['approval_status'] == 'approved':
        score += 20
    elif drug['approval_status'] == 'clinical':
        score += 10
    if not safety_data.get('black_box_warning'):
        score += 10
    score += min(literature_count / 5 * 20, 20)  # Literature (0-20)
    if drug.get('bioavailability') == 'high':
        score += 10  # Drug properties (0-10)
    return score
```

---

## Alternative Strategy A: Mechanism-Based Repurposing

```python
known_drug = "metformin"
moa = tu.tools.drugbank_get_drug_desc_pharmacology_by_moa(mechanism_of_action="[moa_term]")
similar = tu.tools.ChEMBL_search_similar_molecules(query=known_drug, similarity_threshold=70)
```

---

## Alternative Strategy B: Network-Based Repurposing

```python
pathways = tu.tools.drugbank_get_pathways_reactions_by_drug_or_id(drug_name_or_drugbank_id="[drug_name]")
pathway_drugs = tu.tools.drugbank_get_drug_name_and_description_by_pathway_name(
    pathway_name=pathways['data'][0]['pathway_name'])
```

---

## Alternative Strategy C: Phenotype-Based Repurposing

```python
indication_drugs = tu.tools.drugbank_get_drug_name_and_description_by_indication(indication="[related_indication]")
# Analyze adverse events as therapeutic effects (e.g., minoxidil hair growth)
adverse_as_therapeutic = tu.tools.FAERS_search_reports_by_drug_and_reaction(drug_name="[drug_name]", limit=1000)
```

---

## Common Patterns

### Pattern 1: Rapid Screening
```python
targets = get_disease_targets(disease_id)[:10]
all_drugs = []
for target in targets:
    drugs = tu.tools.DGIdb_get_drug_gene_interactions(gene_name=target['gene_symbol'])
    all_drugs.extend(drugs)
approved_drugs = [d for d in all_drugs if d.get('approved')]
```

### Pattern 2: Deep Dive Single Drug
```python
drug_name = "metformin"
info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(drug_name_or_drugbank_id=drug_name)
targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(drug_name_or_drugbank_id=drug_name)
indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(drug_name_or_drugbank_id=drug_name)
pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(drug_name_or_drugbank_id=drug_name)
interactions = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(drug_name_or_id=drug_name)
warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(drug_name=drug_name)
papers = tu.tools.PubMed_search_articles(query=f"{drug_name} AND [new_disease]", max_results=100)
```

### Pattern 3: Comparative Analysis
```python
candidates = ["drug_a", "drug_b", "drug_c"]
comparison = []
for drug in candidates:
    data = {
        'name': drug,
        'info': tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(drug_name_or_drugbank_id=drug),
        'safety': tu.tools.FDA_get_warnings_and_cautions_by_drug_name(drug_name=drug),
        'evidence': tu.tools.PubMed_search_articles(query=drug, max_results=10)
    }
    comparison.append(data)
```

---

## Advanced Techniques

### Polypharmacology-Based Repurposing
Find drugs with multi-target activity matching disease network:
```python
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id, limit=50)
for drug in candidate_drugs:
    drug_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(drug_name_or_drugbank_id=drug)
    overlap = len(set(drug_targets) & set(disease_targets))
    if overlap >= 3:
        print(f"{drug}: hits {overlap} disease targets")
```

### Structure-Based Repurposing
Find structurally similar approved drugs:
```python
cid = tu.tools.PubChem_get_CID_by_compound_name(compound_name=known_active)
similar = tu.tools.PubChem_search_compounds_by_similarity(cid=cid['data']['cid'], threshold=85)
for compound in similar['data']:
    drug_info = tu.tools.PubChem_get_drug_label_info_by_CID(cid=compound['cid'])
```

### AI-Powered Candidate Selection
```python
for drug in candidates_with_smiles:
    admet = tu.tools.ADMETAI_predict_physicochemical_properties(smiles=drug['smiles'], use_cache=True)
    # Keep only drugs passing ADMET criteria
```

---

## Example Use Cases

### Rare Disease Repurposing
Strategy: Find drugs targeting same pathways as related common diseases.

### Adverse Effect as Therapy
Example: Thalidomide (teratogenic) -> cancer treatment. Analyze FAERS for beneficial adverse effects.

### Combination Therapy Discovery
Find drugs covering targets not addressed by existing therapy.
