# Signal Detection Reference

Detailed methodology for pharmacovigilance signal detection, disproportionality analysis, and signal prioritization.

---

## Disproportionality Analysis

**Proportional Reporting Ratio (PRR)**:
```
PRR = (A/B) / (C/D)

Where:
A = Reports of drug X with event Y
B = Reports of drug X with any event
C = Reports of event Y with any drug (excluding X)
D = Total reports (excluding drug X)
```

**Signal Thresholds**:
| Measure | Signal Threshold | Strong Signal |
|---------|------------------|---------------|
| PRR | >2.0 | >3.0 |
| Chi-squared | >4.0 | >10.0 |
| N (case count) | >=3 | >=10 |

---

## Severity Classification

| Category | Definition | Priority |
|----------|------------|----------|
| **Fatal** | Death outcome | Highest |
| **Life-threatening** | Immediate death risk | Very High |
| **Hospitalization** | Required/prolonged hospitalization | High |
| **Disability** | Persistent impairment | High |
| **Congenital anomaly** | Birth defect | High |
| **Other serious** | Medical intervention required | Medium |
| **Non-serious** | No serious criteria | Low |

---

## Signal Scoring Formula

```
Signal Score = PRR x Severity_Weight x log10(Case_Count + 1)

Severity Weights:
- Fatal: 10
- Life-threatening: 8
- Hospitalization: 5
- Disability: 5
- Other serious: 3
- Non-serious: 1
```

---

## Evidence Grading

| Tier | Symbol | Criteria | Example |
|------|--------|----------|---------|
| **T1** | Critical | PRR >10, fatal outcomes, boxed warning | Lactic acidosis |
| **T2** | Serious | PRR 3-10, serious outcomes | Hepatotoxicity |
| **T3** | Moderate | PRR 2-3, moderate concern | Hypoglycemia |
| **T4** | Low | PRR <2, known/expected | GI side effects |

---

## Warning Severity Categories (Label)

| Category | Description |
|----------|-------------|
| **Boxed Warning** | Most serious, life-threatening |
| **Contraindication** | Must not use |
| **Warning** | Significant risk |
| **Precaution** | Use caution |

---

## PGx Evidence Levels

| Level | Description | Clinical Action |
|-------|-------------|-----------------|
| **1A** | CPIC/DPWG guideline, implementable | Follow guideline |
| **1B** | CPIC/DPWG guideline, annotation | Consider testing |
| **2A** | VIP annotation, moderate evidence | May inform |
| **2B** | VIP annotation, weaker evidence | Research |
| **3** | Low-level annotation | Not actionable |

---

## Example: FAERS Signal Interpretation

**Strong Signal: Lactic Acidosis**
- PRR of 15.2 indicates 15x higher reporting rate than expected
- 89% classified as serious
- 156 fatalities (12.5% case fatality)
- **Known class effect of biguanides**
- Risk factors: renal impairment, hypoxia, contrast agents

**Moderate Signal: Hepatotoxicity**
- PRR of 3.1, 234 serious reports, 12 fatal
- Check LFTs if symptoms

**Known/Expected: GI Effects**
- Diarrhea PRR 2.3, 18% frequency -> Start low, titrate slow
- Nausea PRR 1.8, 12% frequency -> Take with food
