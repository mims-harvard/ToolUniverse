# Drug Repurposing: Detailed Procedures

## Complete Workflow Code

### Phase 1: Disease & Target Analysis

```python
# 1.1 Get disease information
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="[disease_name]"
)

# 1.2 Find associated targets
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_info['data']['id'],
    limit=20
)

# 1.3 Get target details for top candidates
target_details = []
for target in targets['data'][:10]:
    details = tu.tools.UniProt_get_entry_by_accession(
        accession=target['uniprot_id']
    )
    target_details.append(details)
```

### Phase 2: Drug Discovery

```python
# 2.1 Find drugs targeting disease-associated targets
drug_candidates = []

for target in targets['data'][:10]:
    # Search DrugBank
    drugbank_results = tu.tools.drugbank_get_drug_name_and_description_by_target_name(
        target_name=target['gene_symbol']
    )

    # Search DGIdb
    dgidb_results = tu.tools.DGIdb_get_drug_gene_interactions(
        gene_name=target['gene_symbol']
    )

    # Search ChEMBL
    chembl_results = tu.tools.ChEMBL_search_drugs(
        query=target['gene_symbol'],
        limit=10
    )

    drug_candidates.extend([drugbank_results, dgidb_results, chembl_results])

# 2.2 Get drug details
for drug_name in unique_drugs:
    drug_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
        drug_name_or_drugbank_id=drug_name
    )
    indications = tu.tools.drugbank_get_indications_by_drug_name_or_drugbank_id(
        drug_name_or_drugbank_id=drug_name
    )
    pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
        drug_name_or_drugbank_id=drug_name
    )
```

### Phase 3: Safety & Feasibility Assessment

```python
# 3.1 Check FDA safety data
for drug in top_candidates:
    warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
        drug_name=drug['name']
    )
    adverse_events = tu.tools.FAERS_search_reports_by_drug_and_reaction(
        drug_name=drug['name'],
        limit=100
    )
    interactions = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(
        drug_name_or_id=drug['name']
    )

# 3.2 Assess ADMET properties (for novel formulations)
for drug in top_candidates:
    if 'smiles' in drug:
        admet = tu.tools.ADMETAI_predict_physicochemical_properties(
            smiles=drug['smiles'],
            use_cache=True
        )
```

### Phase 4: Literature Evidence

```python
for drug in top_candidates:
    pubmed_results = tu.tools.PubMed_search_articles(
        query=f"{drug['name']} AND {disease_name}",
        max_results=50
    )
    pmc_results = tu.tools.EuropePMC_search_articles(
        query=f"{drug['name']} AND {disease_name}",
        limit=50
    )
    trials = tu.tools.search_clinical_trials(
        condition=disease_name,
        intervention=drug['name']
    )
```

### Phase 5: Scoring & Ranking

```python
def score_repurposing_candidate(drug, target_score, safety_data, literature_count):
    """Score drug repurposing candidate (0-100)."""
    score = 0

    # Target association strength (0-40 points)
    score += min(target_score * 40, 40)

    # Safety profile (0-30 points)
    if drug['approval_status'] == 'approved':
        score += 20
    elif drug['approval_status'] == 'clinical':
        score += 10
    if not safety_data.get('black_box_warning'):
        score += 10

    # Literature evidence (0-20 points)
    score += min(literature_count / 5 * 20, 20)

    # Drug-likeness (0-10 points)
    if drug.get('bioavailability') == 'high':
        score += 10

    return score

# Score and rank all candidates
scored_candidates = []
for drug in drug_candidates:
    score = score_repurposing_candidate(
        drug=drug,
        target_score=drug['target_association_score'],
        safety_data=drug['safety_profile'],
        literature_count=drug['supporting_papers']
    )
    drug['repurposing_score'] = score
    scored_candidates.append(drug)

ranked_candidates = sorted(
    scored_candidates,
    key=lambda x: x['repurposing_score'],
    reverse=True
)
```

## Alternative Strategies

### Strategy A: Mechanism-Based Repurposing

```python
known_drug = "metformin"
moa = tu.tools.drugbank_get_drug_desc_pharmacology_by_moa(
    mechanism_of_action="[moa_term]"
)
similar = tu.tools.ChEMBL_search_similar_molecules(
    query=known_drug,
    similarity_threshold=70
)
```

### Strategy B: Network-Based Repurposing

```python
pathways = tu.tools.drugbank_get_pathways_reactions_by_drug_or_id(
    drug_name_or_drugbank_id="[drug_name]"
)
pathway_drugs = tu.tools.drugbank_get_drug_name_and_description_by_pathway_name(
    pathway_name=pathways['data'][0]['pathway_name']
)
```

### Strategy C: Phenotype-Based Repurposing

```python
indication_drugs = tu.tools.drugbank_get_drug_name_and_description_by_indication(
    indication="[related_indication]"
)
# Analyze adverse events as therapeutic effects (e.g., minoxidil → hair growth)
adverse_as_therapeutic = tu.tools.FAERS_search_reports_by_drug_and_reaction(
    drug_name="[drug_name]",
    limit=1000
)
```

## Advanced Techniques

### Polypharmacology-Based Repurposing

```python
# Find drugs with multi-target activity matching disease network
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_id, limit=50
)
for drug in candidate_drugs:
    drug_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
        drug_name_or_drugbank_id=drug
    )
    overlap = len(set(drug_targets) & set(disease_targets))
    if overlap >= 3:
        print(f"{drug}: hits {overlap} disease targets")
```

### Structure-Based Repurposing

```python
cid = tu.tools.PubChem_get_CID_by_compound_name(compound_name=known_active)
similar = tu.tools.PubChem_search_compounds_by_similarity(
    cid=cid['data']['cid'], threshold=85
)
for compound in similar['data']:
    drug_info = tu.tools.PubChem_get_drug_label_info_by_CID(cid=compound['cid'])
```

### AI-Powered Candidate Selection

```python
for drug in candidates_with_smiles:
    admet = tu.tools.ADMETAI_predict_physicochemical_properties(smiles=drug['smiles'], use_cache=True)
    admet_results.append({
        'drug': drug['name'],
        'admet': admet,
        'pass': evaluate_admet_criteria(admet)
    })
viable_candidates = [r for r in admet_results if r['pass']]
```

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

## Use Cases

### Use Case 1: Rare Disease Repurposing
```python
rare_disease = "Niemann-Pick disease"
related_disease = "Alzheimer's disease"  # Similar pathology
targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=related_disease_id)
# Find drugs for those targets, evaluate for rare disease applicability
```

### Use Case 2: Adverse Effect as Therapeutic
```python
# Example: Thalidomide (teratogenic) -> cancer treatment
adverse_events = tu.tools.FAERS_search_reports_by_drug_and_reaction(
    drug_name=drug, limit=1000
)
# Analyze if adverse effects beneficial in other contexts (e.g., weight loss AE -> obesity)
```

### Use Case 3: Combination Therapy Discovery
```python
disease_targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id)
primary_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id=primary_drug
)
uncovered_targets = [t for t in disease_targets if t not in primary_targets]
# Find drugs for uncovered targets
```

## Troubleshooting

- **"Disease not found"**: Try disease synonyms or EFO ID lookup; use broader disease categories
- **"No drugs found for target"**: Check target name/symbol (HUGO nomenclature); expand to pathway-level drugs; consider similar targets (protein family)
- **"Insufficient literature evidence"**: Search for drug class rather than specific drug; check preclinical/animal studies; look for mechanism papers
- **"Safety data unavailable"**: Drug may not be FDA approved in US; check EMA or other regulatory databases; review clinical trial safety data
