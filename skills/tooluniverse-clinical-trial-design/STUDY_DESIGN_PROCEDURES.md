# Study Design Procedures

Detailed procedures for each of the 6 research paths in the clinical trial design feasibility assessment.

---

## PATH 1: Patient Population Sizing

### Steps
1. **Disease prevalence lookup**: Use `OpenTargets_get_disease_id_description_by_name` then `OpenTargets_get_diseases_phenotypes_by_target_ensembl`
2. **Biomarker prevalence**: Use `ClinVar_search_variants` (gene + significance) and `gnomAD_search_gene_variants`
3. **Literature epidemiology**: Use `PubMed_search_articles` for prevalence, incidence, geographic distribution
4. **Enrollment feasibility**: Use `search_clinical_trials` to find past trials and enrollment rates

### Enrollment Funnel Calculation
```
Base disease population (incidence/year)
x Biomarker prevalence (%)
x Eligibility factors (age, PS, prior therapy, organ function): ~60%
/ Competing trials factor
= Available patients/year
```

### Geographic Considerations
- Some biomarkers have ethnic variation (e.g., EGFR mutations: 15% Caucasian, 50% Asian)
- Consider international sites for biomarker-enriched populations

---

## PATH 2: Biomarker Prevalence & Testing

### Steps
1. **Variant pathogenicity**: `ClinVar_get_variant_details`
2. **Cancer-specific frequency**: `COSMIC_search_mutations`
3. **Population genetics**: `gnomAD_get_variant_details`
4. **CDx and testing**: `PubMed_search_articles` for FDA-approved companion diagnostics, NCCN guidelines

### Testing Logistics to Assess
- Pre-screening vs. screening approach
- Central lab vs. local testing
- Tissue vs. liquid biopsy (ctDNA)
- Turnaround time, cost, quality control

---

## PATH 3: Comparator Selection

### Steps
1. **Drug info**: `drugbank_get_drug_basic_info_by_drug_name_or_id`
2. **Indications**: `drugbank_get_indications_by_drug_name_or_drugbank_id`
3. **Pharmacology**: `drugbank_get_pharmacology_by_drug_name_or_drugbank_id`
4. **Generic availability**: `FDA_OrangeBook_search_drugs`
5. **Approval details**: `FDA_get_drug_approval_history`
6. **Historical controls**: `search_clinical_trials` for completed trials with SOC

### Design Options to Evaluate
- **Single-arm vs. historical SOC**: Faster, smaller N, but selection bias
- **Randomized vs. SOC**: Robust, regulatory preferred, but 2x enrollment
- **Non-inferiority**: When aiming for better safety with similar efficacy

---

## PATH 4: Endpoint Selection

### Steps
1. **Precedent trials**: `search_clinical_trials` (condition + phase + status=completed)
2. **FDA acceptance**: `PubMed_search_articles` for accelerated approval endpoints
3. **Approval history**: `FDA_get_drug_approval_history` for endpoints used in approvals

### Endpoint Hierarchy (Oncology)
| Endpoint | Evidence Grade | Use Case |
|----------|---------------|----------|
| Overall Survival (OS) | A | Phase 3, confirmatory |
| Progression-Free Survival (PFS) | A | Phase 2/3 |
| Objective Response Rate (ORR) | A | Phase 2, accelerated approval |
| Duration of Response (DoR) | B | Secondary in Phase 2 |
| Biomarker response | C | Exploratory |

### Statistical Considerations
- Expected effect size (from precedent trials)
- Null hypothesis (from SOC data)
- Sample size calculation (alpha=0.05, beta=0.20)
- Adaptive designs (Simon 2-stage, BOIN for dose escalation)

---

## PATH 5: Safety Endpoints & Monitoring

### Steps
1. **Mechanism-based toxicity**: `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` (class drug)
2. **FDA warnings**: `FDA_get_warnings_and_cautions_by_drug_name`
3. **Real-world AEs**: `FAERS_search_reports_by_drug_and_reaction`, `FAERS_count_reactions_by_drug_event`
4. **DLT definitions**: `PubMed_search_articles` for Phase 1 DLT in similar drug class

### Safety Monitoring Plan Components
- DLT definition and assessment period
- Organ-specific monitoring (hepatic, cardiac, renal)
- Safety Monitoring Committee composition and review frequency
- Stopping rules

### Dose Escalation Designs
- **3+3**: Simple, standard, conservative
- **BOIN**: Bayesian, more efficient, adaptive
- **mTPI**: Model-based, flexible

---

## PATH 6: Regulatory Pathway

### Steps
1. **Breakthrough designations**: `PubMed_search_articles` for FDA breakthrough in indication
2. **Orphan drug eligibility**: Calculate US prevalence (<200,000 total)
3. **FDA guidance**: `PubMed_search_articles` for relevant FDA guidance documents
4. **Approval precedents**: `FDA_get_drug_approval_history` for similar drugs

### FDA Pathway Options
| Pathway | Criteria | Benefits |
|---------|----------|----------|
| 505(b)(1) | New molecular entity | Full exclusivity |
| 505(b)(2) | Relies on published safety data | Faster, smaller safety package |
| Breakthrough Therapy | Substantial improvement on serious condition | Rolling review, frequent FDA meetings |
| Orphan Drug | Prevalence <200,000 in US | 7-year exclusivity, tax credits, fee waivers |
| Fast Track | Serious condition, unmet need | Rolling review |
| Accelerated Approval | Surrogate endpoint reasonably likely to predict benefit | Earlier approval, confirmatory trial required |

### Pre-IND Meeting Topics
1. Primary endpoint acceptability
2. Biomarker test qualification (CDx plan)
3. Comparator arm (single-arm acceptable?)
4. Pediatric study plan waiver
5. Safety monitoring plan

### IND Timeline
| Milestone | Month | Deliverable |
|-----------|-------|-------------|
| Pre-IND meeting request | -4 | Briefing package |
| Pre-IND meeting | -3 | FDA feedback |
| IND submission | 0 | Complete IND package |
| FDA 30-day review | 1 | Clinical hold or proceed |
| First patient dosed | 1-2 | After IND clearance |
