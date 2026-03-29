---
name: tooluniverse-clinical-trial-design
description: Strategic clinical trial design feasibility assessment using ToolUniverse. Evaluates patient population sizing, biomarker prevalence, endpoint selection, comparator analysis, safety monitoring, and regulatory pathways. Creates comprehensive feasibility reports with evidence grading, enrollment projections, and trial design recommendations. Use when planning Phase 1/2 trials, assessing trial feasibility, or designing biomarker-driven studies.
---

# Clinical Trial Design Feasibility Assessment

Systematically assess clinical trial feasibility by analyzing 6 research dimensions. Produces comprehensive feasibility reports with quantitative enrollment projections, endpoint recommendations, and regulatory pathway analysis.

**IMPORTANT**: Always use English terms in tool calls (drug names, disease names, biomarker names), even if the user writes in another language. Only try original-language terms as a fallback if English returns no results. Respond in the user's language.

## Reasoning Before Searching

Trial design starts with the question, not the methods. Answer these four questions before running any tools — they determine everything else:

1. **What is the primary endpoint?** Is it overall survival (gold standard but slow), PFS (faster but surrogate), ORR (single-arm friendly but not always accepted), or a biomarker (needs validation as surrogate first)? The endpoint determines FDA pathway, statistical design, and duration.
2. **Who is the population?** Broad unselected vs. biomarker-enriched. Enriched populations have higher response rates, allowing smaller trials — but require a validated companion diagnostic and reduce the eligible patient pool.
3. **What is the comparator?** Placebo (only if no standard of care exists), active control (requires non-inferiority or superiority framing), or single-arm with historical control (acceptable for rare diseases or breakthrough designations, but FDA scrutiny is high).
4. **Is the effect size realistic given the mechanism?** A 20% improvement in ORR over SOC requires ~100 patients per arm. A 50% improvement requires ~30. If the mechanism only justifies a 10% improvement, the trial may be underpowered regardless of design. Check precedent effect sizes in similar trials before committing to an endpoint.

These four answers determine sample size, duration, and trial design. Look them up from precedent trials and FDA guidance — do not derive them from first principles.

**LOOK UP DON'T GUESS**: Never assume what the standard of care is for an indication — look it up with DrugBank and FDA tools. Never assume an endpoint is FDA-accepted — verify with `search_clinical_trials` precedents and `OpenFDA_get_approval_history`. Never estimate prevalence from memory — use OpenTargets, gnomAD, or COSMIC.

## Core Principles

### 1. Report-First Approach (MANDATORY)
**DO NOT** show tool outputs to user. Instead:
1. Create `[INDICATION]_trial_feasibility_report.md` FIRST
2. Initialize with all section headers
3. Progressively update as data arrives
4. Present only the final report

### 2. Evidence Grading System

| Grade | Symbol | Criteria | Examples |
|-------|--------|----------|----------|
| **A** | 3-star | Regulatory acceptance, multiple precedents | FDA-approved endpoint in same indication |
| **B** | 2-star | Clinical validation, single precedent | Phase 3 trial in related indication |
| **C** | 1-star | Preclinical or exploratory | Phase 1 use, biomarker validation ongoing |
| **D** | 0-star | Proposed, no validation | Novel endpoint, no precedent |

### 3. Feasibility Score (0-100)
Weighted composite score:
- **Patient Availability** (30%): Population size x biomarker prevalence x geography
- **Endpoint Precedent** (25%): Historical use, regulatory acceptance
- **Regulatory Clarity** (20%): Pathway defined, precedents exist
- **Comparator Feasibility** (15%): Standard of care availability
- **Safety Monitoring** (10%): Known risks, monitoring established

**Interpretation**: >=75 HIGH (proceed), 50-74 MODERATE (additional validation), <50 LOW (de-risking required)

---

## When to Use This Skill

Apply when users:
- Plan early-phase trials (Phase 1/2 emphasis)
- Need enrollment feasibility assessment
- Design biomarker-selected trials
- Evaluate endpoint strategies
- Assess regulatory pathways
- Compare trial design options
- Need safety monitoring plans

**Trigger phrases**: "clinical trial design", "trial feasibility", "enrollment projections", "endpoint selection", "trial planning", "Phase 1/2 design", "basket trial", "biomarker trial"

---

## Core Strategy: 6 Research Paths

Execute 6 parallel research dimensions. See `STUDY_DESIGN_PROCEDURES.md` for detailed steps per path.

```
Trial Design Query
|
+-- PATH 1: Patient Population Sizing
|   Disease prevalence, biomarker prevalence, geographic distribution,
|   eligibility criteria impact, enrollment projections
|
+-- PATH 2: Biomarker Prevalence & Testing
|   Mutation frequency, testing availability, turnaround time,
|   cost/reimbursement, alternative biomarkers
|
+-- PATH 3: Comparator Selection
|   Standard of care, approved comparators, historical controls,
|   placebo appropriateness, combination therapy
|
+-- PATH 4: Endpoint Selection
|   Primary endpoint precedents, FDA acceptance history,
|   measurement feasibility, surrogate vs clinical endpoints
|
+-- PATH 5: Safety Endpoints & Monitoring
|   Mechanism-based toxicity, class effects, organ-specific monitoring,
|   DLT history, safety monitoring plan
|
+-- PATH 6: Regulatory Pathway
    Regulatory precedents (505(b)(1), 505(b)(2)), breakthrough therapy,
    orphan drug, fast track, FDA guidance
```

---

## Report Structure (14 Sections)

Create `[INDICATION]_trial_feasibility_report.md` with all 14 sections. See `REPORT_TEMPLATE.md` for full templates with fillable fields.

1. **Executive Summary** - Feasibility score, key findings, go/no-go recommendation
2. **Disease Background** - Prevalence, incidence, SOC, unmet need
3. **Patient Population Analysis** - Base population, biomarker selection, eligibility funnel, enrollment projections
4. **Biomarker Strategy** - Primary biomarker, alternatives, testing logistics
5. **Endpoint Selection & Justification** - Primary/secondary/exploratory endpoints, statistical considerations
6. **Comparator Analysis** - SOC, trial design options (single-arm vs randomized vs non-inferiority), drug sourcing
7. **Safety Endpoints & Monitoring Plan** - DLT definition, mechanism-based toxicities, organ monitoring, SMC
8. **Study Design Recommendations** - Phase, design type, schema, eligibility, treatment plan, assessment schedule
9. **Enrollment & Site Strategy** - Site selection, enrollment projections, recruitment strategies
10. **Regulatory Pathway** - FDA pathway, precedents, pre-IND meeting, IND timeline
11. **Budget & Resource Considerations** - Cost drivers, timeline, FTE requirements
12. **Risk Assessment** - Feasibility risks, scientific risks, mitigation strategies
13. **Success Criteria & Go/No-Go Decision** - Phase 1/2 criteria, interim analysis, feasibility scorecard
14. **Recommendations & Next Steps** - Final recommendation, critical path to IND, alternative designs

---

## Tool Reference by Research Path

### PATH 1: Patient Population Sizing
- `OpenTargets_get_disease_id_description_by_name` - Disease lookup
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` - Prevalence data
- `ClinVar_search_variants` - Biomarker mutation frequency
- `gnomad_search_variants` - Population allele frequencies
- `PubMed_search_articles` - Epidemiology literature
- `search_clinical_trials` - Enrollment feasibility from past trials

### PATH 2: Biomarker Prevalence & Testing
- `ClinVar_get_variant_details` - Variant pathogenicity
- `COSMIC_search_mutations` - Cancer-specific mutation frequencies
- `gnomad_get_variant` - Population genetics
- `PubMed_search_articles` - CDx test performance, guidelines

### PATH 3: Comparator Selection
- `drugbank_get_drug_basic_info_by_drug_name_or_id` - Drug info
- `drugbank_get_indications_by_drug_name_or_drugbank_id` - Approved indications
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Mechanism
- `FDA_OrangeBook_search_drug` - Generic availability
- `OpenFDA_get_approval_history` - Approval details
- `search_clinical_trials` - Historical control data

### PATH 4: Endpoint Selection
- `search_clinical_trials` - Precedent trials, endpoints used
- `PubMed_search_articles` - FDA acceptance history, endpoint validation
- `OpenFDA_get_approval_history` - Approved endpoints by indication

### PATH 5: Safety Endpoints & Monitoring
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Mechanism toxicity
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA black box warnings
- `FAERS_search_reports_by_drug_and_reaction` - Real-world adverse events
- `FAERS_count_reactions_by_drug_event` - AE frequency
- `FAERS_count_death_related_by_drug` - Serious outcomes
- `PubMed_search_articles` - DLT definitions, monitoring strategies

### PATH 6: Regulatory Pathway
- `OpenFDA_get_approval_history` - Precedent approvals
- `PubMed_search_articles` - Breakthrough designations, FDA guidance
- `search_clinical_trials` - Regulatory precedents (accelerated approval)

---

## Quick Start Example

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Example: EGFR+ NSCLC trial feasibility
# Step 1: Disease prevalence
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="non-small cell lung cancer"
)
prevalence = tu.tools.OpenTargets_get_diseases_phenotypes(
    efoId=disease_info['data']['id']
)

# Step 2: Biomarker prevalence
variants = tu.tools.ClinVar_search_variants(gene="EGFR", significance="pathogenic")

# Step 3: Precedent trials
trials = tu.tools.search_clinical_trials(
    condition="EGFR positive non-small cell lung cancer",
    status="completed", phase="2"
)

# Step 4: Standard of care comparator
soc = tu.tools.FDA_OrangeBook_search_drug(ingredient="osimertinib")

# Compile into feasibility report...
```

See `WORKFLOW_DETAILS.md` for the complete 6-path Python workflow and use case examples.

---

## Integration with Other Skills

- **tooluniverse-drug-research**: Investigate mechanism, preclinical data
- **tooluniverse-disease-research**: Deep dive on disease biology
- **tooluniverse-target-research**: Validate drug target, essentiality
- **tooluniverse-pharmacovigilance**: Post-market safety for comparator drugs
- **tooluniverse-precision-oncology**: Biomarker biology, resistance mechanisms

---

## Programmatic Access (Beyond Tools)

When ToolUniverse tools return limited trial metadata, use the ClinicalTrials.gov v2 API directly:

```python
import requests, pandas as pd

# Search with pagination (all lung cancer immunotherapy trials with results)
all_studies = []
token = None
while True:
    params = {"query.cond": "lung cancer", "query.intr": "immunotherapy",
              "filter.overallStatus": "COMPLETED", "filter.results": "WITH_RESULTS", "pageSize": 100}
    if token: params["pageToken"] = token
    resp = requests.get("https://clinicaltrials.gov/api/v2/studies", params=params).json()
    all_studies.extend(resp.get("studies", []))
    token = resp.get("nextPageToken")
    if not token: break

# Extract structured data
rows = []
for s in all_studies:
    proto = s.get("protocolSection", {})
    rows.append({
        "nctId": proto.get("identificationModule", {}).get("nctId"),
        "title": proto.get("identificationModule", {}).get("briefTitle"),
        "enrollment": proto.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
        "phase": proto.get("designModule", {}).get("phases", [None])[0] if proto.get("designModule", {}).get("phases") else None,
    })
df = pd.DataFrame(rows)

# FDA drug approval history
drug = "pembrolizumab"
fda = requests.get(f"https://api.fda.gov/drug/drugsfda.json?search=openfda.brand_name:{drug}&limit=10").json()
```

See `tooluniverse-data-wrangling` skill for pagination, error handling, and bulk download patterns.

---

## Reference Files

| File | Content |
|------|---------|
| `REPORT_TEMPLATE.md` | Full 14-section report template with fillable fields |
| `STUDY_DESIGN_PROCEDURES.md` | Detailed steps for each of the 6 research paths |
| `WORKFLOW_DETAILS.md` | Complete Python example workflow and 5 use case summaries |
| `BEST_PRACTICES.md` | Best practices, common pitfalls, output format requirements |
| `EXAMPLES.md` | Additional examples |
| `QUICK_START.md` | Quick start guide |

---

## Version Information

- **Version**: 1.0.0
- **Last Updated**: February 2026
- **Compatible with**: ToolUniverse 0.5+
- **Focus**: Phase 1/2 early clinical development
