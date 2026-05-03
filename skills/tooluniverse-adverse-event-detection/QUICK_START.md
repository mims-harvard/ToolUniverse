# Adverse Drug Event Signal Detection - Quick Start

## What This Skill Does

Detects and quantifies adverse drug event signals using FDA FAERS disproportionality analysis (PRR, ROR, IC), FDA label mining, mechanism-based prediction, and literature evidence. Produces a Safety Signal Score (0-100) for clinical and regulatory decision-making.

## Quick Examples

### Example 1: Full Safety Signal Report

> "Detect adverse event signals for atorvastatin"

The skill will:
1. Resolve atorvastatin to CHEMBL1487 / DB01076
2. Query FAERS for top adverse events (fatigue, diarrhoea, myalgia, rhabdomyolysis, ...)
3. Calculate PRR/ROR/IC for each significant event with 95% CI
4. Extract FDA label warnings and contraindications
5. Compare to statin class (simvastatin, rosuvastatin, pravastatin)
6. Check PharmGKB for pharmacogenomic risk factors (SLCO1B1)
7. Search PubMed for safety literature
8. Calculate Safety Signal Score (e.g., 62/100 = Moderate Concern)
9. Generate comprehensive markdown report

### Example 2: Specific Adverse Event Investigation

> "Is pembrolizumab associated with myocarditis? Calculate the disproportionality."

The skill will focus on:
1. Resolve pembrolizumab to ChEMBL ID
2. Run `FAERS_calculate_disproportionality(drug_name="PEMBROLIZUMAB", adverse_event="Myocarditis")`
3. Get PRR, ROR, IC with 95% CI and signal strength
4. Stratify by demographics (age, sex)
5. Check FDA label for myocarditis warnings
6. Search literature for immune checkpoint inhibitor cardiotoxicity

### Example 3: Drug Class Comparison

> "Compare safety of apixaban vs warfarin for bleeding events"

The skill will:
1. Run `FAERS_compare_drugs(drug1="APIXABAN", drug2="WARFARIN", adverse_event="Haemorrhage")`
2. Compare PRR/ROR/IC side-by-side
3. Repeat for related events: GI haemorrhage, intracranial haemorrhage, epistaxis
4. Generate comparative safety table

### Example 4: Emerging Signal Detection

> "Are there emerging safety signals for semaglutide not in the label?"

The skill will:
1. Get all FAERS signals for semaglutide
2. Calculate disproportionality for top 20 events
3. Extract all FDA label warnings
4. Identify signals in FAERS that are NOT in the label = potential emerging signals
5. Search recent literature and preprints for confirmation
6. Rank by signal strength and case count

### Example 5: Post-Market Surveillance Report

> "Generate a pharmacovigilance signal detection report for methotrexate"

Produces full 10-section report with:
- Executive summary
- FAERS profile with >15 adverse events
- PRR/ROR/IC for all significant events
- FDA label safety extraction
- Target safety profile
- Drug class comparison
- PGx risk factors
- Literature evidence
- Safety Signal Score
- Clinical recommendations

## Key Outputs

1. **Safety Signal Score** (0-100): Quantitative risk metric
   - 75-100: High concern
   - 50-74: Moderate concern
   - 25-49: Low-moderate concern
   - 0-24: Low concern

2. **Disproportionality Table**: PRR, ROR, IC with 95% CI for each AE

3. **Signal Strength Classification**: Strong/Moderate/Weak/None for each event

4. **Evidence Grading**: T1 (regulatory) to T4 (computational) for each finding

5. **Markdown Report**: Saved to `[DRUG]_adverse_event_report.md`

## Common Drug Names to Try

| Drug | Class | Expected Key Signals |
|------|-------|---------------------|
| Atorvastatin | Statin | Rhabdomyolysis, myalgia, hepatotoxicity |
| Metformin | Biguanide | Lactic acidosis |
| Warfarin | Anticoagulant | Hemorrhage |
| Pembrolizumab | Anti-PD-1 | Immune-mediated AEs (colitis, pneumonitis) |
| Doxorubicin | Anthracycline | Cardiotoxicity |
| Methotrexate | Antimetabolite | Hepatotoxicity, pancytopenia |
| Ibuprofen | NSAID | GI bleeding, renal injury |

## Tips

- **Use generic names** in UPPERCASE for FAERS queries (e.g., "ATORVASTATIN")
- **MedDRA terms** are required for specific event queries (e.g., "Rhabdomyolysis", not "muscle breakdown")
- **PRR >= 2.0** with lower CI > 1.0 and N >= 3 indicates a signal
- **PRR >= 5.0** indicates a strong signal requiring investigation
- **Check FDA label** to distinguish known vs novel signals
- **Drug class comparison** helps determine if signal is drug-specific or class-wide
