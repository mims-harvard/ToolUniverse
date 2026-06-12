# Drug-Drug Interaction Skill Examples

Real-world clinical scenarios demonstrating DDI analysis capabilities.

---

## Example 1: Warfarin + Antibiotic (CYP Interaction)

**Scenario**: 72-year-old patient on warfarin for atrial fibrillation develops UTI requiring antibiotics.

**User Query**:
```
"Analyze drug interactions: warfarin and amoxicillin"
```

**Skill Output** (`DDI_risk_report_warfarin_amoxicillin.md`):

### Executive Summary
- **Overall Risk**: **MODERATE** (Score: 55/100)
- **Key Interaction**: Amoxicillin alters gut flora → ↓ vitamin K → ↑ warfarin effect → ↑ INR
- **Evidence**: ★★★ (FDA label, clinical studies, FAERS signals)
- **Management**: Monitor INR at day 3-5 of antibiotic; adjust warfarin dose if INR >therapeutic range

### Mechanisms
- **CYP450**: No direct CYP interaction
- **Pharmacodynamic**: Antibiotic disrupts gut bacteria that synthesize vitamin K → enhances warfarin effect
- **Bidirectional**: Warfarin → amoxicillin (no interaction)

### Clinical Evidence
- **Literature**: 15 case reports of INR elevation with amoxicillin + warfarin
- **FAERS**: 234 reports of elevated INR with combination

### Management
- **Primary**: Continue both drugs with monitoring
- **Monitoring**: Check INR at baseline, day 3-5, day 7, then resume normal schedule
- **Dose adjustment**: Reduce warfarin by 10-20% if INR rises above 3.0
- **Alternative**: Consider fosfomycin (single dose, less gut flora disruption)

---

## Example 2: Statin + Azole Antifungal (Major DDI)

**Scenario**: 58-year-old on simvastatin for hyperlipidemia develops systemic fungal infection.

**User Query**:
```
"Can I take simvastatin with ketoconazole?"
```

**Skill Output** (`DDI_risk_report_simvastatin_ketoconazole.md`):

### Executive Summary
- **Overall Risk**: **MAJOR - CONTRAINDICATED** (Score: 95/100)
- **Key Interaction**: Ketoconazole (strong CYP3A4 inhibitor) → ↑ simvastatin AUC 10-20x → rhabdomyolysis risk
- **Evidence**: ★★★ (FDA label contraindication, PK study)
- **Management**: **DO NOT COMBINE**. Switch to pravastatin or rosuvastatin (non-CYP3A4 substrates)

### Mechanisms
| Direction | Mechanism | Effect | Severity |
|-----------|-----------|--------|----------|
| Ketoconazole → Simvastatin | Strong CYP3A4 inhibition | ↑ Simvastatin levels 10-20x | **MAJOR** |
| Simvastatin → Ketoconazole | None | No effect | Minor |

### FDA Label Warning
> "Concomitant use of strong CYP3A4 inhibitors (including ketoconazole) with simvastatin is CONTRAINDICATED"

### Alternative Recommendations
**Safer Statins** (no CYP3A4 interaction):
1. **Pravastatin** (hydrophilic, not CYP-metabolized) - PREFERRED
2. **Rosuvastatin** (minimal CYP metabolism)
3. **Pitavastatin** (CYP2C9 metabolism)

**Alternative Antifungals** (if systemic therapy needed):
1. **Fluconazole** (moderate CYP3A4 inhibitor) - allow simvastatin max 20mg
2. **Micafungin** (echinocandin, no CYP interaction)

### Patient Counseling
"These two drugs should NOT be taken together due to very high risk of muscle damage. We will switch you to pravastatin, which works the same way but doesn't have this interaction."

---

## Example 3: Polypharmacy in Elderly (5+ Drugs)

**Scenario**: 78-year-old with multiple conditions on complex medication regimen.

**User Query**:
```
"Assess drug interactions for this regimen: warfarin, lisinopril, metoprolol, omeprazole, amlodipine, furosemide"
```

**Skill Output** (`DDI_risk_report_polypharmacy.md`):

### Executive Summary
- **Drugs Analyzed**: 6 medications
- **Total Interactions Detected**: 15 pairwise combinations
- **Major Interactions**: 0
- **Moderate Interactions**: 3
- **Minor Interactions**: 12
- **Polypharmacy Risk Score**: 38/100 (Low-Moderate)

### DDI Matrix

|  | Warfarin | Lisinopril | Metoprolol | Omeprazole | Amlodipine | Furosemide |
|--|----------|------------|------------|------------|------------|------------|
| **Warfarin** | - | None | Minor | **MODERATE** | None | Minor |
| **Lisinopril** | None | - | MODERATE | None | MODERATE | MODERATE |
| **Metoprolol** | Minor | MODERATE | - | None | Minor | None |
| **Omeprazole** | **MODERATE** | None | None | - | None | None |
| **Amlodipine** | None | MODERATE | Minor | None | - | None |
| **Furosemide** | Minor | MODERATE | None | None | None | - |

### High-Priority Interactions

#### 1. Warfarin + Omeprazole (MODERATE)
- **Mechanism**: Omeprazole inhibits CYP2C19 (warfarin metabolism)
- **Effect**: ↑ warfarin levels → ↑ INR
- **Management**: Monitor INR more frequently (every 2 weeks initially)
- **Evidence**: ★★☆

#### 2. Lisinopril + Furosemide (MODERATE - Pharmacodynamic)
- **Mechanism**: Additive hypotensive effects + hypokalemia risk
- **Effect**: Orthostatic hypotension, electrolyte imbalance
- **Management**: Monitor BP, electrolytes (K+, Na+), renal function
- **Evidence**: ★★☆

#### 3. Lisinopril + Amlodipine (MODERATE - Pharmacodynamic)
- **Mechanism**: Additive blood pressure lowering
- **Effect**: Hypotension, especially in elderly
- **Management**: Start amlodipine at lower dose (2.5mg), monitor BP closely
- **Evidence**: ★★☆

### Monitoring Schedule

| Parameter | Frequency | Action Threshold |
|-----------|-----------|------------------|
| **INR** | Every 2 weeks | Maintain 2.0-3.0 |
| **Blood pressure** | Weekly x 4 weeks, then monthly | <90/60 mmHg → reduce doses |
| **Serum K+** | Monthly | <3.5 or >5.5 → adjust furosemide/lisinopril |
| **Serum creatinine** | Every 3 months | >1.5x baseline → review ACE inhibitor dose |

### Simplification Opportunities
1. **Omeprazole**: If no active GERD/ulcer, consider discontinuation → eliminates warfarin interaction
2. **Furosemide**: Could switch to thiazide diuretic (lower electrolyte disturbance risk)

---

## Example 4: QTc Prolongation Risk (Multiple Drugs)

**Scenario**: Patient on psychiatric medications - risk of cardiac arrhythmia.

**User Query**:
```
"Analyze QTc prolongation risk: escitalopram, quetiapine, azithromycin"
```

**Skill Output**:

### Executive Summary
- **Overall Risk**: **MAJOR** (Score: 80/100)
- **Concern**: All 3 drugs prolong QTc interval → additive risk of torsades de pointes (potentially fatal arrhythmia)
- **Evidence**: ★★★ (FDA warnings for all 3 drugs)
- **Management**: Baseline ECG required; consider alternative to azithromycin if short-term antibiotic needed

### QTc Prolongation Mechanisms

| Drug | QTc Effect | hERG Block | FDA Warning |
|------|------------|------------|-------------|
| **Escitalopram** | Dose-dependent (+15ms at 20mg) | Moderate | Yes |
| **Quetiapine** | Dose-dependent (+20ms) | Moderate | Yes (boxed) |
| **Azithromycin** | +10-15ms | Mild | Yes |
| **COMBINED** | **+45-50ms** (additive) | - | **High risk** |

### Risk Factors Present
✓ Multiple QTc-prolonging drugs
✓ Psychiatric patient (may have baseline QTc prolongation)
✗ Unknown: Electrolyte status (K+, Mg2+)
✗ Unknown: Cardiac history

### Management Strategies

**PRIMARY Recommendation**:
1. **Baseline ECG** - Measure QTc before azithromycin
   - If QTc >450ms (male) or >470ms (female) → high risk
   - If QTc >500ms → DO NOT add azithromycin
2. **Check electrolytes** - Correct K+ >4.0, Mg2+ >2.0
3. **Alternative antibiotic**: Amoxicillin (no QTc effect)

**If Azithromycin Necessary**:
- ECG monitoring during treatment
- Correct all electrolyte abnormalities
- Educate patient on warning signs (palpitations, syncope, dizziness)
- Consider temporary quetiapine dose reduction

**Long-term**:
- Avoid adding other QTc-prolonging drugs
- Annual ECG monitoring recommended
- Maintain optimal electrolytes

---

## Example 5: Alternative Drug Recommendations

**Scenario**: Patient needs statin but takes multiple CYP3A4 inhibitors.

**User Query**:
```
"I'm on diltiazem and erythromycin. Which statin is safest?"
```

**Skill Output**:

### DDI Risk Analysis by Statin

| Statin | CYP3A4 Substrate? | DDI Risk with Diltiazem + Erythromycin | Max Safe Dose | Evidence |
|--------|-------------------|---------------------------------------|---------------|----------|
| **Simvastatin** | Yes (major) | **MAJOR** - contraindicated | Do not use | ★★★ |
| **Atorvastatin** | Yes (major) | **MAJOR** - limit to 20mg | 20mg max | ★★★ |
| **Lovastatin** | Yes (major) | **MAJOR** - contraindicated | Do not use | ★★★ |
| **Pravastatin** | No | **LOW** - no interaction | Standard dosing | ★★★ |
| **Rosuvastatin** | No (minimal) | **LOW** - no interaction | Standard dosing | ★★★ |
| **Pitavastatin** | No (CYP2C9) | **LOW** - no interaction | Standard dosing | ★★☆ |
| **Fluvastatin** | No (CYP2C9) | **LOW** - no interaction | Standard dosing | ★★☆ |

### Recommendation

**PREFERRED Statins** (No DDI risk):
1. **Pravastatin** 40mg daily (hydrophilic, not CYP-metabolized)
2. **Rosuvastatin** 10-20mg daily (minimal CYP metabolism)

**AVOID**:
- Simvastatin (CONTRAINDICATED)
- Atorvastatin >20mg (risk of myopathy)
- Lovastatin (CONTRAINDICATED)

### Clinical Rationale
Diltiazem (moderate CYP3A4 inhibitor) + erythromycin (strong CYP3A4 inhibitor) = very high inhibition → CYP3A4-metabolized statins will have markedly elevated levels → myopathy/rhabdomyolysis risk.

Pravastatin and rosuvastatin do not rely on CYP3A4 metabolism and are safe in this combination.

---

## Example 6: Drug-Food Interaction

**Scenario**: Patient on tacrolimus asks about grapefruit juice.

**User Query**:
```
"Can I drink grapefruit juice while taking tacrolimus?"
```

**Skill Output**:

### Executive Summary
- **Risk**: **MAJOR** (Score: 85/100)
- **Mechanism**: Grapefruit juice irreversibly inhibits intestinal CYP3A4 → ↑ tacrolimus absorption → ↑ toxicity risk
- **Evidence**: ★★★ (FDA label, clinical studies)
- **Management**: **AVOID grapefruit** and grapefruit juice completely

### Interaction Details

**Tacrolimus + Grapefruit Juice**:
- **Effect**: ↑ tacrolimus blood levels by 200-500% (unpredictable)
- **Onset**: Within hours of consumption
- **Duration**: Inhibition lasts 24-72 hours per serving
- **Clinical Consequences**:
  - Nephrotoxicity
  - Neurotoxicity (tremor, seizures)
  - Increased infection risk

### FDA Label Warning
> "Grapefruit juice affects CYP3A4-mediated metabolism and should be avoided"

### Patient Counseling
"Do NOT consume grapefruit or grapefruit juice while taking tacrolimus. Even small amounts can cause dangerous increases in drug levels. This includes:
- Fresh grapefruit
- Grapefruit juice
- Products containing grapefruit

Safe alternatives: Orange juice, apple juice, cranberry juice"

### Other Foods to Avoid (CYP3A4 Inhibitors)
- **Seville oranges** (bitter/sour oranges in marmalade)
- **Pomegranate juice** (moderate inhibitor)
- **Starfruit** (moderate inhibitor)

**Safe citrus fruits**: Regular oranges, lemons, limes, tangerines

---

## Example 7: Timing Separation Strategy

**Scenario**: Patient needs both levothyroxine and calcium supplement.

**User Query**:
```
"When should I take levothyroxine if I'm also taking calcium carbonate?"
```

**Skill Output**:

### Executive Summary
- **Risk**: **MODERATE** (Score: 45/100)
- **Mechanism**: Calcium binds levothyroxine in GI tract → ↓ absorption → ↓ efficacy
- **Evidence**: ★★★ (FDA label, PK studies)
- **Management**: **Separate by 4 hours** - levothyroxine AM on empty stomach, calcium with lunch/dinner

### Interaction Details

**Levothyroxine + Calcium**:
- **Effect**: ↓ levothyroxine absorption by 30-40%
- **Onset**: Immediate (affects same-dose absorption)
- **Duration**: Single-dose effect (no accumulation)
- **Clinical Consequence**: Hypothyroidism symptoms, ↑ TSH

### Timing Separation Strategy

**Recommended Schedule**:

| Time | Medication | Instructions |
|------|------------|--------------|
| **6:00 AM** | Levothyroxine 100mcg | Take on empty stomach with water |
| 7:00 AM | Breakfast | Wait 1 hour after levothyroxine |
| **12:00 PM** | Calcium carbonate 1000mg | Take with lunch (4 hours after levothyroxine) |
| **6:00 PM** | Calcium carbonate 500mg | Take with dinner (if twice-daily dosing) |

**Key Points**:
- Levothyroxine MUST be taken on empty stomach
- Wait at least 4 hours before calcium
- Consistency is critical - same schedule daily

### Other Supplements/Drugs Requiring Separation

| Substance | Separation Time | Rationale |
|-----------|----------------|-----------|
| **Iron supplements** | 4 hours | Chelation |
| **Multivitamins with minerals** | 4 hours | Contains iron/calcium |
| **Antacids** | 4 hours | Aluminum/magnesium binding |
| **Soy products** | 4 hours | Decreased absorption |
| **Coffee** | 30-60 minutes | Decreased absorption |

### Monitoring
- Check TSH in 6-8 weeks after implementing timing separation
- Adjust levothyroxine dose if TSH still elevated

---

## Key Takeaways from Examples

### Evidence Grading Consistency
- ★★★ = FDA label, RCT, established clinical data
- ★★☆ = Clinical studies, case series, PK studies
- ★☆☆ = Case reports, theoretical mechanisms

### Risk Scoring Themes
- **80-100**: Contraindicated, avoid combination
- **60-79**: High risk, use alternatives if possible
- **40-59**: Moderate risk, monitor and adjust
- **20-39**: Low risk, minimal intervention
- **0-19**: Negligible risk

### Management Hierarchy
1. **Avoid combination** (Major DDI)
2. **Use alternative drug** (safer option exists)
3. **Dose adjustment** (reduce doses of affected drugs)
4. **Timing separation** (chelation/absorption issues)
5. **Monitoring** (detect adverse effects early)
6. **Patient education** (recognize warning signs)

### Bidirectional Analysis Importance
- Always analyze BOTH directions (A→B and B→A)
- Effects are often asymmetric
- Example: Ketoconazole affects simvastatin, but simvastatin doesn't affect ketoconazole

### Alternative Drug Selection Criteria
1. **Same therapeutic class** (maintains efficacy)
2. **Different metabolism** (avoids DDI mechanism)
3. **Evidence of safety** (FDA approval, clinical use)
4. **Similar potency** (equivalent dosing exists)
