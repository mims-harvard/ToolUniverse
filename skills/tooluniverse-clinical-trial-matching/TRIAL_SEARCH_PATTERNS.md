# Trial Search Patterns & Execution Strategy

## Trial Search Functions

### Disease-Based Search

```python
def search_trials_by_disease(tu, disease_name, status_filter=None, phase_filter=None, page_size=20):
    """Search ClinicalTrials.gov by disease/condition."""
    query_parts = []
    if status_filter:
        query_parts.append(f'AREA[OverallStatus]{status_filter}')
    if phase_filter:
        query_parts.append(phase_filter)

    query_term = ' AND '.join(query_parts) if query_parts else disease_name

    result = tu.tools.search_clinical_trials(
        condition=disease_name,
        query_term=query_term if query_parts else disease_name,
        pageSize=page_size
    )

    if isinstance(result, str):
        return []
    return result.get('studies', [])
```

### Biomarker-Specific Search

```python
def search_trials_by_biomarker(tu, gene_symbol, alteration, disease_name=None, page_size=15):
    """Search trials mentioning specific biomarkers."""
    biomarker_query = f'{gene_symbol} {alteration}' if alteration else gene_symbol

    result = tu.tools.search_clinical_trials(
        condition=disease_name if disease_name else '',
        query_term=biomarker_query,
        pageSize=page_size
    )

    if isinstance(result, str):
        return []
    return result.get('studies', [])
```

### Intervention-Based Search

```python
def search_trials_by_intervention(tu, drug_name, disease_name=None, page_size=10):
    """Search trials by intervention/drug name."""
    result = tu.tools.search_clinical_trials(
        condition=disease_name if disease_name else '',
        intervention=drug_name,
        query_term=drug_name,
        pageSize=page_size
    )

    if isinstance(result, str):
        return []
    return result.get('studies', [])
```

### Alternative Search (clinical_trials_search)

```python
def search_trials_alternative(tu, condition, intervention=None, limit=10):
    """Alternative trial search with different API endpoint."""
    params = {
        'action': 'search_studies',
        'condition': condition,
        'limit': limit
    }
    if intervention:
        params['intervention'] = intervention

    result = tu.tools.clinical_trials_search(**params)
    return result.get('studies', [])
```

### Deduplication

```python
def deduplicate_trials(trial_lists):
    """Merge and deduplicate trials from multiple searches."""
    seen_ncts = set()
    unique_trials = []

    for trials in trial_lists:
        for trial in trials:
            nct = trial.get('NCT ID') or trial.get('nctId', '')
            if nct and nct not in seen_ncts:
                seen_ncts.add(nct)
                unique_trials.append(trial)

    return unique_trials
```

## Batch Trial Detail Retrieval (Phase 3)

All batch functions process NCT IDs in groups of 10:

```python
def get_trial_eligibility(tu, nct_ids):
    all_criteria = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_eligibility_criteria(nct_ids=batch, eligibility_criteria='all')
        if isinstance(result, list):
            all_criteria.extend(result)
    return all_criteria

def get_trial_interventions(tu, nct_ids):
    all_interventions = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_conditions_and_interventions(nct_ids=batch, condition_and_intervention='all')
        if isinstance(result, list):
            all_interventions.extend(result)
    return all_interventions

def get_trial_locations(tu, nct_ids):
    all_locations = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_locations(nct_ids=batch, location='all')
        if isinstance(result, list):
            all_locations.extend(result)
    return all_locations

def get_trial_status(tu, nct_ids):
    all_status = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_status_and_dates(nct_ids=batch, status_and_date='all')
        if isinstance(result, list):
            all_status.extend(result)
    return all_status

def get_trial_descriptions(tu, nct_ids):
    all_descriptions = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_descriptions(nct_ids=batch, description_type='full')
        if isinstance(result, list):
            all_descriptions.extend(result)
    return all_descriptions
```

## Geographic & Feasibility Analysis (Phase 7)

```python
def analyze_trial_locations(locations_data, patient_location=None):
    """Analyze trial site locations and proximity."""
    if not locations_data:
        return {'total_sites': 0, 'countries': [], 'us_states': [], 'nearest': None}

    locations = locations_data.get('locations', [])
    countries = list(set(loc.get('country', '') for loc in locations if loc.get('country')))
    us_states = list(set(loc.get('state', '') for loc in locations if loc.get('country') == 'United States' and loc.get('state')))

    return {
        'total_sites': len(locations),
        'countries': countries,
        'us_states': us_states,
        'has_us_sites': 'United States' in countries,
        'locations': locations[:10]
    }
```

## Alternative Options (Phase 8)

### Basket Trial Search

**IMPORTANT**: ClinicalTrials.gov search is sensitive to query complexity. Overly specific queries like "NTRK fusion tumor agnostic" may return zero results. Use simpler queries and combine results.

```python
def search_basket_trials(tu, biomarker, page_size=10):
    query_terms = [
        f'{biomarker} solid tumor',
        f'{biomarker}',
        f'{biomarker} basket',
    ]

    all_trials = []
    for query in query_terms:
        result = tu.tools.search_clinical_trials(query_term=query, pageSize=page_size)
        if not isinstance(result, str):
            all_trials.extend(result.get('studies', []))

    return deduplicate_trials([all_trials])
```

### Expanded Access Search

```python
def search_expanded_access(tu, drug_name):
    result = tu.tools.search_clinical_trials(query_term=f'{drug_name} expanded access', pageSize=5)
    if isinstance(result, str):
        return []
    return result.get('studies', [])
```

## Parallelization Opportunities

**Parallel Group 1** (Phase 1 - all simultaneous):
- `MyGene_query_genes` for each gene
- `OpenTargets_get_disease_id_description_by_name` for disease
- `ols_search_efo_terms` for disease
- `fda_pharmacogenomic_biomarkers` (no params)

**Parallel Group 2** (Phase 2 - all simultaneous):
- `search_clinical_trials` with disease condition
- `search_clinical_trials` with biomarker query
- `search_clinical_trials` with intervention query
- `clinical_trials_search` as alternative

**Parallel Group 3** (Phase 3 - all simultaneous):
- `get_clinical_trial_eligibility_criteria` for all NCT IDs
- `get_clinical_trial_conditions_and_interventions` for all NCT IDs
- `get_clinical_trial_locations` for all NCT IDs
- `get_clinical_trial_status_and_dates` for all NCT IDs
- `get_clinical_trial_descriptions` for all NCT IDs

**Parallel Group 4** (Phases 5-6 - for each drug):
- `OpenTargets_get_drug_id_description_by_name` for drug
- `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` for drug
- `FDA_get_indications_by_drug_name` for drug
- `PubMed_search_articles` for evidence

## Performance Optimization

- Batch NCT IDs in groups of 10 for detail tools
- Limit initial search to 20-30 trials per search strategy
- Focus detailed analysis on top 15-20 candidates after initial filtering
- Cache gene/disease resolution results for reuse across phases

## Error Handling

For each tool call:
1. Wrap in try/except
2. Check for empty results
3. Use fallback tools when primary fails
4. Document what failed in completeness checklist
5. Never let one failure block the entire analysis

## Common Use Patterns

### Pattern 1: Targeted Therapy Matching (Most Common)
**Input**: "NSCLC patient with EGFR L858R, failed platinum chemotherapy"
1. Resolve: NSCLC -> EFO_0003060, EGFR -> ENSG00000146648
2. Search: "non-small cell lung cancer" + "EGFR mutation" + "EGFR L858R"
3. Filter: Recruiting trials with EGFR molecular requirements
4. Match: Score trials by EGFR L858R specificity
5. Drugs: Identify TKIs (osimertinib, erlotinib, etc.) in trial arms
6. Evidence: Check FDA approval of EGFR TKIs for NSCLC
7. Report: Prioritize targeted therapy trials, include immunotherapy options

### Pattern 2: Immunotherapy Selection
**Input**: "Melanoma, TMB-high, PD-L1 positive, failed ipilimumab"
1. Resolve: Melanoma -> EFO_0000756
2. Search: "melanoma" + "TMB" + "PD-L1" + "immunotherapy"
3. Filter: Trials requiring PD-L1 or TMB testing
4. Match: Score by TMB/PD-L1 requirements
5. Drugs: Identify checkpoint inhibitors (pembrolizumab, nivolumab)
6. Evidence: Check FDA approval for TMB-high indications
7. Report: Focus on anti-PD-1/PD-L1 trials, combination immunotherapy

### Pattern 3: Basket Trial Identification
**Input**: "Any solid tumor with NTRK fusion"
1. Resolve: NTRK genes (NTRK1, NTRK2, NTRK3)
2. Search: "NTRK fusion" + "tumor agnostic" + "basket"
3. Filter: Biomarker-agnostic trials
4. Match: Score by NTRK-specific inclusion criteria
5. Drugs: Identify larotrectinib, entrectinib
6. Evidence: FDA tissue-agnostic approval for larotrectinib
7. Report: Highlight tumor-agnostic approval, broad eligibility

### Pattern 4: Post-Progression Options
**Input**: "Breast cancer, failed CDK4/6 inhibitors, ESR1 mutation"
1. Resolve: Breast cancer -> EFO_0000305, ESR1 -> ENSG00000091831
2. Search: "breast cancer" + "ESR1" + "CDK4/6 resistance"
3. Filter: Trials for post-CDK4/6 setting
4. Match: Score by ESR1 mutation and prior treatment requirements
5. Drugs: Identify novel endocrine agents, SERDs, ESR1-targeting drugs
6. Evidence: Check clinical data for post-CDK4/6 options
7. Report: Focus on resistance-overcoming strategies

### Pattern 5: Geographic Search
**Input**: "Lung cancer trials within 100 miles of Boston"
1. Search: "lung cancer" (broad)
2. Get locations for all candidate trials
3. Filter: Sites in Massachusetts and nearby states
4. Score: High geographic feasibility for Boston-area sites
5. Report: Prioritize by proximity, include contact info

## Edge Case Handling

### No Matching Trials Found
1. Broaden search to gene-level (remove specific variant)
2. Search for pathway-level trials
3. Search basket trials
4. Suggest additional biomarker testing
5. Report alternative options (off-label, compassionate use)

### Rare Biomarkers
1. Search gene-level trials (any EGFR mutation)
2. Search mechanism-level trials (TKI trials)
3. Check CIViC for any evidence on this specific variant
4. Note variant rarity in report
5. Suggest discussion with molecular tumor board

### Multiple Biomarkers
1. Search for each biomarker independently
2. Search for combination biomarker trials
3. Identify trials that require multiple biomarkers
4. Score based on most actionable biomarker
5. Flag potential synergistic drug targets

### Conflicting Eligibility
1. Score partial match transparently
2. Highlight which criteria are met/unmet
3. Note if unmet criteria are waivable
4. Suggest contacting PI for edge cases
5. Provide alternative trials without conflicting criteria
