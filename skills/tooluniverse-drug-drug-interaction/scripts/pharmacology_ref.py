"""
Pharmacology reference database for clinical drug interaction questions.

Usage:
    python pharmacology_ref.py --type cyp_substrate --drug "lamotrigine"
    python pharmacology_ref.py --type cyp_inhibitor --enzyme "CYP3A4"
    python pharmacology_ref.py --type cyp_inducer --enzyme "CYP2C9"
    python pharmacology_ref.py --type narrow_ti
    python pharmacology_ref.py --type ugt_substrate --drug "lamotrigine"
    python pharmacology_ref.py --type ugt_inhibitor --drug "valproate"
    python pharmacology_ref.py --type interaction --drug1 "valproate" --drug2 "lamotrigine"
    python pharmacology_ref.py --type all_interactions --drug "lamotrigine"

Addresses Q927 failure pattern: valproate inhibits UGT1A4 → lamotrigine levels double.
No external dependencies.
"""

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# CYP450 DATA
# Each entry: drug -> {enzymes: [CYP name, ...]}
# Role keys: "substrate", "inhibitor", "inducer"
# ---------------------------------------------------------------------------

CYP_DATA = {
    # Format: drug_name_lower -> {role: [enzyme, ...]}
    # CYP3A4
    "alprazolam": {"substrate": ["CYP3A4"]},
    "amlodipine": {"substrate": ["CYP3A4"]},
    "atorvastatin": {"substrate": ["CYP3A4"]},
    "buspirone": {"substrate": ["CYP3A4"]},
    "carbamazepine": {"substrate": ["CYP3A4"], "inducer": ["CYP3A4", "CYP2C9", "CYP1A2", "CYP2B6"]},
    "clarithromycin": {"substrate": ["CYP3A4"], "inhibitor": ["CYP3A4"]},
    "clonazepam": {"substrate": ["CYP3A4"]},
    "cyclosporine": {"substrate": ["CYP3A4"], "inhibitor": ["CYP3A4"]},
    "diazepam": {"substrate": ["CYP3A4", "CYP2C19"]},
    "diltiazem": {"substrate": ["CYP3A4"], "inhibitor": ["CYP3A4"]},
    "erythromycin": {"substrate": ["CYP3A4"], "inhibitor": ["CYP3A4"]},
    "felodipine": {"substrate": ["CYP3A4"]},
    "fentanyl": {"substrate": ["CYP3A4"]},
    "fluconazole": {"inhibitor": ["CYP3A4", "CYP2C9", "CYP2C19"]},
    "itraconazole": {"inhibitor": ["CYP3A4"]},
    "ketoconazole": {"inhibitor": ["CYP3A4", "CYP2C9"]},
    "lovastatin": {"substrate": ["CYP3A4"]},
    "midazolam": {"substrate": ["CYP3A4"]},
    "nifedipine": {"substrate": ["CYP3A4"]},
    "pimozide": {"substrate": ["CYP3A4"]},
    "quetiapine": {"substrate": ["CYP3A4"]},
    "rifampin": {"inducer": ["CYP3A4", "CYP2C9", "CYP2C19", "CYP1A2", "CYP2B6"]},
    "ritonavir": {"substrate": ["CYP3A4"], "inhibitor": ["CYP3A4", "CYP2D6"]},
    "sildenafil": {"substrate": ["CYP3A4"]},
    "simvastatin": {"substrate": ["CYP3A4"]},
    "tacrolimus": {"substrate": ["CYP3A4"]},
    "triazolam": {"substrate": ["CYP3A4"]},
    "verapamil": {"substrate": ["CYP3A4"], "inhibitor": ["CYP3A4"]},
    # CYP2D6
    "amitriptyline": {"substrate": ["CYP2D6", "CYP1A2"]},
    "aripiprazole": {"substrate": ["CYP2D6", "CYP3A4"]},
    "atomoxetine": {"substrate": ["CYP2D6"]},
    "bupropion": {"substrate": ["CYP2B6"], "inhibitor": ["CYP2D6"]},
    "codeine": {"substrate": ["CYP2D6"]},
    "desipramine": {"substrate": ["CYP2D6"]},
    "dextromethorphan": {"substrate": ["CYP2D6"]},
    "duloxetine": {"substrate": ["CYP2D6"], "inhibitor": ["CYP2D6"]},
    "fluoxetine": {"substrate": ["CYP2D6"], "inhibitor": ["CYP2D6"]},
    "haloperidol": {"substrate": ["CYP2D6"]},
    "imipramine": {"substrate": ["CYP2D6", "CYP1A2"]},
    "metoprolol": {"substrate": ["CYP2D6"]},
    "nortriptyline": {"substrate": ["CYP2D6"]},
    "oxycodone": {"substrate": ["CYP2D6", "CYP3A4"]},
    "paroxetine": {"substrate": ["CYP2D6"], "inhibitor": ["CYP2D6"]},
    "perphenazine": {"substrate": ["CYP2D6"]},
    "propafenone": {"substrate": ["CYP2D6"]},
    "risperidone": {"substrate": ["CYP2D6"]},
    "tamoxifen": {"substrate": ["CYP2D6", "CYP3A4"]},
    "tramadol": {"substrate": ["CYP2D6", "CYP3A4"]},
    "venlafaxine": {"substrate": ["CYP2D6", "CYP3A4"]},
    # CYP2C9
    "celecoxib": {"substrate": ["CYP2C9"]},
    "diclofenac": {"substrate": ["CYP2C9"]},
    "glipizide": {"substrate": ["CYP2C9"]},
    "glyburide": {"substrate": ["CYP2C9"]},
    "ibuprofen": {"substrate": ["CYP2C9"]},
    "irbesartan": {"substrate": ["CYP2C9"]},
    "losartan": {"substrate": ["CYP2C9"]},
    "meloxicam": {"substrate": ["CYP2C9"]},
    "naproxen": {"substrate": ["CYP2C9"]},
    "phenytoin": {"substrate": ["CYP2C9", "CYP2C19"], "inducer": ["CYP3A4", "CYP2C9"]},
    "piroxicam": {"substrate": ["CYP2C9"]},
    "tolbutamide": {"substrate": ["CYP2C9"]},
    "warfarin": {"substrate": ["CYP2C9", "CYP1A2"]},
    # CYP2C19
    "clopidogrel": {"substrate": ["CYP2C19"]},
    "escitalopram": {"substrate": ["CYP2C19"]},
    "lansoprazole": {"substrate": ["CYP2C19"]},
    "omeprazole": {"substrate": ["CYP2C19"], "inhibitor": ["CYP2C19"]},
    "pantoprazole": {"substrate": ["CYP2C19"]},
    "sertraline": {"substrate": ["CYP2C19"]},
    "voriconazole": {"substrate": ["CYP2C19", "CYP3A4"], "inhibitor": ["CYP2C19", "CYP3A4", "CYP2C9"]},
    # CYP1A2
    "caffeine": {"substrate": ["CYP1A2"]},
    "clozapine": {"substrate": ["CYP1A2"]},
    "fluvoxamine": {"substrate": ["CYP1A2"], "inhibitor": ["CYP1A2", "CYP2C19"]},
    "melatonin": {"substrate": ["CYP1A2"]},
    "olanzapine": {"substrate": ["CYP1A2"]},
    "ramelteon": {"substrate": ["CYP1A2"]},
    "theophylline": {"substrate": ["CYP1A2"]},
    "tizanidine": {"substrate": ["CYP1A2"]},
    # CYP2B6
    "cyclophosphamide": {"substrate": ["CYP2B6"]},
    "efavirenz": {"substrate": ["CYP2B6"], "inducer": ["CYP2B6"]},
    "methadone": {"substrate": ["CYP2B6", "CYP3A4"]},
    "nevirapine": {"substrate": ["CYP2B6"], "inducer": ["CYP3A4", "CYP2B6"]},
    "sertraline": {"substrate": ["CYP2C19", "CYP2D6"]},
}

# ---------------------------------------------------------------------------
# UGT DATA
# Format: drug_name_lower -> {role: [ugt_enzyme, ...], note: str}
# ---------------------------------------------------------------------------

UGT_DATA = {
    # UGT1A4 substrates
    "lamotrigine": {
        "substrate": ["UGT1A4"],
        "note": "Primary glucuronidation pathway; UGT1A4 inhibition by valproate doubles lamotrigine levels",
    },
    "olanzapine": {
        "substrate": ["UGT1A4"],
        "note": "Glucuronidation via UGT1A4 and UGT1A9",
    },
    "clozapine": {
        "substrate": ["UGT1A4"],
    },
    "imipramine": {
        "substrate": ["UGT1A4"],
    },
    "trifluoperazine": {
        "substrate": ["UGT1A4"],
    },
    # UGT1A1 substrates
    "irinotecan": {
        "substrate": ["UGT1A1"],
        "note": "Active metabolite SN-38 glucuronidated by UGT1A1; UGT1A1*28 reduces clearance",
    },
    "bilirubin": {
        "substrate": ["UGT1A1"],
    },
    # UGT1A9 substrates
    "mycophenolate": {
        "substrate": ["UGT1A9"],
        "note": "Enterohepatic recycling; cyclosporine inhibits UGT1A9 → reduced mycophenolate exposure",
    },
    "propofol": {
        "substrate": ["UGT1A9"],
    },
    # UGT2B7 substrates
    "morphine": {
        "substrate": ["UGT2B7"],
        "note": "Produces morphine-6-glucuronide (active) and morphine-3-glucuronide (inactive)",
    },
    "hydromorphone": {
        "substrate": ["UGT2B7"],
    },
    "lorazepam": {
        "substrate": ["UGT2B7"],
    },
    "oxazepam": {
        "substrate": ["UGT2B7"],
    },
    "zidovudine": {
        "substrate": ["UGT2B7"],
        "note": "Valproate inhibits UGT2B7 → zidovudine glucuronidation reduced",
    },
    "naloxone": {
        "substrate": ["UGT2B7"],
    },
    "naltrexone": {
        "substrate": ["UGT2B7"],
    },
    # UGT inhibitors
    "valproate": {
        "inhibitor": ["UGT1A4", "UGT2B7"],
        "note": "Inhibits UGT1A4 (lamotrigine, olanzapine) and UGT2B7 (zidovudine, morphine); also inhibits CYP2C9",
    },
    "valproic acid": {
        "inhibitor": ["UGT1A4", "UGT2B7"],
        "note": "Same as valproate",
    },
    "probenecid": {
        "inhibitor": ["UGT1A1", "UGT2B7"],
        "note": "Inhibits multiple UGT enzymes",
    },
    "fluconazole": {
        "inhibitor": ["UGT2B7"],
    },
    # UGT inducers
    "rifampin": {
        "inducer": ["UGT1A1", "UGT1A4", "UGT2B7"],
        "note": "Broad UGT inducer; also broad CYP inducer",
    },
    "carbamazepine": {
        "inducer": ["UGT1A4"],
        "note": "Induces lamotrigine glucuronidation; reduces lamotrigine levels by ~50%",
    },
    "phenytoin": {
        "inducer": ["UGT1A4"],
        "note": "Induces lamotrigine glucuronidation; reduces lamotrigine levels",
    },
    "phenobarbital": {
        "inducer": ["UGT1A1", "UGT1A4"],
        "note": "Broad enzyme inducer; reduces lamotrigine and other UGT substrates",
    },
    "primidone": {
        "inducer": ["UGT1A4"],
        "note": "Metabolized to phenobarbital; induces lamotrigine glucuronidation",
    },
}

# ---------------------------------------------------------------------------
# NARROW THERAPEUTIC INDEX DRUGS
# ---------------------------------------------------------------------------

NARROW_TI_DRUGS = {
    "warfarin": {
        "category": "anticoagulant",
        "monitoring": "INR (target depends on indication; typical 2-3)",
        "risk": "Bleeding (supratherapeutic) or thrombosis (subtherapeutic)",
        "key_interactions": ["CYP2C9 inhibitors raise INR", "CYP2C9 inducers lower INR", "VitK intake affects INR"],
    },
    "lithium": {
        "category": "mood stabilizer",
        "monitoring": "Serum lithium level (therapeutic 0.6-1.2 mmol/L; toxicity >1.5)",
        "risk": "Neurotoxicity, nephrogenic diabetes insipidus, renal failure",
        "key_interactions": ["NSAIDs raise lithium levels", "Thiazide diuretics raise lithium levels", "ACE inhibitors raise lithium levels"],
    },
    "digoxin": {
        "category": "cardiac glycoside",
        "monitoring": "Serum digoxin level (therapeutic 0.5-2 ng/mL)",
        "risk": "Arrhythmias, bradycardia, AV block, toxicity worsened by hypokalemia",
        "key_interactions": ["P-gp inhibitors raise digoxin levels", "Amiodarone raises digoxin levels", "Quinidine raises digoxin levels"],
    },
    "phenytoin": {
        "category": "anticonvulsant",
        "monitoring": "Total phenytoin 10-20 mcg/mL; free phenytoin 1-2 mcg/mL",
        "risk": "Nystagmus, ataxia, cerebellar atrophy (supratherapeutic); seizures (subtherapeutic)",
        "key_interactions": ["Valproate displaces protein binding + inhibits metabolism", "CYP2C9 inhibitors raise phenytoin", "CYP2C9 inducers lower phenytoin"],
    },
    "theophylline": {
        "category": "bronchodilator",
        "monitoring": "Serum theophylline 10-20 mcg/mL",
        "risk": "Seizures, arrhythmias, nausea",
        "key_interactions": ["CYP1A2 inhibitors raise theophylline (ciprofloxacin, fluvoxamine)", "Smoking induces CYP1A2; cessation raises theophylline"],
    },
    "cyclosporine": {
        "category": "immunosuppressant",
        "monitoring": "Trough cyclosporine level (varies by indication and transplant type)",
        "risk": "Nephrotoxicity, hypertension, PRES (supratherapeutic); rejection (subtherapeutic)",
        "key_interactions": ["CYP3A4 inhibitors raise cyclosporine", "CYP3A4 inducers lower cyclosporine", "Inhibits UGT1A9 reducing mycophenolate"],
    },
    "tacrolimus": {
        "category": "immunosuppressant",
        "monitoring": "Trough tacrolimus level (varies by indication)",
        "risk": "Nephrotoxicity, neurotoxicity, diabetes (supratherapeutic); rejection (subtherapeutic)",
        "key_interactions": ["CYP3A4 inhibitors raise tacrolimus", "CYP3A4 inducers lower tacrolimus", "Azole antifungals markedly raise tacrolimus"],
    },
    "aminoglycosides": {
        "category": "antibiotic",
        "monitoring": "Peak and trough levels (gentamicin trough <2 mcg/mL; amikacin trough <10 mcg/mL)",
        "risk": "Nephrotoxicity, ototoxicity (dose-related and cumulative)",
        "key_interactions": ["Loop diuretics increase ototoxicity risk", "NSAIDs increase nephrotoxicity risk", "Synergistic nephrotoxicity with vancomycin"],
    },
    "lamotrigine": {
        "category": "anticonvulsant / mood stabilizer",
        "monitoring": "Serum lamotrigine level (suggested 3-15 mcg/mL; monitoring critical during pregnancy)",
        "risk": "Seizures (subtherapeutic); Stevens-Johnson syndrome/DRESS risk with rapid titration",
        "key_interactions": ["Valproate inhibits UGT1A4 → doubles lamotrigine levels", "Carbamazepine induces UGT1A4 → halves lamotrigine levels", "Oral contraceptives induce UGT1A4 → reduces lamotrigine levels"],
    },
    "carbamazepine": {
        "category": "anticonvulsant",
        "monitoring": "Serum carbamazepine 4-12 mcg/mL",
        "risk": "CNS depression, hyponatremia; autoinduction complicates dosing",
        "key_interactions": ["CYP3A4 inhibitors raise carbamazepine", "Autoinduces CYP3A4 over 2-4 weeks; doses must be escalated"],
    },
    "vancomycin": {
        "category": "antibiotic",
        "monitoring": "AUC/MIC-guided dosing preferred; trough 10-20 mcg/mL (traditional)",
        "risk": "Nephrotoxicity, ototoxicity",
        "key_interactions": ["Loop diuretics increase ototoxicity", "Aminoglycosides and NSAIDs increase nephrotoxicity"],
    },
    "methotrexate": {
        "category": "DMARD / chemotherapy",
        "monitoring": "Serum methotrexate level (high-dose protocols); LFTs, CBC, renal function",
        "risk": "Myelosuppression, hepatotoxicity, mucositis",
        "key_interactions": ["NSAIDs reduce renal elimination", "Trimethoprim additive antifolate toxicity", "Proton pump inhibitors reduce renal clearance"],
    },
    "sirolimus": {
        "category": "immunosuppressant",
        "monitoring": "Trough sirolimus level",
        "risk": "Myelosuppression, hyperlipidemia, impaired wound healing",
        "key_interactions": ["CYP3A4 and P-gp inhibitors raise sirolimus", "CYP3A4 inducers lower sirolimus"],
    },
}

# ---------------------------------------------------------------------------
# KEY DRUG INTERACTIONS DATABASE
# Format: (drug1_lower, drug2_lower) -> interaction details
# Canonical order: alphabetical by first element; lookup normalizes order.
# ---------------------------------------------------------------------------

DDI_DATABASE = {
    ("carbamazepine", "lamotrigine"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: CYP3A4 induction by carbamazepine + UGT1A4 induction by carbamazepine → accelerated lamotrigine glucuronidation",
        "effect": "Carbamazepine reduces lamotrigine plasma levels by approximately 40-50%. Seizure control may be lost when carbamazepine is started or dose is increased.",
        "direction": "carbamazepine → lamotrigine",
        "management": "Increase lamotrigine dose when adding carbamazepine. Monitor lamotrigine levels. When stopping carbamazepine, reduce lamotrigine dose to avoid toxicity.",
        "evidence": "★★★ (FDA label, multiple clinical pharmacokinetic studies)",
        "note": "This is a well-established pharmacokinetic interaction. Lamotrigine dose requirements are ~2x higher in patients on carbamazepine vs. valproate.",
    },
    ("carbamazepine", "valproate"): {
        "severity": "Moderate",
        "mechanism": "Complex bidirectional: carbamazepine induces valproate metabolism (CYP2C9); valproate inhibits carbamazepine epoxide hydrolase → carbamazepine-10,11-epoxide (toxic metabolite) accumulates",
        "effect": "Valproate raises carbamazepine-epoxide levels causing CNS toxicity (diplopia, ataxia, dizziness) even at therapeutic carbamazepine levels.",
        "direction": "bidirectional",
        "management": "Monitor carbamazepine AND carbamazepine-epoxide levels. Watch for toxicity symptoms even with therapeutic total carbamazepine.",
        "evidence": "★★★ (FDA label, pharmacokinetic studies)",
    },
    ("lamotrigine", "valproate"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: Valproate inhibits UGT1A4, the primary enzyme responsible for lamotrigine glucuronidation. This reduces lamotrigine clearance by approximately 50%.",
        "effect": "Valproate DOUBLES lamotrigine plasma levels. If lamotrigine dose is not reduced, patients face significantly elevated risk of Stevens-Johnson syndrome (SJS) and toxic epidermal necrolysis (TEN), which are potentially fatal.",
        "direction": "valproate → lamotrigine (perpetrator → victim)",
        "management": "MANDATORY dose reduction: When adding valproate to lamotrigine, reduce lamotrigine dose by 50%. Restart lamotrigine titration at lower doses. The lamotrigine starter pack for patients ON valproate uses half the standard dose and slower titration (25 mg every other day × 2 weeks, then 25 mg/day × 2 weeks).",
        "evidence": "★★★ (FDA label Box Warning, multiple clinical PK studies)",
        "note": "This is the Q927 reference interaction. Valproate is a perpetrator (UGT1A4 inhibitor); lamotrigine is the victim (UGT1A4 substrate). The clinical consequence is doubled lamotrigine levels and SJS/TEN risk. The lamotrigine FDA label carries a Black Box Warning specifically about this interaction.",
    },
    ("fluoxetine", "tramadol"): {
        "severity": "Major",
        "mechanism": "Dual mechanism: (1) Pharmacokinetic: fluoxetine inhibits CYP2D6 → reduced conversion of tramadol to active O-desmethyltramadol, reducing analgesic effect; (2) Pharmacodynamic: serotonin syndrome risk from additive serotonergic activity",
        "effect": "Serotonin syndrome (agitation, tremor, hyperthermia, tachycardia); reduced tramadol analgesia",
        "direction": "bidirectional PK+PD",
        "management": "Avoid combination. If unavoidable, monitor closely for serotonin syndrome symptoms.",
        "evidence": "★★☆ (clinical case reports and pharmacokinetic studies)",
    },
    ("rifampin", "warfarin"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: rifampin is a potent CYP2C9 inducer. Warfarin is a CYP2C9 substrate. Induction accelerates warfarin clearance.",
        "effect": "Rifampin decreases warfarin levels by 60-90%, causing subtherapeutic anticoagulation and thrombosis risk.",
        "direction": "rifampin → warfarin",
        "management": "Avoid if possible. If concurrent use required, increase warfarin dose (may need 5-10x normal dose) with very frequent INR monitoring. After stopping rifampin, reduce warfarin dose promptly (enzyme induction takes 1-4 weeks to resolve).",
        "evidence": "★★★ (FDA label, pharmacokinetic studies)",
    },
    ("simvastatin", "ketoconazole"): {
        "severity": "Contraindicated",
        "mechanism": "Pharmacokinetic: ketoconazole is a potent CYP3A4 inhibitor. Simvastatin is a CYP3A4 substrate. Inhibition markedly increases simvastatin exposure.",
        "effect": "Simvastatin AUC increases up to 20-fold, causing myopathy and rhabdomyolysis risk.",
        "direction": "ketoconazole → simvastatin",
        "management": "Contraindicated. Use pravastatin or rosuvastatin (non-CYP3A4 substrates) instead of simvastatin/lovastatin when azole antifungals are required.",
        "evidence": "★★★ (FDA label contraindication)",
    },
    ("amiodarone", "warfarin"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: amiodarone inhibits CYP2C9, reducing S-warfarin metabolism. Also inhibits CYP3A4.",
        "effect": "INR increases significantly (can double or triple). Bleeding risk.",
        "direction": "amiodarone → warfarin",
        "management": "Reduce warfarin dose by 30-50% when starting amiodarone. Monitor INR weekly for first month, then monthly. Effect persists for weeks after amiodarone discontinuation (long half-life).",
        "evidence": "★★★ (FDA label, clinical studies)",
    },
    ("clopidogrel", "omeprazole"): {
        "severity": "Moderate",
        "mechanism": "Pharmacokinetic: omeprazole inhibits CYP2C19. Clopidogrel requires CYP2C19 activation to its active metabolite.",
        "effect": "Omeprazole reduces clopidogrel active metabolite by ~40%, reducing antiplatelet effect and potentially increasing cardiovascular events.",
        "direction": "omeprazole → clopidogrel",
        "management": "Use pantoprazole (weaker CYP2C19 inhibition) or famotidine (H2 blocker, not CYP2C19 inhibitor) instead of omeprazole/esomeprazole.",
        "evidence": "★★★ (FDA black box warning, clinical outcome studies)",
    },
    ("metformin", "vancomycin"): {
        "severity": "Minor",
        "mechanism": "Pharmacokinetic: vancomycin inhibits MATE1/MATE2-K transporters, reducing renal tubular secretion of metformin",
        "effect": "Metformin levels may increase, raising lactic acidosis risk in susceptible patients",
        "direction": "vancomycin → metformin",
        "management": "Monitor renal function and for signs of metformin toxicity during co-administration",
        "evidence": "★☆☆ (in vitro data, limited clinical evidence)",
    },
    ("quinidine", "digoxin"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: quinidine inhibits P-glycoprotein (P-gp), reducing digoxin renal elimination and biliary excretion",
        "effect": "Digoxin levels increase by approximately 100% (doubles). Digoxin toxicity: bradycardia, AV block, arrhythmias",
        "direction": "quinidine → digoxin",
        "management": "Reduce digoxin dose by 30-50% when starting quinidine. Monitor digoxin levels and ECG closely.",
        "evidence": "★★★ (FDA label, pharmacokinetic studies)",
    },
    ("fluconazole", "phenytoin"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: fluconazole inhibits CYP2C9, the primary enzyme metabolizing phenytoin",
        "effect": "Phenytoin levels may increase significantly. Phenytoin toxicity: nystagmus, ataxia, confusion.",
        "direction": "fluconazole → phenytoin",
        "management": "Monitor phenytoin levels closely when adding or removing fluconazole. Dose reduction of phenytoin may be needed.",
        "evidence": "★★☆ (clinical case reports, pharmacokinetic studies)",
    },
    ("valproate", "phenytoin"): {
        "severity": "Major",
        "mechanism": "Complex: (1) valproate displaces phenytoin from protein binding → transiently increases free phenytoin; (2) valproate inhibits CYP2C9 → reduces phenytoin metabolism",
        "effect": "Total phenytoin levels may decrease (due to displacement) while free (active) phenytoin increases. Net effect is variable but free phenytoin toxicity can occur.",
        "direction": "valproate → phenytoin",
        "management": "Monitor FREE phenytoin levels (not total). Total phenytoin measurement is misleading in this interaction.",
        "evidence": "★★★ (FDA label, clinical studies)",
    },
    ("lithium", "nsaids"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: NSAIDs inhibit prostaglandin synthesis in the kidney → reduced renal blood flow → decreased lithium clearance",
        "effect": "Lithium levels increase by 20-60%. Lithium toxicity: tremor, ataxia, confusion, renal damage.",
        "direction": "NSAIDs → lithium",
        "management": "Avoid NSAIDs in lithium patients. If necessary, use short courses with close lithium level monitoring. Acetaminophen preferred for pain.",
        "evidence": "★★★ (multiple clinical studies)",
    },
    ("clarithromycin", "simvastatin"): {
        "severity": "Contraindicated",
        "mechanism": "Pharmacokinetic: clarithromycin is a potent CYP3A4 inhibitor. Simvastatin is primarily metabolized by CYP3A4.",
        "effect": "Simvastatin AUC increases markedly → rhabdomyolysis risk",
        "direction": "clarithromycin → simvastatin",
        "management": "Contraindicated. Temporarily suspend simvastatin during clarithromycin course. Use pravastatin or rosuvastatin if statin is essential during infection.",
        "evidence": "★★★ (FDA label contraindication)",
    },
    ("fluoxetine", "maois"): {
        "severity": "Contraindicated",
        "mechanism": "Pharmacodynamic: additive serotonergic activity. SSRIs + MAOIs → serotonin syndrome",
        "effect": "Serotonin syndrome: hyperthermia, agitation, tremor, hyperreflexia, autonomic instability → potentially fatal",
        "direction": "bidirectional pharmacodynamic",
        "management": "Contraindicated. Requires 5-week washout after fluoxetine (long half-life) before starting MAOIs. Requires 2-week washout after MAOI before starting fluoxetine.",
        "evidence": "★★★ (FDA black box warning)",
    },
    ("oral contraceptives", "lamotrigine"): {
        "severity": "Major",
        "mechanism": "Pharmacokinetic: ethinyl estradiol in combined oral contraceptives induces UGT1A4, accelerating lamotrigine glucuronidation",
        "effect": "Combined OCs reduce lamotrigine levels by approximately 50%. Risk of breakthrough seizures. Paradoxically, lamotrigine levels spike during pill-free week.",
        "direction": "oral contraceptives → lamotrigine",
        "management": "Increase lamotrigine dose when OC is started. Avoid pill-free intervals (use continuous dosing OC) or use progestin-only contraception. Monitor lamotrigine levels.",
        "evidence": "★★★ (FDA label, clinical PK studies)",
    },
}

# ---------------------------------------------------------------------------
# REVERSE INDEX: drug name -> all interactions it participates in
# ---------------------------------------------------------------------------

def _build_reverse_index():
    index = {}
    for (d1, d2), info in DDI_DATABASE.items():
        for drug in (d1, d2):
            if drug not in index:
                index[drug] = []
            index[drug].append(((d1, d2), info))
    return index


REVERSE_DDI_INDEX = _build_reverse_index()


# ---------------------------------------------------------------------------
# LOOKUP HELPERS
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    return name.strip().lower()


def cyp_lookup_substrate(drug: str) -> dict:
    d = _normalize(drug)
    result = {}
    for role in ("substrate", "inhibitor", "inducer"):
        enzymes = CYP_DATA.get(d, {}).get(role, [])
        if enzymes:
            result[role] = enzymes
    return result


def cyp_lookup_by_enzyme_and_role(enzyme: str, role: str) -> list:
    enzyme_upper = enzyme.upper()
    drugs = []
    for drug, roles in CYP_DATA.items():
        if role in roles and enzyme_upper in [e.upper() for e in roles[role]]:
            drugs.append(drug)
    return sorted(drugs)


def ugt_lookup(drug: str) -> dict:
    d = _normalize(drug)
    return UGT_DATA.get(d, {})


def ugt_lookup_by_enzyme_and_role(enzyme: str, role: str) -> list:
    enzyme_upper = enzyme.upper()
    result = []
    for drug, info in UGT_DATA.items():
        if role in info:
            if enzyme_upper in [e.upper() for e in info[role]]:
                entry = {"drug": drug}
                if "note" in info:
                    entry["note"] = info["note"]
                result.append(entry)
    return result


def get_interaction(drug1: str, drug2: str) -> dict | None:
    d1, d2 = _normalize(drug1), _normalize(drug2)
    # Try both orderings and common aliases
    for key in ((d1, d2), (d2, d1)):
        if key in DDI_DATABASE:
            return DDI_DATABASE[key]
    return None


def get_all_interactions(drug: str) -> list:
    d = _normalize(drug)
    interactions = REVERSE_DDI_INDEX.get(d, [])
    result = []
    for (d1, d2), info in interactions:
        other = d2 if d1 == d else d1
        result.append({"partner": other, "interaction": info})
    return result


# ---------------------------------------------------------------------------
# CLI OUTPUT FORMATTERS
# ---------------------------------------------------------------------------

def print_json(obj):
    print(json.dumps(obj, indent=2))


def format_cyp_substrate(drug: str):
    roles = cyp_lookup_substrate(drug)
    if not roles:
        print(f"No CYP data found for '{drug}'")
        return
    print(f"\nCYP roles for: {drug.title()}")
    print("=" * 50)
    for role, enzymes in roles.items():
        print(f"  {role.upper()}: {', '.join(enzymes)}")
    print()


def format_cyp_by_enzyme(enzyme: str, role: str):
    drugs = cyp_lookup_by_enzyme_and_role(enzyme, role)
    if not drugs:
        print(f"No drugs found as {role} of {enzyme}")
        return
    print(f"\n{enzyme.upper()} {role.upper()}S ({len(drugs)} found)")
    print("=" * 50)
    for d in drugs:
        print(f"  - {d}")
    print()


def format_narrow_ti():
    print("\nNARROW THERAPEUTIC INDEX DRUGS")
    print("=" * 60)
    for drug, info in NARROW_TI_DRUGS.items():
        print(f"\n{drug.title()} [{info['category']}]")
        print(f"  Monitoring : {info['monitoring']}")
        print(f"  Risk       : {info['risk']}")
        print("  Key DDIs   :")
        for interaction in info["key_interactions"]:
            print(f"    - {interaction}")
    print()


def format_ugt_substrate(drug: str):
    info = ugt_lookup(drug)
    if not info:
        print(f"No UGT data found for '{drug}'")
        return
    print(f"\nUGT data for: {drug.title()}")
    print("=" * 50)
    for role in ("substrate", "inhibitor", "inducer"):
        if role in info:
            print(f"  {role.upper()}: {', '.join(info[role])}")
    if "note" in info:
        print(f"  NOTE: {info['note']}")
    print()


def format_ugt_inhibitor(drug: str):
    """Show which UGT enzymes a drug inhibits, then list their substrates."""
    info = ugt_lookup(drug)
    if not info or "inhibitor" not in info:
        print(f"'{drug}' is not listed as a UGT inhibitor in this database")
        return
    inhibited = info["inhibitor"]
    print(f"\n{drug.title()} inhibits: {', '.join(inhibited)}")
    print("=" * 50)
    if "note" in info:
        print(f"Note: {info['note']}")
    print()
    for enzyme in inhibited:
        substrates = ugt_lookup_by_enzyme_and_role(enzyme, "substrate")
        print(f"  Substrates of {enzyme} (affected by {drug}):")
        for s in substrates:
            note = f"  [{s['note']}]" if "note" in s else ""
            print(f"    - {s['drug']}{note}")
    print()


def format_interaction(drug1: str, drug2: str):
    info = get_interaction(drug1, drug2)
    if info is None:
        print(f"\nNo interaction found between '{drug1}' and '{drug2}' in local database.")
        print("Tip: search PubMed or ChEMBL for clinical evidence.")
        return
    print(f"\nINTERACTION: {drug1.title()} + {drug2.title()}")
    print("=" * 60)
    print(f"  Severity  : {info['severity']}")
    print(f"  Direction : {info['direction']}")
    print(f"  Mechanism : {info['mechanism']}")
    print(f"  Effect    : {info['effect']}")
    print(f"  Management: {info['management']}")
    print(f"  Evidence  : {info['evidence']}")
    if "note" in info:
        print(f"  NOTE      : {info['note']}")
    print()


def format_all_interactions(drug: str):
    interactions = get_all_interactions(drug)
    if not interactions:
        print(f"\nNo interactions found for '{drug}' in local database.")
        return
    print(f"\nAll interactions for: {drug.title()} ({len(interactions)} found)")
    print("=" * 60)
    for entry in interactions:
        partner = entry["partner"]
        info = entry["interaction"]
        print(f"\n  vs. {partner.title()}")
        print(f"    Severity  : {info['severity']}")
        print(f"    Direction : {info['direction']}")
        print(f"    Mechanism : {info['mechanism'][:100]}...")
        print(f"    Management: {info['management'][:100]}...")
    print()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pharmacology reference database for drug-enzyme and DDI queries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pharmacology_ref.py --type cyp_substrate --drug "lamotrigine"
  python pharmacology_ref.py --type cyp_inhibitor --enzyme "CYP3A4"
  python pharmacology_ref.py --type cyp_inducer --enzyme "CYP2C9"
  python pharmacology_ref.py --type narrow_ti
  python pharmacology_ref.py --type ugt_substrate --drug "lamotrigine"
  python pharmacology_ref.py --type ugt_inhibitor --drug "valproate"
  python pharmacology_ref.py --type interaction --drug1 "valproate" --drug2 "lamotrigine"
  python pharmacology_ref.py --type all_interactions --drug "lamotrigine"
  python pharmacology_ref.py --type interaction --drug1 "simvastatin" --drug2 "ketoconazole"
        """,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=[
            "cyp_substrate",
            "cyp_inhibitor",
            "cyp_inducer",
            "narrow_ti",
            "ugt_substrate",
            "ugt_inhibitor",
            "interaction",
            "all_interactions",
        ],
        help="Query type",
    )
    p.add_argument("--drug", help="Drug name (for substrate/inhibitor lookups and all_interactions)")
    p.add_argument("--drug1", help="First drug (for interaction query)")
    p.add_argument("--drug2", help="Second drug (for interaction query)")
    p.add_argument("--enzyme", help="Enzyme name, e.g. CYP3A4 (for cyp_inhibitor / cyp_inducer)")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    t = args.type

    if t == "cyp_substrate":
        if not args.drug:
            parser.error("--drug required for cyp_substrate")
        if args.json:
            print_json(cyp_lookup_substrate(args.drug))
        else:
            format_cyp_substrate(args.drug)

    elif t == "cyp_inhibitor":
        if not args.enzyme:
            parser.error("--enzyme required for cyp_inhibitor")
        if args.json:
            print_json(cyp_lookup_by_enzyme_and_role(args.enzyme, "inhibitor"))
        else:
            format_cyp_by_enzyme(args.enzyme, "inhibitor")

    elif t == "cyp_inducer":
        if not args.enzyme:
            parser.error("--enzyme required for cyp_inducer")
        if args.json:
            print_json(cyp_lookup_by_enzyme_and_role(args.enzyme, "inducer"))
        else:
            format_cyp_by_enzyme(args.enzyme, "inducer")

    elif t == "narrow_ti":
        if args.json:
            print_json(NARROW_TI_DRUGS)
        else:
            format_narrow_ti()

    elif t == "ugt_substrate":
        if not args.drug:
            parser.error("--drug required for ugt_substrate")
        if args.json:
            print_json(ugt_lookup(args.drug))
        else:
            format_ugt_substrate(args.drug)

    elif t == "ugt_inhibitor":
        if not args.drug:
            parser.error("--drug required for ugt_inhibitor")
        if args.json:
            print_json(
                {
                    "inhibitor_info": ugt_lookup(args.drug),
                    "affected_substrates": {
                        enzyme: ugt_lookup_by_enzyme_and_role(enzyme, "substrate")
                        for enzyme in ugt_lookup(args.drug).get("inhibitor", [])
                    },
                }
            )
        else:
            format_ugt_inhibitor(args.drug)

    elif t == "interaction":
        if not args.drug1 or not args.drug2:
            parser.error("--drug1 and --drug2 required for interaction")
        if args.json:
            result = get_interaction(args.drug1, args.drug2)
            print_json(result if result else {"error": "not found"})
        else:
            format_interaction(args.drug1, args.drug2)

    elif t == "all_interactions":
        if not args.drug:
            parser.error("--drug required for all_interactions")
        if args.json:
            print_json(get_all_interactions(args.drug))
        else:
            format_all_interactions(args.drug)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
