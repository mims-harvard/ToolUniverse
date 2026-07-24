---

name: tooluniverse-clinical-risk-scoring
description: "Compute and interpret validated bedside clinical risk scores and pretest probabilities for an INDIVIDUAL patient — pick the right score for the scenario, gather inputs, run the deterministic calculator tool, and read the result against an interpretation table. Covers CHA2DS2-VASc (AF stroke risk), HAS-BLED (bleeding on anticoagulation), CURB-65 (pneumonia severity / admit decision), qSOFA (sepsis screen), Child-Pugh + MELD-Na (cirrhosis severity / transplant priority), Wells DVT and Wells PE (VTE pretest probability), ASCVD (10-year cardiovascular risk / statin decision), and eGFR CKD-EPI (kidney function / drug dosing). Use when asked things like \"stroke risk for this AF patient\", \"should this patient be anticoagulated\", \"pneumonia severity — admit or not?\", \"sepsis screen this patient\", \"DVT/PE pretest probability\", \"10-year cardiovascular risk\", \"cirrhosis severity / MELD score\", or \"eGFR / kidney function\". Pairs CHA2DS2-VASc with HAS-BLED to weigh anticoagulation. NOT for..."
---

# Clinical Risk Scoring

Turn a clinical scenario into the right validated risk score, compute it with a deterministic calculator tool, and interpret the number into a clinical action. All 10 backing tools are pure-compute (no network, no API key) and return `{status, data:{score, interpretation, components, ...}}`.

This skill is **decision-support only** — see LIMITATIONS. It does not replace clinical judgment.

## Step 1 — Map the scenario to the score(s)

| Clinical scenario | Score(s) | Tool(s) |
|---|---|---|
| Atrial fibrillation — stroke risk / anticoagulate? | CHA2DS2-VASc **and** HAS-BLED (pair) | `ClinicalCalc_CHA2DS2_VASc` + `ClinicalCalc_HAS_BLED` |
| Community-acquired pneumonia — severity / admit? | CURB-65 | `ClinicalCalc_CURB_65` |
| Suspected sepsis (infection + ? deterioration) | qSOFA | `ClinicalCalc_qSOFA` |
| Cirrhosis / chronic liver disease severity | Child-Pugh **and** MELD-Na (pair) | `ClinicalCalc_Child_Pugh` + `ClinicalCalc_MELD_Na` |
| Suspected DVT — pretest probability | Wells DVT | `ClinicalCalc_Wells_DVT` |
| Suspected PE — pretest probability | Wells PE | `ClinicalCalc_Wells_PE` |
| Primary CVD prevention — 10-yr risk / statin? | ASCVD | `ClinicalCalc_ASCVD_risk` |
| Kidney function / renal drug dosing / CKD stage | eGFR CKD-EPI | `ClinicalCalc_eGFR_CKD_EPI` |

When the scenario names a **pair**, always run both — one alone is misleading (e.g. stroke risk without bleeding risk, or Child-Pugh without MELD-Na).

## Step 2 — Gather the required inputs

Required vs optional inputs per tool (omitted booleans default to `false`/absent; omitted scalars are rejected when required):

| Tool | Required | Key optional booleans/values |
|---|---|---|
| `ClinicalCalc_CHA2DS2_VASc` | `age` | `chf`, `hypertension`, `diabetes`, `stroke_history`(2pt), `vascular_disease`, `female` |
| `ClinicalCalc_HAS_BLED` | `age` | `hypertension`, `renal_disease`, `liver_disease`, `stroke_history`, `bleeding_history`, `labile_inr`, `drugs`, `alcohol` |
| `ClinicalCalc_CURB_65` | `age` | `confusion`, `elevated_urea`(BUN>19), `high_resp_rate`(>=30), `low_bp` |
| `ClinicalCalc_qSOFA` | (none) | `high_resp_rate`(>=22), `altered_mentation`, `low_sbp`(<=100) |
| `ClinicalCalc_Child_Pugh` | `bilirubin`, `albumin`, `inr` | `ascites`(none/mild/moderate), `encephalopathy`(none/grade1-2/grade3-4) |
| `ClinicalCalc_MELD_Na` | `creatinine`, `bilirubin`, `inr`, `sodium` | `dialysis` (forces creatinine to 4.0) |
| `ClinicalCalc_Wells_DVT` | (none) | `active_cancer`, `immobilization`, `recent_surgery`, `localized_tenderness`, `leg_swollen`, `calf_swelling`, `pitting_edema`, `collateral_veins`, `previous_dvt`, `alternative_diagnosis`(-2) |
| `ClinicalCalc_Wells_PE` | (none) | `clinical_dvt`(3), `pe_most_likely`(3), `tachycardia`(1.5), `immobilization`(1.5), `previous_vte`(1.5), `hemoptysis`(1), `malignancy`(1) |
| `ClinicalCalc_ASCVD_risk` | `age`(40-79), `total_cholesterol`, `hdl_cholesterol`, `systolic_bp` | `bp_treated`, `smoker`, `diabetes`, `female`, `race`("white"/"black") |
| `ClinicalCalc_eGFR_CKD_EPI` | `creatinine`, `age` | `female` |

If a required value is missing, ask the user for it — do not guess. State explicitly which booleans you assumed `false`.

## Step 3 — Compute

```bash
tu run ClinicalCalc_CHA2DS2_VASc '{"age":76,"female":true,"hypertension":true,"diabetes":true}'
```

Every tool returns `data.score` plus a human-readable `data.interpretation` and a `data.components` breakdown (per-factor points). MELD/eGFR/ASCVD also return `unit`; Child-Pugh returns `child_pugh_class`; Wells PE returns `three_tier` and `two_tier`. Echo the `components` so the user can audit which factors drove the score.

## Step 4 — Interpret (per-score tables)

### CHA2DS2-VASc (stroke risk in AF, 0–9)
| Score | Stroke risk | Action |
|---|---|---|
| 0 (men) / 1 (women, sex point only) | Low | No anticoagulation |
| 1 (men) | Intermediate | Consider anticoagulation |
| **>=2 (men) / >=3 (women)** | Elevated | **Oral anticoagulation recommended** |

### HAS-BLED (major bleeding on anticoagulation, 0–9)
| Score | Bleeding risk | Action |
|---|---|---|
| 0–2 | Low–moderate | Anticoagulation reasonable |
| **>=3** | High | Caution; correct **reversible** factors (BP, labile INR, antiplatelet/NSAID, alcohol), closer follow-up — NOT an automatic contraindication |

### How to weigh CHA2DS2-VASc + HAS-BLED together
A high HAS-BLED **does not by itself withhold anticoagulation**. If CHA2DS2-VASc meets the threshold, the stroke benefit usually outweighs bleeding risk; HAS-BLED instead flags **modifiable** risk factors to fix and patients needing closer monitoring. Only a very high, non-modifiable bleeding risk shifts the decision against anticoagulation.

### CURB-65 (CAP severity, 0–5)
| Score | 30-day mortality | Disposition |
|---|---|---|
| 0–1 | Low (~1.5–3%) | Outpatient |
| 2 | Intermediate (~9%) | Short-stay / inpatient admission |
| **3–5** | High (~15–40%) | Inpatient; assess for **ICU** at 4–5 |

### qSOFA (sepsis screen, 0–3)
| Score | Meaning |
|---|---|
| 0–1 | Lower risk — does not rule out sepsis; reassess |
| **>=2** | Higher risk of poor outcome — escalate, full sepsis workup, consider full SOFA / lactate |
qSOFA is a **screen**, not a diagnosis; a low score never excludes sepsis.

### Child-Pugh (cirrhosis severity, class A/B/C)
| Class | Score | 1-yr survival (approx) | Meaning |
|---|---|---|---|
| A | 5–6 | ~100% | Well-compensated |
| B | 7–9 | ~80% | Significant functional compromise |
| C | 10–15 | ~45% | Decompensated; high surgical/anesthetic risk |

### MELD-Na (90-day mortality / transplant priority, 6–40)
| MELD-Na | 90-day mortality (approx) | Transplant relevance |
|---|---|---|
| <=9 | ~2% | Low priority |
| 10–19 | ~6% | |
| 20–29 | ~20% | Rising allocation priority |
| 30–39 | ~50% | High priority |
| **>=40** | **>50%** | Highest priority |
Pair with Child-Pugh: Child-Pugh class anchors chronic severity / surgical risk; MELD-Na drives short-term mortality and transplant listing.

### Wells DVT (pretest probability)
| Score | Probability | Workup |
|---|---|---|
| <2 (esp. <=0) | DVT unlikely | D-dimer; if negative, DVT excluded |
| **>=2** | DVT likely | Proceed to **compression ultrasound** |

### Wells PE (pretest probability)
| Two-tier | Three-tier | Workup |
|---|---|---|
| PE unlikely (<=4) | low (0–1) / moderate (2–6) | D-dimer; if negative, PE excluded (consider PERC if very low) |
| **PE likely (>4)** | high (>6) | **CT pulmonary angiography** (D-dimer not sufficient to exclude) |

### ASCVD 10-year risk (%)
| Risk % | Category | Statin guidance (with shared decision-making) |
|---|---|---|
| <5% | Low | Lifestyle |
| 5–7.4% | Borderline | Consider if risk-enhancers present |
| **7.5–19.9%** | Intermediate | Moderate-intensity statin reasonable |
| **>=20%** | High | High-intensity statin |

### eGFR CKD-EPI (mL/min/1.73m^2) → CKD stage
| eGFR | Stage | Note |
|---|---|---|
| >=90 | G1 | Normal (CKD only if other markers of damage) |
| 60–89 | G2 | Mildly decreased |
| 45–59 | G3a | Mild–moderate |
| 30–44 | G3b | Moderate–severe |
| 15–29 | G4 | Severe — nephrology referral |
| <15 | G5 | Kidney failure |
Use eGFR for renal drug dosing and CKD staging; a single value is an estimate — confirm with a repeat/eGFR trend for staging.

## Worked example A — Atrial fibrillation, weigh anticoagulation (paired)

76-year-old woman with AF, hypertension, type 2 diabetes; on an NSAID; no prior stroke/bleed, BP controlled, stable INR.

```bash
tu run ClinicalCalc_CHA2DS2_VASc '{"age":76,"female":true,"hypertension":true,"diabetes":true}'
# -> score 5: "Elevated risk (5) — oral anticoagulation recommended"
#    components: Age>=75 2, Hypertension 1, Diabetes 1, Female 1

tu run ClinicalCalc_HAS_BLED '{"age":76,"hypertension":true,"drugs":true}'
# -> score 3: "High bleeding risk (3) — caution, review reversible factors"
#    components: Hypertension_uncontrolled 1, Elderly_>65 1, Drugs_antiplatelet_NSAID 1
```

**Interpretation.** CHA2DS2-VASc 5 (>=3 for a woman) → anticoagulation recommended. HAS-BLED 3 is high but driven by **modifiable** factors: stop the NSAID and control BP and 2 of the 3 points disappear, lowering bleeding risk. The high HAS-BLED does **not** cancel anticoagulation — it directs you to fix reversible risks and monitor more closely.

## Worked example B — Cirrhosis severity and transplant priority (paired)

Cirrhotic patient: bilirubin 3.5 mg/dL, albumin 2.5 g/dL, INR 2.4, moderate ascites, grade 1–2 encephalopathy; creatinine 2.0, sodium 128, not on dialysis.

```bash
tu run ClinicalCalc_Child_Pugh '{"bilirubin":3.5,"albumin":2.5,"inr":2.4,"ascites":"moderate","encephalopathy":"grade1-2"}'
# -> score 14, child_pugh_class "C": "Class C (score 14): decompensated disease"

tu run ClinicalCalc_MELD_Na '{"creatinine":2.0,"bilirubin":5.0,"inr":2.0,"sodium":128,"dialysis":false}'
# -> score 31: "MELD-Na 31: very high ... 90-day mortality risk"
```

**Interpretation.** Child-Pugh class C (14) = decompensated cirrhosis, very high surgical/anesthetic risk — avoid elective surgery. MELD-Na 31 implies roughly a third-or-higher 90-day mortality and a high transplant-allocation priority. Together they justify urgent hepatology / transplant evaluation. (Note MELD uses bilirubin 5.0 and INR 2.0 from this patient's labs; lower bounds of 1.0 are applied internally.)

## Completeness checklist
- [ ] Picked the score(s) that match the scenario — ran **both** members of a pair (CHA2DS2-VASc+HAS-BLED, Child-Pugh+MELD-Na)
- [ ] Confirmed all **required** inputs; asked for missing ones rather than guessing
- [ ] Stated which optional booleans were assumed `false`
- [ ] Reported `score`, `interpretation`, and the `components` breakdown
- [ ] Mapped the score to a clinical action using the interpretation table
- [ ] For pairs, explained how to weigh the two scores together
- [ ] Stated the LIMITATIONS caveat (decision-support, validated population, ASCVD age 40–79)

## LIMITATIONS
- **Decision-support only.** These scores inform, but do not replace, clinical judgment and the full clinical picture. Do not present output as a treatment directive.
- **Validated populations.** Each score was derived/validated in specific cohorts and may not transfer to children, pregnancy, valvular AF (CHA2DS2-VASc is for **non-valvular** AF), or other excluded groups.
- **ASCVD** Pooled Cohort Equations are validated only for **ages 40–79** and the White / African-American coefficient sets; they can mis-estimate for other ancestries and are for **primary** prevention (no prior ASCVD event).
- **eGFR** CKD-EPI assumes stable kidney function (steady-state creatinine); it is unreliable in acute kidney injury, extremes of muscle mass, or amputees, and a single value does not stage CKD on its own.
- **qSOFA / CURB-65 / Wells** are screening / pretest-probability tools — a reassuring score does not exclude the diagnosis; combine with clinical gestalt and confirmatory testing.
- **MELD-Na / Child-Pugh** apply to **chronic** liver disease; they do not capture acute liver failure or hepatocellular-carcinoma exception points.
- Inputs are taken at face value — garbage in, garbage out. Verify lab units (mg/dL vs mmol/L, BUN vs urea) before entry.
- Not a substitute for institutional protocols, guideline updates, or specialist consultation.
