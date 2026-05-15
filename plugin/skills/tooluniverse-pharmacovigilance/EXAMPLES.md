# Pharmacovigilance Safety Analyzer - Examples

## Example 1: Single Drug Safety Profile

### User Query
"What are the safety concerns for metformin? I'm considering it for a patient with mild renal impairment."

### Expected Output

```markdown
# Pharmacovigilance Safety Report: Metformin

**Generated**: 2026-02-04 | **Query**: Metformin safety with renal impairment

---

## Executive Summary

Metformin is generally well-tolerated but carries a **boxed warning for lactic acidosis** (⚠️⚠️⚠️), which is rare but potentially fatal. The risk increases significantly with renal impairment. For patients with mild renal impairment (eGFR 45-60), metformin can be used with dose adjustment and monitoring. **Contraindicated at eGFR <30**.

**Key Safety Signals**:
1. **Lactic acidosis** (PRR 15.2) - Boxed warning, 156 fatalities in FAERS
2. **Vitamin B12 deficiency** (PRR 8.4) - Annual monitoring recommended
3. **GI intolerance** (PRR 2.3) - Common, usually manageable

**Recommendation for this patient**: May use metformin if eGFR ≥45. Check baseline renal function, start low dose, monitor eGFR and B12 annually.

---

## 1. Drug Identification

| Property | Value |
|----------|-------|
| **Generic Name** | Metformin hydrochloride |
| **Brand Names** | Glucophage, Glucophage XR, Fortamet, Glumetza |
| **Drug Class** | Biguanide antidiabetic |
| **ChEMBL ID** | CHEMBL1431 |
| **Mechanism** | AMPK activation, decreased hepatic gluconeogenesis |
| **First Approved** | 1994 (US), 1957 (Europe) |
| **Indications** | Type 2 diabetes mellitus |

*Source: DailyMed via `DailyMed_search_spls`, ChEMBL*

---

## 2. Adverse Event Profile (FAERS)

**Data Period**: Q1 2020 - Q4 2025
**Total Reports**: 128,456

### 2.1 Top Adverse Events by Frequency

| Rank | Adverse Event | Reports | PRR | 95% CI | Serious (%) | Fatal |
|------|---------------|---------|-----|--------|-------------|-------|
| 1 | Diarrhea | 23,412 | 2.3 | 2.2-2.4 | 8% | 12 |
| 2 | Nausea | 18,234 | 1.8 | 1.7-1.9 | 5% | 2 |
| 3 | Abdominal pain | 12,456 | 1.5 | 1.4-1.6 | 12% | 4 |
| 4 | Vomiting | 8,923 | 1.6 | 1.5-1.7 | 9% | 3 |
| 5 | Decreased appetite | 6,234 | 2.1 | 2.0-2.3 | 4% | 1 |
| 6 | Lactic acidosis | 3,892 | 15.2 | 14.2-16.3 | 89% | 156 ⚠️ |
| 7 | Acute kidney injury | 2,341 | 4.2 | 3.8-4.6 | 78% | 34 |
| 8 | Vitamin B12 deficiency | 1,892 | 8.4 | 7.8-9.1 | 12% | 0 |
| 9 | Hypoglycemia | 1,567 | 1.2 | 1.1-1.3 | 23% | 3 |
| 10 | Metallic taste | 1,234 | 3.2 | 2.9-3.6 | 2% | 0 |

### 2.2 Serious Adverse Events Analysis

| Adverse Event | Serious Reports | Fatal | PRR | Signal Tier |
|---------------|-----------------|-------|-----|-------------|
| **Lactic acidosis** | 3,464 | 156 | 15.2 | ⚠️⚠️⚠️ T1 |
| Acute kidney injury | 1,826 | 34 | 4.2 | ⚠️⚠️ T2 |
| Hepatotoxicity | 456 | 8 | 2.8 | ⚠️ T3 |
| Pancreatitis | 234 | 4 | 2.1 | ⚠️ T3 |

### 2.3 Lactic Acidosis Deep Dive ⚠️⚠️⚠️

| Characteristic | Finding |
|----------------|---------|
| Total cases | 3,892 |
| Serious | 3,464 (89%) |
| Fatal | 156 (4.0% case fatality) |
| Median age | 68 years |
| Common comorbidities | Renal impairment (67%), CHF (34%), sepsis (23%) |
| Concurrent meds | Contrast agents (12%), NSAIDs (28%) |

**Risk Factors Identified in Reports**:
1. Renal impairment (eGFR <45) - 67% of cases
2. Acute illness/dehydration - 45% of cases
3. Heart failure - 34% of cases
4. Age >65 - 72% of cases
5. Contrast media exposure - 12% of cases

*Source: FAERS via `FAERS_count_reactions_by_drug_event` (Q1 2020 - Q4 2025)*

---

## 3. FDA Label Safety Information

### 3.1 Boxed Warning ⬛

> **LACTIC ACIDOSIS**
> 
> Postmarketing cases of metformin-associated lactic acidosis have resulted in death, hypothermia, hypotension, and resistant bradyarrhythmias. The onset is often subtle, accompanied only by nonspecific symptoms such as malaise, myalgias, respiratory distress, somnolence, and abdominal pain.
>
> Metformin-associated lactic acidosis was characterized by elevated blood lactate levels (>5 mmol/L), anion gap acidosis, an increased lactate/pyruvate ratio, and metformin plasma levels generally >5 mcg/mL.
>
> Risk factors include renal impairment, concomitant use of certain drugs, age ≥65, radiological studies with contrast, surgery, hypoxic states, excessive alcohol intake, and hepatic impairment.

### 3.2 Contraindications 🔴

| Contraindication | Rationale | Action |
|------------------|-----------|--------|
| **eGFR <30 mL/min/1.73m²** | High lactic acidosis risk | Do not initiate |
| Acute/chronic metabolic acidosis | May worsen | Discontinue |
| Hypersensitivity to metformin | Allergic reaction | Contraindicated |

### 3.3 Renal Dosing Guidelines

| eGFR (mL/min/1.73m²) | Recommendation |
|----------------------|----------------|
| ≥60 | No dose adjustment |
| 45-60 | May continue, monitor renal function |
| 30-45 | Reduce dose to 50%, monitor closely |
| <30 | **Contraindicated** |

### 3.4 Key Warnings and Precautions 🟠

| Warning | Clinical Action |
|---------|-----------------|
| Vitamin B12 deficiency | Monitor annually; supplement if deficient |
| Radiologic contrast | Hold 48h before and after |
| Surgery/procedures | Hold day of surgery |
| Hypoglycemia with insulin | May need insulin dose reduction |
| Excessive alcohol | Avoid; potentiates lactic acidosis |

*Source: DailyMed via `DailyMed_search_spls`*

---

## 4. Pharmacogenomic Risk Factors

### 4.1 Clinically Relevant Variants

| Gene | Variant | rs ID | Effect | Evidence | Recommendation |
|------|---------|-------|--------|----------|----------------|
| SLC22A1 (OCT1) | *2, *3, *4, *5 | Multiple | Reduced uptake | 2A | May have reduced response |
| SLC22A1 | rs628031 | A>G | Reduced function | 2A | Consider higher dose |
| ATM | rs11212617 | C>A | Enhanced response | 3 | Standard dosing |
| SLC47A1 (MATE1) | rs2289669 | G>A | Reduced clearance | 3 | Monitor for toxicity |

### 4.2 Clinical Implications

**OCT1 (SLC22A1) Poor Transporters**:
- Prevalence: ~9% of Caucasians, ~2% of Asians
- Effect: Reduced hepatic metformin uptake
- Clinical: May have decreased glucose-lowering efficacy
- Action: Consider higher doses or alternative if poor response

**Note**: No CPIC or DPWG guidelines for metformin PGx testing at this time.

*Source: PharmGKB via `PharmGKB_search_drugs`*

---

## 5. Clinical Trial Safety Data

### 5.1 Landmark Trial Summary

| Trial | N | Duration | Serious AE (Met) | Serious AE (Control) | Deaths |
|-------|---|----------|------------------|---------------------|--------|
| UKPDS | 1,704 | 10.7 yr | 12.3% | 14.1% (Conventional) | 8.2% vs 9.1% |
| DPP | 1,073 | 2.8 yr | 4.2% | 3.8% (Placebo) | 0.1% vs 0.1% |

### 5.2 Common Adverse Events in Trials

| Adverse Event | Metformin (%) | Placebo (%) | NNH |
|---------------|---------------|-------------|-----|
| Diarrhea | 53% | 12% | 2.4 |
| Nausea/vomiting | 26% | 8% | 5.6 |
| Flatulence | 12% | 6% | 17 |
| Asthenia | 9% | 6% | 33 |
| Dyspepsia | 7% | 4% | 33 |

### 5.3 Lactic Acidosis in Trials

In controlled trials, **zero cases** of lactic acidosis were observed with metformin. The boxed warning is based on postmarketing data, particularly from older biguanides (phenformin) and patients with contraindications.

*Source: Published trial results, DailyMed label*

---

## 6. Prioritized Safety Signals

### 6.1 Critical Signals (⚠️⚠️⚠️) - Immediate Attention

| Signal | PRR | Fatal | Action Required |
|--------|-----|-------|-----------------|
| Lactic acidosis | 15.2 | 156 | Boxed warning; check renal function |

### 6.2 Moderate Signals (⚠️⚠️) - Monitor

| Signal | PRR | Serious | Monitoring |
|--------|-----|---------|------------|
| Acute kidney injury | 4.2 | 1,826 | Monitor eGFR, especially if dehydrated |
| Vitamin B12 deficiency | 8.4 | 227 | Annual B12 levels |

### 6.3 Known/Expected (ℹ️) - Manage Clinically

| Signal | PRR | Management Strategy |
|--------|-----|---------------------|
| Diarrhea | 2.3 | Start low (500mg), titrate slowly, take with food |
| Nausea | 1.8 | Temporary; improves with time |
| Metallic taste | 3.2 | Usually transient |

---

## 7. Risk-Benefit Assessment

### For This Patient (Mild Renal Impairment)

| Factor | Assessment |
|--------|------------|
| **Benefits** | HbA1c reduction 1-1.5%, weight neutral, CV benefit (UKPDS), low cost |
| **Risks** | Lactic acidosis (elevated but still rare), GI intolerance |
| **eGFR Consideration** | If 45-60: acceptable with monitoring; if <45: reduce dose 50% |

### Risk Level: **MODERATE** (in renal impairment context)

**Recommendation**: Metformin is appropriate if:
- eGFR ≥45 mL/min/1.73m²
- No other contraindications (acidosis, contrast exposure, acute illness)
- Patient educated on symptoms of lactic acidosis
- Regular renal function monitoring

---

## 8. Clinical Recommendations

### 8.1 Pre-Treatment Checklist

- [ ] Check eGFR (must be ≥30, ideally ≥45)
- [ ] Review for contraindications (CHF NYHA III-IV, hepatic disease)
- [ ] Check baseline vitamin B12
- [ ] Review concurrent medications (contrast, nephrotoxins)
- [ ] Assess alcohol intake

### 8.2 Monitoring Recommendations

| Parameter | Frequency | Action Threshold |
|-----------|-----------|------------------|
| eGFR | Every 3-6 months | Reduce dose if <45, stop if <30 |
| Vitamin B12 | Annually | Supplement if <300 pg/mL |
| LFTs | Baseline | Discontinue if hepatic disease |
| Lactate | If symptomatic | >5 mmol/L: stop metformin |

### 8.3 Patient Counseling Points

1. **Take with food** to reduce GI side effects
2. **Stay hydrated** - dehydration increases lactic acidosis risk
3. **Hold before procedures** with contrast or surgery
4. **Seek care immediately** for unexplained muscle pain, weakness, difficulty breathing, stomach pain
5. **Limit alcohol** - increases lactic acidosis risk
6. **Report illness** - may need temporary discontinuation during acute illness

---

## 9. Data Gaps & Limitations

| Gap | Impact | Mitigation |
|-----|--------|------------|
| FAERS underreporting | True AE rates may differ | Use PRR (relative measure) |
| Confounding in FAERS | Comorbidities affect risk | Note risk factors |
| PGx not routine | OCT1 status unknown | Monitor response clinically |

---

## 10. Data Sources

| Tool | Query | Data Retrieved |
|------|-------|----------------|
| FAERS_count_reactions_by_drug_event | metformin | AE counts, PRR |
| DailyMed_search_spls | metformin | Drug identification |
| DailyMed_get_spl_by_set_id | [setid] | Label warnings |
| PharmGKB_search_drug | metformin | PGx variants |
| search_clinical_trials | metformin phase 3 | Trial safety data |
```

---

## Example 2: Drug Comparison

### User Query
"Compare the safety of DOACs - apixaban vs rivaroxaban vs dabigatran for AFib"

### Expected Output (Key Sections)

```markdown
# Pharmacovigilance Comparison: DOACs for Atrial Fibrillation

**Generated**: 2026-02-04

---

## Executive Summary

All three DOACs have similar overall safety profiles but differ in specific risks:

| Drug | Major Bleeding PRR | GI Bleeding | Reversal Agent |
|------|-------------------|-------------|----------------|
| **Apixaban** | 2.1 (Lowest) | Lower | Andexanet alfa |
| **Rivaroxaban** | 2.8 | Higher ⚠️ | Andexanet alfa |
| **Dabigatran** | 2.4 | Higher ⚠️ | Idarucizumab ✓ |

**Recommendation**: Apixaban may have the most favorable bleeding profile. All require renal function monitoring.

---

## Comparative Adverse Event Analysis

### Bleeding Events (FAERS)

| Event | Apixaban PRR | Rivaroxaban PRR | Dabigatran PRR |
|-------|--------------|-----------------|----------------|
| Major bleeding | 2.1 | 2.8 | 2.4 |
| GI bleeding | 2.3 | 3.8 ⚠️ | 3.5 ⚠️ |
| Intracranial bleeding | 1.8 | 2.1 | 1.9 |
| Epistaxis | 3.2 | 3.8 | 2.9 |

### GI Tolerability

| Event | Apixaban | Rivaroxaban | Dabigatran |
|-------|----------|-------------|------------|
| Dyspepsia | PRR 1.2 | PRR 1.5 | PRR 4.2 ⚠️ |
| Nausea | PRR 1.1 | PRR 1.3 | PRR 2.8 |

**Note**: Dabigatran has higher GI intolerance due to tartaric acid formulation.

---

## Renal Considerations

| Drug | Renal Clearance | CrCl 30-50 | CrCl 15-30 | CrCl <15 |
|------|-----------------|------------|------------|----------|
| Apixaban | 27% | Dose reduce | Dose reduce | Avoid |
| Rivaroxaban | 36% | Dose reduce | Avoid | Avoid |
| Dabigatran | 80% | Dose reduce | Avoid | Avoid |

**For renal impairment**: Apixaban has least renal dependence.

---

## Summary Recommendation

| Patient Profile | Preferred DOAC | Rationale |
|-----------------|----------------|-----------|
| General AFib | Apixaban | Lowest bleeding signal |
| High GI bleeding risk | Apixaban | Lower GI bleeding PRR |
| High reversal need | Dabigatran | Idarucizumab available |
| Renal impairment | Apixaban | Least renal clearance |
| GI intolerance | Apixaban/Rivaroxaban | Dabigatran has dyspepsia |
```

---

## Example 3: Emerging Safety Signal

### User Query
"I heard there might be new safety concerns with semaglutide. What does the data show?"

### Expected Output (Key Sections)

```markdown
# Pharmacovigilance Safety Report: Semaglutide

**Generated**: 2026-02-04

---

## Executive Summary

Semaglutide (Ozempic, Wegovy, Rybelsus) has seen a **500% increase in FAERS reports** since 2021 due to expanded use. Most signals are **known class effects** (GI, pancreatitis). Recent signals under evaluation:

| Signal | PRR | Status | Evidence |
|--------|-----|--------|----------|
| Thyroid C-cell tumors | 3.8 | Boxed warning | Animal data; human uncertain |
| Pancreatitis | 5.2 | Known risk | Monitor for symptoms |
| **Gastroparesis** | 4.1 | **Emerging** ⚠️ | Increasing reports |
| **Ileus** | 3.2 | **Emerging** ⚠️ | FDA reviewing |
| Suicidal ideation | 1.4 | Under review | EMA/FDA investigating |

**Note**: Disproportionate media attention may be driving reporting bias for some AEs.

---

## Recent FDA Safety Communications

| Date | Communication | Topic |
|------|---------------|-------|
| 2023-09 | Drug Safety Communication | Suicidal ideation - under review |
| 2024-01 | Label Update | Ileus added to warnings |
| 2024-06 | Safety Review | Gastroparesis ongoing evaluation |

---

## Emerging Signal: Gastroparesis

| Metric | Finding |
|--------|---------|
| FAERS reports | 2,341 (2023-2025) |
| PRR | 4.1 (95% CI: 3.8-4.5) |
| Serious cases | 1,892 (81%) |
| Required hospitalization | 1,234 (53%) |
| Trend | Increasing since 2022 |

**Mechanism**: GLP-1 agonists delay gastric emptying. At high doses (Wegovy), this may cause severe gastroparesis in susceptible individuals.

**Risk factors identified**:
- Pre-existing gastroparesis
- Diabetic autonomic neuropathy
- Concurrent opioid use

---

## Signal vs Noise Assessment

| Signal | Likely Real? | Rationale |
|--------|--------------|-----------|
| GI effects | ✓ Yes | Mechanism-based, dose-dependent |
| Pancreatitis | ✓ Yes | Class effect, monitor |
| Gastroparesis | ✓ Probable | Increasing, mechanism plausible |
| Suicidal ideation | ? Uncertain | No clear mechanism, confounders |
| Thyroid cancer | ? Uncertain | Animal data only, long latency |

---

## Clinical Recommendations

### For New Prescribers
1. **Screen for GI conditions** before starting
2. **Start low, go slow** - titrate per label
3. **Counsel on GI symptoms** - most are transient
4. **Monitor for pancreatitis symptoms**
5. **Report AEs to FDA MedWatch**

### For Current Users
1. **Continue if tolerating well**
2. **Report persistent vomiting** (possible gastroparesis)
3. **No action on suicidal ideation** pending more data
4. **Thyroid monitoring not routine** (unless symptoms)
```
