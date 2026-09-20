# Pharmacovigilance Safety Analyzer - Tool Reference

## Phase 1: Drug Identification

### DailyMed Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DailyMed_search_spls` | Search drug labels | `drug_name` |
| `DailyMed_search_spls` | Get full label | `setid` |
| `DailyMed_parse_drug_interactions` | Drug interactions | `setid` |

**Example - Resolve drug identity**:
```python
# Search for drug
results = tu.tools.DailyMed_search_spls(drug_name="metformin")
setid = results[0]['setid']

# Get full label
label = tu.tools.DailyMed_get_spl_by_setid(setid=setid)
```

### ChEMBL Drug Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChEMBL_search_drugs` | Search drugs | `query` |
| `ChEMBL_get_molecule` | Get molecule details | `molecule_chembl_id` |
| `ChEMBL_get_drug_mechanisms` | Get MOA | `molecule_chembl_id` |

---

## Phase 2: FAERS Adverse Events

### FAERS Query Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `FAERS_count_reactions_by_drug_event` | AE counts for drug | `medicinalproduct`, `limit` |
| `FAERS_search_reports_by_drug_and_reaction` | Reports for a drug + specific reaction | `medicinalproduct`, `reactionmeddrapt` |
| `FAERS_search_adverse_event_reports` | Search all reports for a drug | `medicinalproduct`, `limit` |
| `FAERS_calculate_disproportionality` | PRR / ROR / IC signal metrics | `drug_name`, `adverse_event` |
| `FAERS_stratify_by_demographics` | Patient demographics | `drug_name`, `reaction` |

**Parameter Note**: The `FAERS_count_*` and `FAERS_search_*` tools take `medicinalproduct` (not `drug_name` or `drug`); the analysis tools (`FAERS_calculate_disproportionality`, `FAERS_stratify_by_demographics`) take `drug_name`.

**Example - Get adverse events**:
```python
# Get top adverse events
events = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct="metformin",
    limit=50
)
# Returns: results[] of {term, count}, e.g. {"term": "NAUSEA", "count": 31807}

# Get details for specific event
details = tu.tools.FAERS_search_reports_by_drug_and_reaction(
    medicinalproduct="metformin",
    reactionmeddrapt="Lactic acidosis"
)
# Returns: reports[] (patient, drug, reaction details per case)

# Signal strength for a drug-event pair
signal = tu.tools.FAERS_calculate_disproportionality(
    drug_name="metformin",
    adverse_event="Lactic acidosis"
)
# Returns: data.metrics.PRR.value / ROR.value / IC.value and data.signal_detection
```

### OpenFDA Tools (Alternative)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OpenFDA_search_drug_events` | AE reports | `search` |
| `OpenFDA_search_drug_enforcement` | Drug recalls | `search` |
| `OpenFDA_search_drug_enforcement` | Enforcement actions | `search` |

---

## Phase 3: Label Warnings

### DailyMed Label Sections

```python
def extract_safety_sections(tu, setid):
    """Extract all safety-relevant sections from label."""
    label = tu.tools.DailyMed_get_spl_by_setid(setid=setid)
    
    return {
        'boxed_warning': label.get('boxed_warning'),
        'contraindications': label.get('contraindications'),
        'warnings_precautions': label.get('warnings_and_precautions'),
        'adverse_reactions': label.get('adverse_reactions'),
        'drug_interactions': label.get('drug_interactions'),
        'use_in_specific_populations': label.get('use_in_specific_populations'),
        'overdosage': label.get('overdosage')
    }
```

---

## Phase 4: Pharmacogenomics

### PharmGKB Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PharmGKB_search_drugs` | Search drug annotations | `query` |
| `PharmGKB_get_clinical_annotations` | Clinical PGx data (one annotation) | `annotation_id` |
| `PharmGKB_get_drug_details` | PGx labeling | `drug_id` |
| `PharmGKB_search_variants` | Relevant variants | `drug_id` |

**Example - Get PGx data**:
```python
# Search for drug
pgx = tu.tools.PharmGKB_search_drugs(query="warfarin")

# Drug record (pgx['data'][0]['id'] == "PA451906" for warfarin)
drug = tu.tools.PharmGKB_get_drug_details(drug_id=pgx['data'][0]['id'])

# Clinical annotations are fetched by annotation ID (lookup by drug or gene is not supported by the API)
annotation = tu.tools.PharmGKB_get_clinical_annotations(
    annotation_id="1183618159"
)
```

### CPIC Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CPIC_list_guidelines` | CPIC guidelines | `drug_name` or `gene` |
| `CPIC_get_recommendations` | Dosing recommendations | `guideline_id` |

---

## Phase 5: Clinical Trial Safety

### ClinicalTrials.gov Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_clinical_trials` | Search trials | `intervention`, `condition`, `query_term`, `overall_status` (list) |
| `ClinicalTrials_get_study` | Get trial details | `nct_id` |
| `get_clinical_trial_outcome_measures` | Get posted results | `nct_ids` (list), `outcome_measures` |

**Example - Get trial safety data**:
```python
# Search completed phase 3 trials
# There is no phase parameter: filter phase with an Essie expression in query_term
trials = tu.tools.search_clinical_trials(
    intervention="metformin",
    query_term="AREA[Phase]PHASE3",
    overall_status=["COMPLETED"],
    pageSize=20
)

# Fetch outcome measures for the returned trials
for trial in trials['data']['studies']:
    results = tu.tools.get_clinical_trial_outcome_measures(
        nct_ids=[trial['NCT ID']]
    )
```

---

## Phase 5.5: Pathway & Mechanism Context (NEW)

### KEGG Pathway Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `kegg_search_pathway` | Search pathways | `keyword` |
| `kegg_get_gene_info` | Get gene details | `gene_id` |
| `kegg_find_genes` | Find genes by keyword | `keyword`, `organism` |

**Example - Get drug metabolism pathways**:
```python
# Search for drug metabolism
pathways = tu.tools.kegg_search_pathway(keyword="drug metabolism")
# Returns: data[] of {pathway_id: "map00982", description: ...}

# Get genes in pathway (needs the organism-specific ID, hsaNNNNN, not the mapNNNNN reference ID)
pathway_id = "hsa" + pathways['data'][0]['pathway_id'][3:]
genes = tu.tools.KEGG_get_pathway_genes(pathway_id=pathway_id)
# Returns: data.genes[] such as "hsa:10720"
```

### Reactome Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ReactomeContent_search` | Search pathways | `query`, `species` |
| `Reactome_get_participants` | Get pathway entities | `pathway_id` |

**Use**: Understand drug mechanism pathways to contextualize adverse events.

---

## Phase 5.6: Literature Intelligence (NEW)

### PubMed Safety Literature

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search articles | `query`, `limit` |
| `PubMed_get_article` | Get article | `pmid` |

**Example - Search safety literature**:
```python
papers = tu.tools.PubMed_search_articles(
    query="metformin adverse event lactic acidosis",
    limit=50
)
```

### Preprint Servers (Emerging Safety Signals)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search preprints (bioRxiv/medRxiv) | `query` (prefix `SRC:PPR AND` for preprints only), `limit` |
| `BioRxiv_get_preprint` | Get preprint by DOI | `doi` |

**⚠️ Preprints are NOT peer-reviewed but may contain emerging safety signals!**

**Example - Search preprints for emerging signals** (bioRxiv/medRxiv don't have search APIs, use EuropePMC):
```python
# EuropePMC for mechanism insights
preprints = tu.tools.EuropePMC_search_articles(
    query="SRC:PPR AND metformin toxicity mechanism",  # SRC:PPR = preprints only
    limit=15
)

# MedRxiv for real-world safety data (via EuropePMC)
clinical_preprints = tu.tools.EuropePMC_search_articles(
    query="SRC:PPR AND metformin real-world safety",
    limit=15
)
```

### Citation Analysis Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `openalex_search_works` | Search with citations | `query`, `limit` |
| `SemanticScholar_search_papers` | AI-ranked search | `query`, `limit` |

**Example - Find high-impact safety papers**:
```python
papers = tu.tools.openalex_search_works(
    query="metformin lactic acidosis clinical",
    limit=20
)
# Sort by cited_by_count for impact
```

---

## Disproportionality Calculations

### PRR Calculation

```python
def calculate_prr(a, b, c, d):
    """
    Calculate Proportional Reporting Ratio.
    
    a = reports of drug X with event Y
    b = reports of drug X with all other events
    c = reports of event Y with all other drugs
    d = reports of all other drug-event pairs
    
    PRR = (a/(a+b)) / (c/(c+d))
    """
    prr = (a / (a + b)) / (c / (c + d))
    
    # 95% CI using Rothman formula
    import math
    se = math.sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))
    ci_lower = math.exp(math.log(prr) - 1.96 * se)
    ci_upper = math.exp(math.log(prr) + 1.96 * se)
    
    return {
        'prr': prr,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'significant': ci_lower > 1.0
    }
```

### Signal Detection Criteria

```python
def detect_signal(prr, ci_lower, n_cases):
    """
    Apply signal detection criteria.
    
    WHO-UMC criteria: PRR ≥2, Chi-squared ≥4, N ≥3
    """
    is_signal = prr >= 2 and ci_lower >= 1 and n_cases >= 3
    
    if prr > 10:
        tier = 'T1'  # Critical
    elif prr > 3:
        tier = 'T2'  # Moderate
    elif prr > 2:
        tier = 'T3'  # Mild
    else:
        tier = 'T4'  # Known/expected
    
    return {
        'is_signal': is_signal,
        'tier': tier
    }
```

---

## Workflow Code Examples

### Example 1: Complete Safety Profile

```python
def generate_safety_profile(tu, drug_name):
    """Generate comprehensive safety profile for a drug."""
    
    # Phase 1: Identify drug
    dailymed = tu.tools.DailyMed_search_spls(drug_name=drug_name)
    chembl = tu.tools.ChEMBL_search_drugs(query=drug_name)
    
    # Phase 2: FAERS events
    events = tu.tools.FAERS_count_reactions_by_drug_event(
        medicinalproduct=drug_name,
        limit=50
    )
    
    # Phase 3: Label warnings
    if dailymed:
        label = tu.tools.DailyMed_get_spl_by_setid(
            setid=dailymed[0]['setid']
        )
    
    # Phase 4: Pharmacogenomics
    pgx = tu.tools.PharmGKB_search_drugs(query=drug_name)
    
    # Phase 5: Clinical trials
    trials = tu.tools.search_clinical_trials(
        intervention=drug_name,
        query_term="AREA[Phase]PHASE3",
        overall_status=["COMPLETED"]
    )
    
    return {
        'identification': {'dailymed': dailymed, 'chembl': chembl},
        'adverse_events': events,
        'label': label,
        'pharmacogenomics': pgx,
        'trials': trials
    }
```

### Example 2: Drug Comparison

```python
def compare_drug_safety(tu, drug_a, drug_b):
    """Compare safety profiles of two drugs."""
    
    # Get events for both drugs
    events_a = tu.tools.FAERS_count_reactions_by_drug_event(
        medicinalproduct=drug_a, limit=30
    )
    events_b = tu.tools.FAERS_count_reactions_by_drug_event(
        medicinalproduct=drug_b, limit=30
    )
    
    # Find common events (results[] items are {term, count})
    events_a_dict = {e['term']: e for e in events_a['results']}
    events_b_dict = {e['term']: e for e in events_b['results']}
    
    common_events = set(events_a_dict.keys()) & set(events_b_dict.keys())
    
    comparison = []
    for event in common_events:
        comparison.append({
            'event': event,
            'drug_a_count': events_a_dict[event].get('count'),
            'drug_b_count': events_b_dict[event].get('count')
            # PRR is not in the count results: call FAERS_calculate_disproportionality per drug/event
        })
    
    return comparison
```

### Example 3: Emerging Signal Detection

```python
def detect_emerging_signals(tu, drug_name, threshold_prr=3.0):
    """Identify signals that may require attention."""
    
    events = tu.tools.FAERS_count_reactions_by_drug_event(
        medicinalproduct=drug_name,
        limit=100
    )
    
    signals = []
    for event in events['results']:
        # PRR comes from the disproportionality tool, not the count tool
        metrics = tu.tools.FAERS_calculate_disproportionality(
            drug_name=drug_name,
            adverse_event=event['term']
        )['data']['metrics']
        prr = metrics['PRR']['value']
        if prr >= threshold_prr:
            signals.append({
                'event': event['term'],
                'prr': prr,
                'count': event['count']
            })
    
    # Sort by signal strength
    return sorted(signals, key=lambda x: x['prr'], reverse=True)
```

---

## Fallback Chains

### FAERS Alternatives
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `FAERS_count_reactions_by_drug_event` | `OpenFDA_search_drug_events` | PubMed safety literature |
| `FAERS_search_adverse_event_reports` | OpenFDA with filters | Manual FAERS query |

### Label Alternatives
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `DailyMed_search_spls` | `OpenFDA_search_drug_labels` | FDA website |
| `DailyMed_search_spls` | `FDA_search_drug_labels` | DrugBank |

### PGx Alternatives
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PharmGKB_search_drugs` | `CPIC_list_guidelines` | FDA PGx table |
| `PharmGKB_get_clinical_annotations` | Literature search | FDA label PGx |

### Pathway Analysis (NEW)
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `kegg_search_pathway` | `ReactomeContent_search` | Literature search |

### Literature (NEW)
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PubMed_search_articles` | `openalex_search_works` | `SemanticScholar_search_papers` |
| `EuropePMC_search_articles` (`SRC:PPR` query) | `web_search` (site:medrxiv.org) | Skip preprints |

---

## ICD-10 Mapping Tool

### AdverseEventICDMapper

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `AdverseEventICDMapper` | Map AE text to ICD-10 | `text` |

**Example**:
```python
# Map adverse event to ICD-10
mapping = tu.tools.AdverseEventICDMapper(
    text="Patient developed severe hepatotoxicity with jaundice"
)
# Returns: [{"adverse_event": "hepatotoxicity", "icd10cm_code": "K71.9", ...}]
```

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `FAERS_count_reactions_by_drug_event` | `drug="metformin"` / `drug_name="metformin"` | `medicinalproduct="metformin"` |
| `DailyMed_search_spls` | `name="aspirin"` | `drug_name="aspirin"` |
| `PharmGKB_search_drugs` | `drug="warfarin"` | `query="warfarin"` |
| `OpenFDA_search_drug_events` | `drug_name="X"` | `search="patient.drug.medicinalproduct:X"` |

---

## Rate Limits and Best Practices

### FAERS/OpenFDA
- Rate limit: 240 requests/minute (without API key)
- Best practice: Cache results, batch queries

### PharmGKB
- No strict rate limit
- Best practice: Use drug ID for subsequent queries

### DailyMed
- No strict rate limit
- Best practice: Cache SPL content (large responses)

### ClinicalTrials.gov
- Rate limit: 3 requests/second
- Best practice: Use pageSize parameter to reduce calls
