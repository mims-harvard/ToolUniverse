# Scoring Criteria & Recommendation Tiers

## Trial Match Score Components (Total: 0-100)

### Molecular Match (0-40 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Exact biomarker match | 40 | Trial requires patient's specific variant |
| Gene-level match | 30 | Trial requires gene mutation, patient has specific variant |
| Pathway match | 20 | Trial targets same pathway as patient's biomarker |
| No molecular criteria | 10 | General disease trial |
| Excluded biomarker | 0 | Patient's biomarker is in exclusion criteria |

### Clinical Eligibility (0-25 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| All criteria met | 25 | Disease, stage, prior treatment all match |
| Most criteria met | 18 | 1-2 criteria unclear |
| Some criteria met | 10 | Several criteria unclear |
| Clearly ineligible | 0 | Fails major criterion |

### Evidence Strength (0-20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| FDA-approved combination | 20 | T1 evidence |
| Phase III positive | 15 | T2 evidence |
| Phase II promising | 10 | T3 evidence |
| Phase I or no results | 5 | T4 evidence |

### Trial Phase (0-10 points)

| Phase | Points |
|-------|--------|
| Phase III | 10 |
| Phase II | 8 |
| Phase I/II | 6 |
| Phase I | 4 |

### Geographic Feasibility (0-5 points)

| Criterion | Points |
|-----------|--------|
| Patient's city/state | 5 |
| Same country | 3 |
| International only | 1 |
| Unknown | 0 |

## Evidence Tier Classification

| Tier | Symbol | Criteria | Score Impact |
|------|--------|----------|-------------|
| **T1** | [T1] | FDA-approved biomarker-drug, NCCN guideline | 20 points |
| **T2** | [T2] | Phase III positive, clinical evidence | 15 points |
| **T3** | [T3] | Phase I/II results, preclinical | 10 points |
| **T4** | [T4] | Computational, mechanism inference | 5 points |

## Recommendation Tiers

| Score | Tier | Label | Action |
|-------|------|-------|--------|
| **80-100** | Tier 1 | Optimal Match | Strongly recommend - contact site immediately |
| **60-79** | Tier 2 | Good Match | Recommend - discuss with care team |
| **40-59** | Tier 3 | Possible Match | Consider - needs further eligibility review |
| **0-39** | Tier 4 | Exploratory | Backup option - consider if Tier 1-3 unavailable |

## Molecular Match Scoring Logic

```python
def score_molecular_match(patient_biomarkers, trial_requirements):
    """Score molecular match between patient and trial (0-40 points)."""
    if not trial_requirements['required_biomarkers'] and not trial_requirements['excluded_biomarkers']:
        return 10, 'No specific molecular criteria (general trial)'

    patient_genes = {b['gene'].upper() for b in patient_biomarkers}
    required_genes = {b['gene'].upper() for b in trial_requirements['required_biomarkers']}
    excluded_genes = {b['gene'].upper() for b in trial_requirements['excluded_biomarkers']}

    # Check exclusions first
    excluded_match = patient_genes & excluded_genes
    if excluded_match:
        return 0, f'Patient biomarker(s) {excluded_match} are in exclusion criteria'

    if not required_genes:
        return 10, 'No specific biomarker requirements found'

    # Check for exact gene match
    matched_genes = patient_genes & required_genes
    if matched_genes:
        exact_variant_match = False
        for req in trial_requirements['required_biomarkers']:
            for pb in patient_biomarkers:
                if pb['gene'].upper() == req['gene'].upper():
                    alt = pb.get('alteration', '').upper()
                    if alt and alt in req.get('context', '').upper():
                        exact_variant_match = True
                        break

        if exact_variant_match:
            return 40, f'Exact biomarker match: {matched_genes} with specific variant'
        else:
            return 30, f'Gene-level match: {matched_genes} (specific variant match unclear)'

    return 5, 'No direct biomarker match found'
```

## Drug-Biomarker Alignment Scoring

```python
def score_drug_biomarker_alignment(patient_gene_symbols, drug_mechanisms):
    """Check if trial drug targets patient's biomarkers."""
    patient_genes_upper = {g.upper() for g in patient_gene_symbols}

    for mech in drug_mechanisms:
        target_genes = {g.upper() for g in mech.get('target_genes', [])}
        if patient_genes_upper & target_genes:
            return True, f"Drug targets {patient_genes_upper & target_genes} via {mech.get('mechanism')}"

    return False, "No direct target overlap with patient biomarkers"
```
