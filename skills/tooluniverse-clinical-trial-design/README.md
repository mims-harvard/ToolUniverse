# Clinical Trial Design Feasibility Skill

Strategic clinical trial design feasibility assessment for early-phase trials (Phase 1/2 emphasis).

## What This Skill Does

Systematically evaluates clinical trial feasibility across 6 research dimensions:
1. **Patient Population Sizing** - Prevalence, biomarker rates, enrollment projections
2. **Biomarker Strategy** - Testing availability, turnaround time, CDx landscape
3. **Comparator Selection** - SOC analysis, historical controls, single-arm vs. randomized
4. **Endpoint Selection** - Regulatory precedents, measurement feasibility
5. **Safety Monitoring** - Mechanism-based toxicities, monitoring plans, DLT definitions
6. **Regulatory Pathway** - 505(b)(1), breakthrough therapy, orphan designation

**Output**: Comprehensive feasibility report with quantitative feasibility score (0-100), enrollment timelines, and go/no-go recommendations.

## When to Use This Skill

Use this skill when you need to:
- Plan Phase 1/2 trials (early development focus)
- Assess enrollment feasibility for biomarker-selected trials
- Design basket or umbrella trials
- Evaluate endpoint strategies (ORR, PFS, biomarker endpoints)
- Determine regulatory pathways (breakthrough, orphan, accelerated approval)
- Calculate sample sizes and enrollment timelines
- Create safety monitoring plans
- Compare trial design alternatives (single-arm vs. randomized)

**Trigger phrases**: "clinical trial design", "trial feasibility", "enrollment projections", "biomarker trial", "Phase 1/2 design", "basket trial", "endpoint selection", "regulatory pathway"

## Quick Start

### Basic Feasibility Assessment

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Example: Assess EGFR+ NSCLC trial feasibility
indication = "EGFR L858R+ non-small cell lung cancer"
biomarker = "EGFR L858R"

# 1. Disease prevalence
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="non-small cell lung cancer"
)

# 2. Biomarker prevalence
variants = tu.tools.ClinVar_search_variants(
    gene="EGFR",
    significance="pathogenic"
)

# 3. Precedent trials
trials = tu.tools.search_clinical_trials(
    condition="EGFR positive non-small cell lung cancer",
    status="completed",
    phase="2"
)

# 4. Standard of care
soc_drug = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    drug_name_or_drugbank_id="osimertinib"
)

# Compile into feasibility report...
```

## Files in This Skill

### SKILL.md (Main Instructions)
- **Report-first approach** - Create trial_feasibility_report.md FIRST
- **6 research paths** - Systematic data collection workflow
- **14-section report structure** - Executive summary to final recommendations
- **Evidence grading** (A/B/C/D) - Grade all regulatory precedents
- **Feasibility scoring** (0-100) - Quantitative assessment across 5 dimensions
- **Complete example workflow** - Full EGFR+ NSCLC Phase 1/2 trial

### EXAMPLES.md (5 Worked Examples)
1. **Biomarker-Selected Oncology Trial** - EGFR L858R+ NSCLC (Score: 82/100, HIGH feasibility)
2. **Rare Disease Trial** - Niemann-Pick Type C (Score: 58/100, MODERATE-LOW, slow enrollment)
3. **Superiority Trial vs. SOC** - PD-1 inhibitor vs. pembrolizumab (Score: 87/100, HIGH)
4. **Non-Inferiority Trial** - Oral anticoagulant (Score: 90/100, but large N, expensive)
5. **Basket Trial** - NTRK fusion+ solid tumors (Score: 68/100, MODERATE, ultra-rare)

### README.md (This File)
Quick start guide and overview

## Key Features

### Quantitative Feasibility Score (0-100)
Weighted composite across 5 dimensions:
- **Patient Availability** (30%): Population size, biomarker prevalence, enrollment timeline
- **Endpoint Precedent** (25%): FDA acceptance, measurement feasibility
- **Regulatory Clarity** (20%): Pathway defined, precedent approvals
- **Comparator Feasibility** (15%): SOC data, single-arm vs. randomized
- **Safety Monitoring** (10%): Known toxicities, monitoring plan

**Interpretation**:
- **≥75**: HIGH feasibility - Recommend proceed
- **50-74**: MODERATE feasibility - Additional validation needed
- **<50**: LOW feasibility - Significant de-risking required

### Evidence Grading System
| Grade | Symbol | Criteria | Example |
|-------|--------|----------|---------|
| **A** | ★★★ | Regulatory acceptance, multiple precedents | FDA-approved endpoint in indication |
| **B** | ★★☆ | Clinical validation, single precedent | Phase 3 trial in related indication |
| **C** | ★☆☆ | Preclinical or exploratory | Phase 1 use, biomarker validation |
| **D** | ☆☆☆ | Proposed, no validation | Novel endpoint, no precedent |

### Report Structure (14 Sections)
1. Executive Summary (with feasibility score)
2. Disease Background
3. Patient Population Analysis (with eligibility funnel)
4. Biomarker Strategy
5. Endpoint Selection & Justification
6. Comparator Analysis
7. Safety Endpoints & Monitoring Plan
8. Study Design Recommendations
9. Enrollment & Site Strategy
10. Regulatory Pathway
11. Budget & Resource Considerations
12. Risk Assessment
13. Success Criteria & Go/No-Go Decision
14. Recommendations & Next Steps

## Research Paths Overview

### PATH 1: Patient Population Sizing
**Objective**: Calculate eligible patient pool and enrollment timeline

**Tools**:
- `OpenTargets_get_disease_id_description_by_name` - Disease lookup
- `OpenTargets_get_diseases_phenotypes` - Prevalence data
- `ClinVar_search_variants` - Biomarker mutation frequency
- `gnomAD_search_gene_variants` - Population genetics
- `PubMed_search_articles` - Epidemiology literature

**Outputs**:
- Annual eligible patients (with eligibility funnel)
- Sites required
- Enrollment timeline (months)

### PATH 2: Biomarker Strategy
**Objective**: Assess biomarker testing feasibility and CDx landscape

**Tools**:
- `ClinVar_get_variant_details` - Variant pathogenicity
- `COSMIC_search_mutations` - Cancer mutation frequencies
- `PubMed_search_articles` - CDx tests, testing guidelines

**Outputs**:
- Biomarker prevalence (by geography, ethnicity)
- Testing methods (NGS, IHC, liquid biopsy)
- Turnaround time and cost

### PATH 3: Comparator Selection
**Objective**: Identify standard of care and determine design (single-arm vs. randomized)

**Tools**:
- `drugbank_get_drug_basic_info_by_drug_name_or_id` - Drug information
- `drugbank_get_indications_by_drug_name_or_drugbank_id` - Approved indications
- `FDA_OrangeBook_search_drugs` - Generic availability
- `search_clinical_trials` - Historical control data

**Outputs**:
- SOC drug(s) and efficacy
- Single-arm vs. randomized recommendation
- Comparator sourcing plan

### PATH 4: Endpoint Selection
**Objective**: Select primary endpoint with regulatory precedent

**Tools**:
- `search_clinical_trials` - Precedent trials, endpoints used
- `FDA_get_drug_approval_history` - FDA acceptance by indication
- `PubMed_search_articles` - Endpoint validation studies

**Outputs**:
- Primary endpoint recommendation (ORR, PFS, DLT, biomarker)
- Evidence grade (A/B/C/D)
- Sample size calculation

### PATH 5: Safety Monitoring
**Objective**: Design mechanism-based safety monitoring plan

**Tools**:
- `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` - Mechanism toxicity
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA warnings
- `FAERS_search_reports_by_drug_and_reaction` - Real-world AEs
- `FAERS_count_reactions_by_drug_event` - AE frequency

**Outputs**:
- DLT definition (Phase 1)
- Mechanism-based toxicities
- Monitoring schedule (labs, imaging, ECG)
- Stopping rules

### PATH 6: Regulatory Pathway
**Objective**: Determine regulatory strategy and potential designations

**Tools**:
- `FDA_get_drug_approval_history` - Precedent approvals
- `PubMed_search_articles` - Breakthrough, orphan designations

**Outputs**:
- Regulatory pathway (505(b)(1), 505(b)(2))
- Designation opportunities (breakthrough, fast track, orphan)
- Pre-IND meeting topics
- IND timeline

## Trial Design Types Supported

### 1. Biomarker-Selected Oncology
- **Example**: EGFR L858R+ NSCLC
- **Design**: Single-arm Phase 2, ORR primary
- **Feasibility**: HIGH (clear biomarker, precedents)
- **Timeline**: 12-18 months

### 2. Rare Disease
- **Example**: Niemann-Pick Type C
- **Design**: Single-arm vs. natural history
- **Feasibility**: MODERATE-LOW (slow enrollment)
- **Timeline**: 36-48 months
- **Special Considerations**: Orphan drug, patient registries

### 3. Superiority Trial
- **Example**: Novel PD-1 vs. pembrolizumab
- **Design**: Randomized 1:1, ORR primary
- **Feasibility**: HIGH (large population)
- **Timeline**: 18-24 months

### 4. Non-Inferiority Trial
- **Example**: Novel anticoagulant vs. apixaban
- **Design**: Randomized, double-blind, event-driven
- **Feasibility**: HIGH but expensive
- **Sample Size**: Large (N=5,000+)

### 5. Basket Trial
- **Example**: NTRK fusion+ solid tumors
- **Design**: Single-arm, multiple histologies
- **Feasibility**: MODERATE (ultra-rare, broad screening)
- **Timeline**: 36-48 months

## Common Workflows

### Workflow 1: Quick Feasibility Check (1-2 hours)
1. Disease prevalence (OpenTargets, PubMed)
2. Biomarker frequency (ClinVar, gnomAD)
3. Precedent trials (search_clinical_trials)
4. Quick feasibility score
5. Go/no-go recommendation

**Use Case**: Executive decision-making, portfolio prioritization

### Workflow 2: Comprehensive Feasibility Report (1-2 days)
1. Execute all 6 research paths
2. Compile 14-section report
3. Calculate enrollment funnel
4. Regulatory pathway analysis
5. Risk assessment
6. Budget estimate

**Use Case**: Protocol development, investor presentations, FDA pre-IND prep

### Workflow 3: Design Comparison (0.5-1 day)
1. Assess 2-3 alternative designs (single-arm vs. randomized, different endpoints)
2. Score each design
3. Pros/cons analysis
4. Recommendation

**Use Case**: Study team decision-making, choosing between design options

## Performance Tips

1. **Enable caching**: `tu = ToolUniverse(use_cache=True)` - Critical for repeated queries
2. **Parallel research paths**: Run PATH 1-6 concurrently, not sequentially
3. **Use English terms**: Always query tools in English, even if user asks in another language
4. **Cross-validate prevalence**: Check ClinVar AND gnomAD AND literature for biomarkers
5. **Report-first**: Create report structure FIRST, populate progressively
6. **Grade evidence**: Every regulatory precedent needs evidence grade (A/B/C/D)

## Prerequisites

### Installation
```bash
pip install tooluniverse
```

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."  # For LLM-based tool search
export NCBI_API_KEY="..."       # For higher PubMed rate limits (optional)
```

### Recommended Knowledge
- Clinical trial design basics (Phase 1/2/3, endpoints)
- FDA regulatory pathways (IND, NDA, accelerated approval)
- Biomarker concepts (CDx, NGS, prevalence)
- Statistical concepts (sample size, power, non-inferiority margin)

## Integration with Other Skills

Works well with:
- **tooluniverse-drug-research** - Drug mechanism, preclinical data
- **tooluniverse-disease-research** - Disease biology, natural history
- **tooluniverse-target-research** - Target validation, druggability
- **tooluniverse-precision-oncology** - Biomarker biology, resistance
- **tooluniverse-pharmacovigilance** - Post-market safety data

## Validation Checklist

Before recommending trial proceed:

**Patient Population**:
- [ ] Prevalence data validated across ≥2 sources
- [ ] Biomarker frequency confirmed (ClinVar, literature)
- [ ] Eligibility criteria funnel calculated
- [ ] Enrollment timeline realistic (<24 months for Phase 2)

**Endpoints**:
- [ ] Primary endpoint has regulatory precedent (evidence grade A/B)
- [ ] Measurement method standardized (RECIST, CTCAE, etc.)
- [ ] Sample size calculation provided

**Regulatory**:
- [ ] Pathway identified (505(b)(1), breakthrough, orphan)
- [ ] Pre-IND meeting topics defined
- [ ] Precedent approvals cited (drug names, years, NCT numbers)

**Safety**:
- [ ] Mechanism-based toxicities identified
- [ ] Monitoring schedule defined (labs, imaging frequency)
- [ ] DLT definition provided (Phase 1)

**Feasibility Score**:
- [ ] All 5 dimensions scored (patient, endpoint, regulatory, comparator, safety)
- [ ] Rationale provided for each score
- [ ] Overall score calculated (weighted average)

## Success Metrics

**HIGH Feasibility (≥75)**:
- Patient availability strong (enrollment <18 months)
- Endpoint has FDA precedent (grade A/B)
- Clear regulatory path (precedents exist)
- Comparator data robust (published trials)
- Safety monitoring established (class effects known)

**MODERATE Feasibility (50-74)**:
- Patient availability moderate (enrollment 18-36 months)
- Endpoint used in Phase 2 but not pivotal (grade B/C)
- Regulatory path defined but needs FDA input
- Comparator available but limited data
- Safety monitoring feasible but novel mechanism

**LOW Feasibility (<50)**:
- Patient availability poor (enrollment >36 months or infeasible)
- Endpoint novel, no precedent (grade D)
- Regulatory path unclear
- No comparator or historical data
- Safety unknowns, high risk

## Limitations

1. **Data Availability**: Not all diseases/biomarkers have published prevalence data
2. **Geographic Variation**: Prevalence estimates may vary by region (US vs. Asia)
3. **Enrollment Projections**: Actual enrollment depends on site performance, competition
4. **Regulatory Landscape**: FDA policies evolve; precedents are guidance, not guarantees
5. **Budget Estimates**: Rough order-of-magnitude only; detailed budgets need finance input

**Always**: Validate feasibility findings with experienced clinical development team

## Example Outputs

### Example 1: EGFR+ NSCLC (HIGH Feasibility)
- **Score**: 82/100
- **Recommendation**: RECOMMEND PROCEED
- **Timeline**: 24 months (enrollment + primary analysis)
- **Key Strengths**: Large patient pool, ORR precedent, clear regulatory path

### Example 2: Niemann-Pick Type C (MODERATE-LOW Feasibility)
- **Score**: 58/100
- **Recommendation**: CONDITIONAL GO (require registry partnership)
- **Timeline**: 48-60 months
- **Key Challenge**: Ultra-rare (36+ months enrollment)

### Example 3: NTRK Basket (MODERATE Feasibility)
- **Score**: 68/100
- **Recommendation**: CONDITIONAL GO (require CGP partnership)
- **Timeline**: 48 months (screening challenge)
- **Key Challenge**: Ultra-rare biomarker (need broad NGS screening)

## Citation

When using this skill, cite:
- **ToolUniverse**: Gao S, Ding J, Zitnik M. ToolUniverse: Developing multi-tool AI systems with 750+ biomedical tools. arXiv:2024.xxxxx
- **Databases**: OpenTargets, ClinVar, gnomAD, ClinicalTrials.gov, FDA, FAERS, DrugBank
- **Primary literature**: Cite specific papers used for prevalence, endpoints

## Support

- **ToolUniverse Docs**: https://zitniklab.hms.harvard.edu/ToolUniverse/
- **Slack Community**: https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ
- **GitHub**: https://github.com/mims-harvard/ToolUniverse
- **Issues**: https://github.com/mims-harvard/ToolUniverse/issues

## Version

- **Version**: 1.0.0
- **Last Updated**: February 2026
- **Compatible with**: ToolUniverse 0.5+
- **Focus**: Early-phase trials (Phase 1/2 emphasis)

## License

This skill follows ToolUniverse licensing. Check individual database terms of use for commercial clinical trial applications.

---

## Quick Reference: Feasibility Score Calculation

```python
# Feasibility Score Formula
dimensions = {
    'patient_availability': {'weight': 0.30, 'raw_score': 0-10},
    'endpoint_precedent': {'weight': 0.25, 'raw_score': 0-10},
    'regulatory_clarity': {'weight': 0.20, 'raw_score': 0-10},
    'comparator_feasibility': {'weight': 0.15, 'raw_score': 0-10},
    'safety_monitoring': {'weight': 0.10, 'raw_score': 0-10}
}

# Total feasibility score (0-100)
feasibility_score = sum(d['weight'] * d['raw_score'] * 10 for d in dimensions.values())

# Interpretation
if feasibility_score >= 75:
    recommendation = "RECOMMEND PROCEED"
elif feasibility_score >= 50:
    recommendation = "CONDITIONAL GO - Additional validation needed"
else:
    recommendation = "DO NOT RECOMMEND - Significant de-risking required"
```

## Quick Reference: Evidence Grading

| Grade | Regulatory | Clinical | Preclinical | Proposed |
|-------|-----------|----------|-------------|----------|
| **A** ★★★ | FDA-approved endpoint in indication | Multiple Phase 3 precedents | - | - |
| **B** ★★☆ | Used in Phase 3, not approved | Single Phase 3 or multiple Phase 2 | - | - |
| **C** ★☆☆ | Phase 1/2 only | Case series | Validated in animal models | - |
| **D** ☆☆☆ | No precedent | Anecdotal | Cell line data | Computational only |

---

**Ready to assess your clinical trial feasibility? See SKILL.md for detailed instructions and EXAMPLES.md for 5 complete worked examples.**
