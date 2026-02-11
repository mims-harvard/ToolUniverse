# Drug-Drug Interaction Prediction Skill

Comprehensive DDI risk assessment with evidence-based clinical guidance.

---

## Quick Start

### Example 1: Two-Drug Analysis
```
User: "Analyze drug interactions between warfarin and amoxicillin"

Agent: Creates `DDI_risk_report_warfarin_amoxicillin.md` with:
- Bidirectional mechanism analysis
- Risk score: 55/100 (Moderate)
- Management: Monitor INR at day 3-5
- Evidence: ★★★ (FDA label + clinical studies)
```

### Example 2: Polypharmacy (5+ drugs)
```
User: "Assess interactions for: warfarin, lisinopril, metoprolol, omeprazole, amlodipine, furosemide"

Agent: Creates `DDI_risk_report_polypharmacy.md` with:
- 15 pairwise interactions analyzed
- DDI matrix showing all combinations
- Polypharmacy risk score: 38/100
- Top 3 priority interactions with management
```

### Example 3: Alternative Drug Recommendations
```
User: "Which statin is safest with diltiazem and erythromycin?"

Agent: Analyzes all statins and recommends:
- PREFERRED: Pravastatin or rosuvastatin (no CYP3A4 interaction)
- AVOID: Simvastatin, lovastatin (contraindicated)
- Evidence table with risk scores for each statin
```

---

## Core Features

### 1. Bidirectional Analysis
Always analyzes both directions:
- Drug A → Drug B (A affects B)
- Drug B → Drug A (B affects A)

Effects are often asymmetric (e.g., ketoconazole affects simvastatin, but not vice versa).

### 2. Multi-Dimensional Risk Scoring (0-100)
```
Score = Mechanism(30) + Evidence(25) + Clinical Impact(25) + Prevalence(10) + Reversibility(10)

80-100: Critical (contraindicated)
60-79:  High (avoid if possible)
40-59:  Moderate (monitor/adjust)
20-39:  Low (minimal action)
0-19:   Negligible
```

### 3. Evidence Grading
- ★★★ = FDA label, RCT, clinical guidelines
- ★★☆ = Clinical studies, PK studies, case series
- ★☆☆ = Case reports, theoretical mechanisms
- ☆☆☆ = Computational predictions only

### 4. Mechanism Analysis
**Pharmacokinetic (PK)**:
- CYP450 enzyme interactions (CYP3A4, 2D6, 2C9, 2C19, 1A2)
- Drug transporter interactions (P-gp, OATs, OCTs, BCRP, OATPs)
- Protein binding displacement

**Pharmacodynamic (PD)**:
- Additive/synergistic effects (e.g., two anticoagulants)
- Antagonistic effects (e.g., beta-blocker + beta-agonist)
- QTc prolongation (additive cardiac risk)
- CNS depression (additive sedation)
- Serotonin syndrome risk

### 5. Clinical Management Strategies
For each DDI, provides:
1. Avoid combination (if Major/contraindicated)
2. Alternative drug recommendations
3. Dose adjustments
4. Timing separation strategies
5. Monitoring parameters (labs, vital signs, symptoms)
6. Patient counseling points

---

## When to Use This Skill

✅ **Use for**:
- Two-drug interaction analysis
- Polypharmacy risk assessment (3+ drugs)
- Alternative drug recommendations (lower DDI risk)
- QTc prolongation risk (multiple drugs)
- Clinical decision support for prescribing
- Patient safety reviews
- Medication reconciliation

❌ **Don't use for**:
- Single drug safety profile → use `tooluniverse-drug-research`
- Drug mechanism only → use `tooluniverse-drug-research`
- Pharmacogenomics → use PGx-specific analysis
- Disease-drug associations → use disease-focused skills

---

## Key Principles

### Report-First Approach
1. Create report file FIRST with all section headers
2. Populate progressively as data is gathered
3. User sees complete report, not search process

### Patient Safety Focus
- Actionable clinical guidance, not just theory
- Evidence-based recommendations
- Alternative drugs when DDI risk is high
- Clear monitoring parameters
- Patient-friendly counseling language

### Completeness Requirement
- All sections must exist
- Explicit "No interaction found" when appropriate
- Document tool failures
- Cite data sources throughout

---

## Tools Used

| Analysis Path | Primary Tools |
|---------------|---------------|
| Drug ID | `rxnorm_get_drugs_by_name`, `DailyMed_search_spls`, `PubChem_get_CID_by_compound_name` |
| CYP interactions | `ADMETAI_predict_CYP_interactions`, `DailyMed_get_spl_sections_by_setid` |
| FDA warnings | `DailyMed_get_spl_sections_by_setid` (contraindications, boxed_warning, drug_interactions) |
| Clinical evidence | `PubMed_search_articles`, `search_clinical_trials` |
| Post-marketing | `FAERS_count_reactions_by_drug_event` |
| Alternatives | `DGIdb_get_drug_gene_interactions`, `DailyMed_search_spls` |

---

## Output Format

### Report Structure
```
DDI_risk_report_[DRUG1]_[DRUG2].md

0. Drug Identification
1. Interaction Mechanisms (CYP, Transporters, PD)
2. FDA Label & Regulatory Warnings
3. Clinical Evidence & Literature
4. Post-Marketing Surveillance (FAERS)
5. Severity Classification & Risk Scoring
6. Clinical Management Strategies
7. Summary & Clinical Action Plan
```

### Polypharmacy Report
```
DDI_risk_report_polypharmacy.md

- DDI matrix (all pairwise combinations)
- Polypharmacy risk score
- Top priority interactions
- Cumulative monitoring plan
- Simplification opportunities
```

---

## Real-World Examples

See [EXAMPLES.md](EXAMPLES.md) for 7 detailed scenarios:

1. **Warfarin + Amoxicillin** - CYP/gut flora interaction
2. **Simvastatin + Ketoconazole** - Major contraindicated DDI
3. **Polypharmacy (6 drugs)** - Complex elderly regimen
4. **QTc prolongation** - Multiple psychiatric drugs
5. **Alternative recommendations** - Safer statin selection
6. **Drug-food interaction** - Tacrolimus + grapefruit
7. **Timing separation** - Levothyroxine + calcium

---

## Success Criteria

Before finalizing DDI report:

✅ All drug names resolved to standard identifiers
✅ Bidirectional analysis completed (A→B and B→A)
✅ All mechanism types assessed (CYP, transporters, PD)
✅ FDA label warnings extracted
✅ Clinical literature searched
✅ Evidence grades assigned (★★★, ★★☆, ★☆☆)
✅ Risk score calculated (0-100)
✅ Severity classified (Major/Moderate/Minor)
✅ Primary management recommendation provided
✅ Alternative drugs suggested (if Major DDI)
✅ Monitoring parameters defined
✅ Patient counseling points included
✅ All sections completed (no `[Analyzing...]` placeholders)
✅ Data sources cited throughout

When all criteria met → **Ready for Clinical Use**

---

## Quick Reference

### Severity Classification
- **Major**: High risk, life-threatening. **Avoid combination**
- **Moderate**: Significant risk. **Monitor closely**, dose adjust
- **Minor**: Limited risk. **Minimal action** needed

### Risk Score Interpretation
- **80-100**: Critical - contraindicated
- **60-79**: High - avoid if alternatives exist
- **40-59**: Moderate - monitor and adjust
- **20-39**: Low - minimal precautions
- **0-19**: Negligible

### Management Hierarchy
1. Avoid combination (Major DDI)
2. Use alternative drug
3. Dose adjustment
4. Timing separation
5. Intensive monitoring
6. Patient education

---

## Technical Details

### Evidence Quality Metrics
Reports include:
- Distribution of evidence grades (% ★★★, ★★☆, ★☆☆)
- Source coverage (FDA labels, PubMed, FAERS)
- Data recency and limitations

### Limitations
- FAERS does not support direct co-medication queries (requires manual review)
- Some theoretical interactions lack clinical validation
- Alternative drug recommendations limited to same therapeutic class
- Non-US regulatory data (EMA, PMDA) not available via public APIs

---

## For Developers

### Skill Implementation
See [SKILL.md](SKILL.md) for:
- Complete implementation guide
- Tool call sequences
- Error handling patterns
- Bidirectional analysis algorithms
- Risk scoring formulas
- Alternative drug selection logic

### Testing
Validate skill with:
1. Two-drug pairs (10+ examples)
2. Polypharmacy (3 scenarios, 5-8 drugs each)
3. Edge cases (no interaction, contraindicated, food-drug)
4. Bidirectional asymmetry (e.g., A→B but not B→A)

---

## Clinical Disclaimer

This skill provides decision support information based on FDA labels, clinical literature, and pharmacology databases. It is NOT a substitute for clinical judgment, patient-specific assessment, or consultation with a pharmacist. Always verify critical DDI information with authoritative sources and consider individual patient factors (age, renal/hepatic function, comorbidities, concomitant medications beyond those analyzed).

---

## Version Information

**Skill Version**: 1.0
**Last Updated**: 2026-02-09
**ToolUniverse Compatibility**: v0.3.0+
**Key Dependencies**: DailyMed, PubMed, ADMET-AI, FAERS, RxNorm

---

For questions or feedback, see main ToolUniverse documentation.
