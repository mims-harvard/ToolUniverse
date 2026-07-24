"""
Clinical diagnosis reference for rare-disease-diagnosis skill.

Usage:
    python clinical_patterns.py --type syndrome --name "Felty"
    python clinical_patterns.py --type differential --symptoms "RA,splenomegaly,neutropenia"
    python clinical_patterns.py --type red_flag --symptom "splenomegaly"
    python clinical_patterns.py --type occupational --exposure "asbestos"
"""

import argparse
import json
import sys

SYNDROMES = {
    "felty": {
        "name": "Felty's Syndrome",
        "triad": ["rheumatoid arthritis", "splenomegaly", "neutropenia"],
        "key_distinction": "NOT infectious — neutropenia is autoimmune, not septic",
        "misdiagnosis_traps": [
            "Splenomegaly + neutropenia mistaken for lymphoma or leukemia",
            "Recurrent infections (secondary to neutropenia) mistaken for primary immunodeficiency",
            "RA assumed inactive when joint disease quiets but hematologic disease progresses",
        ],
        "red_flags": [
            "Seropositive RA (high RF, anti-CCP) — essential for diagnosis",
            "Neutrophil count < 2.0 × 10⁹/L in RA patient",
            "Palpable spleen in long-standing RA",
            "Recurrent bacterial infections without obvious cause",
        ],
        "diagnostic_steps": [
            "1. Confirm seropositive RA (RF, anti-CCP)",
            "2. CBC with differential — absolute neutrophil count",
            "3. Abdominal exam / ultrasound for splenomegaly",
            "4. Bone marrow biopsy if needed to exclude myeloid pathology",
            "5. Rule out drug-induced neutropenia (methotrexate, gold, penicillamine)",
        ],
        "treatment_hint": "MTX or leflunomide; G-CSF for severe/recurrent infections; splenectomy rarely needed",
        "icd10": "M05.0",
        "orpha": "ORPHA:47612",
    },
    "coccidioidomycosis": {
        "name": "Coccidioidomycosis (Valley Fever)",
        "triad": ["fever", "cough", "chest pain"],
        "key_distinction": "Endemic fungal infection — travel history to SW USA, Mexico, Central/South America is ESSENTIAL",
        "misdiagnosis_traps": [
            "Pulmonary form mistaken for community-acquired pneumonia or TB",
            "Disseminated form (meningitis, bone) mistaken for bacterial meningitis or osteomyelitis",
            "Skin lesions mistaken for sarcoidosis or cutaneous TB",
            "Eosinophilia clue often overlooked",
        ],
        "red_flags": [
            "Flu-like illness + eosinophilia after travel to endemic region",
            "Erythema nodosum or erythema multiforme with respiratory symptoms",
            "Pneumonia not responding to standard antibiotics",
            "Meningitis with eosinophils in CSF",
            "Lytic bone lesions + pulmonary infiltrates",
        ],
        "diagnostic_steps": [
            "1. ALWAYS take travel/residence history (endemic: Arizona, California's Central Valley, Texas, Mexico, Central America)",
            "2. Serology: IgM (early) and IgG (complement fixation — severity marker)",
            "3. Culture of sputum/BAL (BSL-3 precautions — inform lab)",
            "4. Urine antigen for disseminated disease",
            "5. Chest CT: nodules, cavities, hilar lymphadenopathy",
        ],
        "treatment_hint": "Mild pulmonary: fluconazole or itraconazole. Severe/disseminated: amphotericin B then azole step-down. Meningitis: lifelong fluconazole.",
        "icd10": "B38",
        "orpha": None,
    },
    "sle_nephritis": {
        "name": "SLE Nephritis (Lupus Nephritis)",
        "triad": ["hematuria", "proteinuria", "hypertension"],
        "key_distinction": "vs. post-streptococcal GN: check ASO titers and complement (C3/C4 persistently low in SLE, transiently low in PSGN)",
        "misdiagnosis_traps": [
            "Post-strep GN: low C3 but ASO high, short course, resolves in weeks",
            "SLE: C3 AND C4 both low, ANA positive, multi-system involvement",
            "IgA nephropathy: normal complement, elevated IgA, no systemic features",
            "ANCA vasculitis: pauci-immune on biopsy, ANCA positive",
        ],
        "red_flags": [
            "Hematuria + proteinuria in young woman with malar rash or photosensitivity",
            "Nephrotic range proteinuria (>3.5 g/day) with systemic symptoms",
            "Complement levels (C3, C4) persistently depressed — not just transiently",
            "Positive ANA (>1:160), anti-dsDNA, anti-Smith",
            "Thrombocytopenia or hemolytic anemia alongside renal disease",
        ],
        "diagnostic_steps": [
            "1. ASO titer + anti-DNase B — if high, favors PSGN; repeat complement in 6-8 weeks",
            "2. ANA panel (ANA, anti-dsDNA, anti-Smith, anti-SSA/SSB, antiphospholipid)",
            "3. C3, C4, CH50 — persistent low favors SLE",
            "4. Urinalysis with microscopy — RBC casts = glomerulonephritis",
            "5. 24-hour urine protein or urine protein:creatinine ratio",
            "6. Renal biopsy — ISN/RPS class I-VI guides treatment",
        ],
        "treatment_hint": "Class III/IV: hydroxychloroquine + MMF/cyclophosphamide + steroids. Class V: MMF. Target remission (proteinuria <0.5 g/day).",
        "icd10": "M32.14",
        "orpha": "ORPHA:536425",
    },
    "turner": {
        "name": "Turner Syndrome",
        "triad": ["short stature", "ovarian dysgenesis / primary amenorrhea", "cardiac malformation"],
        "key_distinction": "Chromosomal (45,X or mosaic) — cardiac and renal anomalies must be screened even in mild phenotypes",
        "misdiagnosis_traps": [
            "Mosaic Turner (45,X/46,XX) has near-normal phenotype — missed if karyotype not performed",
            "Short stature attributed to growth hormone deficiency without chromosomal workup",
            "Bicuspid aortic valve/coarctation diagnosed without Turner consideration",
            "Amenorrhea attributed to hypothalamic cause without karyotype",
        ],
        "red_flags": [
            "Short stature in a girl (height >2 SD below mean) with no clear cause",
            "Webbed neck, low posterior hairline, wide-carrying angle (cubitus valgus)",
            "Bicuspid aortic valve or coarctation of aorta in a female",
            "Primary amenorrhea or premature ovarian insufficiency",
            "Shield chest, widely spaced nipples, lymphedema in neonate",
        ],
        "diagnostic_steps": [
            "1. Karyotype (at least 30 cells to detect mosaicism)",
            "2. Cardiac MRI/echo — bicuspid AV, coarctation, aortic root dilation",
            "3. Renal ultrasound — horseshoe kidney, duplicated collecting system",
            "4. Pelvic ultrasound — streak gonads",
            "5. FSH, LH (elevated in ovarian failure), estradiol",
            "6. Bone age X-ray",
            "7. Hearing evaluation — sensorineural hearing loss common",
        ],
        "treatment_hint": "Growth hormone from early childhood. Estrogen replacement at puberty (bone, cardiovascular, quality of life). Cardiac surveillance lifelong.",
        "icd10": "Q96",
        "orpha": "ORPHA:881",
    },
    "wernicke_korsakoff": {
        "name": "Wernicke-Korsakoff Syndrome",
        "triad": ["confusion / encephalopathy", "ophthalmoplegia (eye movement abnormalities)", "ataxia"],
        "key_distinction": "Wernicke's encephalopathy (acute, reversible with thiamine) progresses to Korsakoff's (chronic amnestic syndrome with confabulation if untreated)",
        "misdiagnosis_traps": [
            "Classic triad present in only 16% of cases — do NOT wait for all three",
            "Confusion attributed to alcohol intoxication/withdrawal, missing thiamine deficiency",
            "Ophthalmoplegia subtle (nystagmus only) and attributed to intoxication",
            "MRI normal in up to 50% of acute Wernicke's",
            "Korsakoff's confabulation mistaken for psychosis or dementia",
        ],
        "red_flags": [
            "ANY two of: confusion, ophthalmoplegia, ataxia in an at-risk patient",
            "Risk groups: alcohol use disorder, prolonged vomiting/starvation, bariatric surgery, malabsorption, refeeding without thiamine",
            "Nystagmus (most common eye finding), lateral gaze palsy, or complete ophthalmoplegia",
            "Confabulation: plausible but fabricated memories — pathognomonic of Korsakoff's",
            "Peripheral neuropathy + encephalopathy in malnourished patient",
        ],
        "diagnostic_steps": [
            "1. GIVE THIAMINE BEFORE GLUCOSE — IV thiamine 500 mg TID × 3 days (NEVER give dextrose first)",
            "2. Whole blood thiamine level (but do not delay treatment for result)",
            "3. MRI brain: hyperintense lesions in periaqueductal gray, mammillary bodies, thalamus (DWI/FLAIR)",
            "4. Blood glucose (hypoglycemia may coexist)",
            "5. Comprehensive metabolic panel, B12, folate",
            "6. Neuropsychological testing for memory deficits (Korsakoff's)",
        ],
        "treatment_hint": "IV thiamine STAT. Oral thiamine unreliable in alcoholics (malabsorption). Continue thiamine supplementation. Address underlying cause.",
        "icd10": "E51.2",
        "orpha": "ORPHA:900",
    },
}

# Pre-compute lowercased triads once to avoid repeating in every build_differential call.
_SYNDROME_TRIADS_LOWER = {
    key: [t.lower() for t in s["triad"]] for key, s in SYNDROMES.items()
}

OCCUPATIONAL_EXPOSURES = {
    "asbestos": {
        "diseases": ["Mesothelioma", "Asbestosis", "Pleural plaques", "Pleural effusion", "Bronchogenic carcinoma (additive with smoking)"],
        "latency": "10-40 years (mesothelioma up to 50 years)",
        "at_risk_occupations": ["Shipbuilding / ship repair", "Insulation installation", "Construction (pre-1980 buildings)", "Brake lining repair", "Boilermaking", "Mining (crocidolite / amosite)"],
        "key_findings": [
            "Pleural plaques on CT (calcified, bilateral, diaphragmatic) — pathognomonic of asbestos exposure",
            "Mesothelioma: pleural thickening + effusion + restricted lung; mesothelial cells on cytology",
            "Asbestosis: bilateral basal fibrosis, honeycombing on HRCT; ferruginous bodies on BAL",
        ],
        "diagnostic_note": "No safe level of asbestos. All-fiber types cause mesothelioma. Amphiboles (crocidolite, amosite) > chrysotile risk.",
        "workup": ["HRCT chest", "PFTs (restrictive pattern)", "Bronchoscopy + BAL", "Pleural biopsy (CT/thoracoscopy-guided)", "Calretinin, WT1, D2-40 IHC for mesothelioma"],
    },
    "silica": {
        "diseases": ["Silicosis (simple, accelerated, acute)", "Progressive massive fibrosis (PMF)", "COPD", "Lung cancer (IARC Group 1)", "Autoimmune diseases (SLE, RA, scleroderma)", "Chronic kidney disease"],
        "latency": "Simple: >10 years. Accelerated: 5-10 years. Acute: <5 years (high dose).",
        "at_risk_occupations": ["Mining / tunneling", "Sandblasting", "Quarrying", "Foundry work", "Ceramics / pottery", "Denim sandblasting (epidemic in Turkey)", "Artificial stone (engineered quartz) countertop fabrication"],
        "key_findings": [
            "Bilateral upper lobe nodules (1-10 mm) on CXR/CT",
            "Eggshell calcification of hilar/mediastinal lymph nodes — classic",
            "PMF: conglomerate upper lobe masses >1 cm",
            "Acute silicosis: alveolar proteinosis pattern (crazy paving on HRCT)",
        ],
        "diagnostic_note": "Occupational history is the key — silicosis is radiographic diagnosis. Rule out TB (silico-TB complication). Accelerated silicosis epidemic from engineered stone.",
        "workup": ["HRCT chest", "PFTs", "ANA, ANCA (autoimmune screen)", "TB screening (IGRA / TST)", "Urinalysis + creatinine"],
    },
    "coal": {
        "diseases": ["Coal workers' pneumoconiosis (CWP) / black lung", "Progressive massive fibrosis", "COPD", "Caplan syndrome (RA + large pulmonary nodules)"],
        "latency": "Simple CWP: 10+ years. PMF: earlier with higher dust levels.",
        "at_risk_occupations": ["Underground coal mining", "Surface coal mining", "Coal processing / washing", "Coal-fired power plant workers"],
        "key_findings": [
            "Small rounded opacities on CXR (ILO classification p, q, r type)",
            "PMF: bilateral upper lobe masses, may cavitate",
            "Caplan nodules: well-defined 1-5 cm nodules in setting of RA",
            "Black lung resurgence (newer mining exposures to silica-rich seams)",
        ],
        "diagnostic_note": "ILO chest X-ray classification used for grading. Differentiate from TB (coalminers at increased TB risk). MSHA-certified B-reader for X-ray interpretation.",
        "workup": ["ILO-classified CXR", "HRCT chest", "PFTs (spirometry)", "RA factor, anti-CCP (Caplan's)", "TB screening"],
    },
    "metal_smelting": {
        "diseases": ["Heavy metal poisoning (lead, arsenic, mercury, cadmium, manganese)", "Metal fume fever (zinc, copper fumes)", "Hard metal disease (cobalt)", "Nickel-induced lung cancer / nasal cancer", "Chromium-induced lung cancer / nasal ulcers"],
        "latency": "Metal fume fever: hours to days. Chronic poisoning: months to years.",
        "at_risk_occupations": ["Smelting / foundry workers", "Battery manufacturing (lead)", "Electronic waste recycling", "Welders", "Pesticide manufacturers (arsenic)", "Chloralkali plant workers (mercury)", "Hard metal (WC-Co) tooling"],
        "key_findings": {
            "lead": "Anemia + basophilic stippling, peripheral neuropathy, Burton's lines (gingival), encephalopathy; blood Pb >5 µg/dL",
            "arsenic": "Peripheral neuropathy + hyperkeratosis + Mees' lines (transverse white bands on nails) + rain-drop skin pigmentation",
            "mercury": "Erethism (excessive shyness, memory loss, irritability) + tremor + gingivitis ('mad hatter')",
            "cadmium": "Renal tubular dysfunction (proximal) + osteomalacia (Itai-itai disease) + proteinuria",
            "manganese": "Manganism: Parkinsonism-like syndrome with cock-walk gait, psychiatric symptoms; basal ganglia T1 hyperintensity on MRI",
            "cobalt": "Hard metal lung disease: giant cell interstitial pneumonitis on biopsy",
        },
        "diagnostic_note": "Collect 24-hour urine for heavy metals (not just serum). Chelation therapy depends on specific metal and severity.",
        "workup": ["Blood lead, mercury, arsenic levels", "24-hour urine arsenic, mercury, cadmium", "CBC with differential (lead: basophilic stippling)", "Nerve conduction studies", "Renal function / urinalysis", "Brain MRI (manganese)", "Chest HRCT (cobalt)"],
    },
}

RED_FLAGS = {
    "splenomegaly": {
        "symptom": "Splenomegaly",
        "differentials": [
            {
                "diagnosis": "Felty's Syndrome",
                "additional_features": ["seropositive RA", "neutropenia", "recurrent infections"],
                "key_test": "CBC + RF + anti-CCP",
                "pitfall": "Confused with infection or lymphoma",
            },
            {
                "diagnosis": "Portal hypertension (cirrhosis)",
                "additional_features": ["variceal bleeding", "ascites", "jaundice", "spider angiomata"],
                "key_test": "LFTs, platelet count, hepatic ultrasound with Doppler",
                "pitfall": "Hypersplenism causes cytopenias — may mimic hematologic disease",
            },
            {
                "diagnosis": "Lymphoma / CLL",
                "additional_features": ["lymphadenopathy", "B symptoms (fever, night sweats, weight loss)", "fatigue"],
                "key_test": "CBC + flow cytometry + CT staging + biopsy",
                "pitfall": "B symptoms overlap with infection",
            },
            {
                "diagnosis": "Visceral leishmaniasis (kala-azar)",
                "additional_features": ["massive splenomegaly", "fever", "weight loss", "travel to endemic area", "pancytopenia"],
                "key_test": "Leishmania serology / rK39 antigen / bone marrow biopsy",
                "pitfall": "Missed without travel history",
            },
            {
                "diagnosis": "Storage diseases (Gaucher, Niemann-Pick)",
                "additional_features": ["hepatomegaly", "bone pain", "cytopenias", "childhood onset"],
                "key_test": "Glucocerebrosidase enzyme assay (Gaucher), GBA sequencing",
                "pitfall": "Adult Gaucher often missed; bone crisis confused with osteomyelitis",
            },
        ],
        "urgent_workup": ["CBC with differential", "Peripheral blood smear", "LFTs", "LDH + uric acid", "Abdominal ultrasound", "Epstein-Barr virus / CMV serology"],
    },
    "neutropenia": {
        "symptom": "Neutropenia (ANC < 1.5 × 10⁹/L)",
        "differentials": [
            {
                "diagnosis": "Drug-induced neutropenia",
                "additional_features": ["recent medication start (clozapine, carbimazole, trimethoprim, methotrexate, chemotherapy)"],
                "key_test": "Medication review; stop offending drug",
                "pitfall": "Drug timeline not reviewed systematically",
            },
            {
                "diagnosis": "Felty's Syndrome",
                "additional_features": ["seropositive RA", "splenomegaly"],
                "key_test": "RF, anti-CCP, abdominal exam",
                "pitfall": "Attributed to infection rather than autoimmune cause",
            },
            {
                "diagnosis": "Autoimmune neutropenia",
                "additional_features": ["isolated neutropenia", "otherwise well", "childhood more common"],
                "key_test": "ANA, anti-neutrophil antibodies",
                "pitfall": "Often benign and self-limited in children",
            },
            {
                "diagnosis": "Large granular lymphocyte (LGL) leukemia",
                "additional_features": ["cytopenias", "splenomegaly", "recurrent infections", "RA association"],
                "key_test": "Peripheral blood flow cytometry (CD8+/CD57+ clonal T cells), TCR gene rearrangement",
                "pitfall": "Overlaps with Felty syndrome; LGL leukemia may coexist",
            },
        ],
        "urgent_workup": ["CBC with differential + peripheral smear", "Drug review", "ANA, RF, anti-CCP", "Vitamin B12, folate, copper", "Flow cytometry if persistent", "Bone marrow biopsy if ANC <0.5"],
    },
    "ophthalmoplegia": {
        "symptom": "Ophthalmoplegia / Eye movement abnormality",
        "differentials": [
            {
                "diagnosis": "Wernicke's Encephalopathy",
                "additional_features": ["confusion", "ataxia", "malnutrition / alcohol use disorder", "nystagmus"],
                "key_test": "GIVE THIAMINE FIRST — then MRI brain, blood thiamine level",
                "pitfall": "Attributed to alcohol intoxication; dextrose given before thiamine",
            },
            {
                "diagnosis": "Miller Fisher Syndrome (GBS variant)",
                "additional_features": ["ophthalmoplegia", "ataxia", "areflexia — triad", "recent infection"],
                "key_test": "Anti-GQ1b antibodies (positive in >90%), CSF albumino-cytologic dissociation",
                "pitfall": "Mistaken for Wernicke's — key: anti-GQ1b and areflexia distinguish",
            },
            {
                "diagnosis": "Myasthenia Gravis",
                "additional_features": ["ptosis", "diplopia worse with fatigue", "bulbar symptoms", "proximal limb weakness"],
                "key_test": "Anti-AChR, anti-MuSK antibodies; repetitive nerve stimulation",
                "pitfall": "Fatigable ophthalmoplegia missed; ice pack test positive",
            },
            {
                "diagnosis": "Internuclear Ophthalmoplegia (INO)",
                "additional_features": ["adduction deficit", "contralateral nystagmus", "diplopia", "MS or brainstem lesion"],
                "key_test": "MRI brain (MLF lesion), VEP",
                "pitfall": "INO in young adult — consider multiple sclerosis",
            },
        ],
        "urgent_workup": ["Thiamine 500 mg IV (before glucose)", "MRI brain + posterior fossa", "Anti-GQ1b antibodies", "AChR antibodies", "Edrophonium test (myasthenia)", "CSF analysis"],
    },
    "confabulation": {
        "symptom": "Confabulation (fabricated plausible memories)",
        "differentials": [
            {
                "diagnosis": "Korsakoff's Syndrome",
                "additional_features": ["severe anterograde amnesia", "intact procedural memory", "history of Wernicke's episode", "alcohol use disorder / malnutrition"],
                "key_test": "Detailed neuropsychological testing, MRI (mammillary body atrophy), thiamine history",
                "pitfall": "Mistaken for dementia or psychosis; confabulation not explicitly elicited",
            },
            {
                "diagnosis": "Frontotemporal Dementia",
                "additional_features": ["behavioral disinhibition", "executive dysfunction", "early onset (<65)", "language problems"],
                "key_test": "MRI (frontal/temporal atrophy), neuropsychological battery, FDG-PET",
                "pitfall": "Korsakoff's distinguished by specific amnestic profile + thiamine history",
            },
        ],
        "urgent_workup": ["Thiamine level", "MRI brain with hippocampal + mammillary body volumetry", "Neuropsychological testing (RBMT, WMS)", "B12, folate, TSH", "RPR/VDRL (neurosyphilis)"],
    },
    "erythema_nodosum": {
        "symptom": "Erythema Nodosum (tender red nodules, shins)",
        "differentials": [
            {
                "diagnosis": "Sarcoidosis (Löfgren syndrome)",
                "additional_features": ["bilateral hilar lymphadenopathy", "arthritis", "fever", "excellent prognosis"],
                "key_test": "CXR / CT chest, ACE level, BAL",
                "pitfall": "Löfgren syndrome treated conservatively — biopsy usually NOT needed",
            },
            {
                "diagnosis": "Coccidioidomycosis",
                "additional_features": ["travel to SW USA / Mexico", "respiratory symptoms", "eosinophilia"],
                "key_test": "Coccidioides serology (IgM/IgG), urine antigen",
                "pitfall": "Mistaken for sarcoidosis without travel history",
            },
            {
                "diagnosis": "Inflammatory bowel disease",
                "additional_features": ["diarrhea", "rectal bleeding", "abdominal pain", "weight loss"],
                "key_test": "Colonoscopy with biopsies, calprotectin, CRP",
                "pitfall": "Skin manifestation precedes gut symptoms in some IBD patients",
            },
            {
                "diagnosis": "Streptococcal infection",
                "additional_features": ["recent pharyngitis", "high ASO titer"],
                "key_test": "Throat culture, ASO titer, anti-DNase B",
                "pitfall": "Most common cause in children — always check ASO",
            },
        ],
        "urgent_workup": ["CXR", "ASO titer", "Coccidioides serology (if travel history)", "ACE level", "ANA", "Stool culture / calprotectin", "Tuberculin skin test / IGRA"],
    },
    "short_stature": {
        "symptom": "Short Stature in Females (>2 SD below mean)",
        "differentials": [
            {
                "diagnosis": "Turner Syndrome",
                "additional_features": ["ovarian failure", "cardiac anomalies", "webbed neck", "cubitus valgus", "learning differences"],
                "key_test": "Karyotype (minimum 30 cells), FSH/LH/estradiol, cardiac echo",
                "pitfall": "Mosaic Turner underdiagnosed; karyotype not ordered for 'short but otherwise normal' girls",
            },
            {
                "diagnosis": "Growth Hormone Deficiency",
                "additional_features": ["delayed bone age", "decreased IGF-1", "normal body proportions"],
                "key_test": "IGF-1, IGFBP-3, GH stimulation test, MRI pituitary",
                "pitfall": "Turner excluded if chromosomes not checked",
            },
            {
                "diagnosis": "Hypothyroidism",
                "additional_features": ["fatigue", "constipation", "delayed bone age", "elevated TSH"],
                "key_test": "TSH, free T4",
                "pitfall": "Acquired hypothyroidism in girls — easily treatable cause of growth failure",
            },
            {
                "diagnosis": "Celiac Disease",
                "additional_features": ["failure to thrive", "diarrhea", "anemia", "delayed puberty"],
                "key_test": "Anti-tTG IgA, total IgA, duodenal biopsy",
                "pitfall": "Silent celiac (no GI symptoms) presents with short stature only",
            },
        ],
        "urgent_workup": ["Karyotype (females)", "Bone age X-ray", "TSH + free T4", "IGF-1, IGFBP-3", "CBC, CMP", "Anti-tTG IgA + total IgA", "FSH, LH, estradiol"],
    },
    "hematuria_proteinuria": {
        "symptom": "Hematuria + Proteinuria (nephritic/nephrotic syndrome)",
        "differentials": [
            {
                "diagnosis": "SLE Nephritis",
                "additional_features": ["young woman", "malar rash", "photosensitivity", "arthritis", "persistent low C3/C4"],
                "key_test": "ANA, anti-dsDNA, complement (C3/C4), renal biopsy",
                "pitfall": "Mistaken for PSGN; ASO titers and persistent complement depression distinguish",
            },
            {
                "diagnosis": "Post-streptococcal GN (PSGN)",
                "additional_features": ["2-3 weeks after strep throat / skin infection", "periorbital edema", "hypertension", "HIGH ASO titers", "TRANSIENT low C3"],
                "key_test": "ASO titer, anti-DNase B, C3 (normalizes in 6-8 weeks)",
                "pitfall": "Persistent low complement or positive ANA → SLE, not PSGN",
            },
            {
                "diagnosis": "IgA Nephropathy",
                "additional_features": ["synpharyngitic hematuria (during illness, not 2-3 weeks after)", "normal complement", "male predominance"],
                "key_test": "Serum IgA, renal biopsy (mesangial IgA deposits on IF)",
                "pitfall": "Timing of hematuria relative to infection is key (concurrent vs. delayed)",
            },
            {
                "diagnosis": "ANCA Vasculitis (GPA/MPA)",
                "additional_features": ["rapidly progressive GN", "pulmonary hemorrhage", "sinusitis", "weight loss"],
                "key_test": "c-ANCA/p-ANCA (PR3/MPO), renal biopsy (pauci-immune)",
                "pitfall": "Rapidly progressive — act urgently; delay causes permanent renal loss",
            },
        ],
        "urgent_workup": ["Urinalysis with microscopy (RBC casts)", "24-h urine protein or Pr:Cr ratio", "ANA, anti-dsDNA, C3, C4", "ASO titer, anti-DNase B", "ANCA (PR3/MPO)", "Renal biopsy if progressive"],
    },
}


def _header(title: str) -> list[str]:
    bar = "=" * 60
    return [f"\n{bar}", f"  {title}", bar]


def _fuzzy_find(query: str, mapping: dict, name_field: str) -> tuple[str, dict] | tuple[None, None]:
    """Return (key, entry) for the first entry whose key or name_field contains query."""
    q = query.lower()
    for key, entry in mapping.items():
        if q in key or q in entry[name_field].lower():
            return key, entry
    return None, None


def _require_arg(value: str | None, flag: str, query_type: str) -> None:
    if not value:
        print(f"Error: {flag} required for --type {query_type}", file=sys.stderr)
        sys.exit(1)


def build_differential(symptoms_str: str) -> dict:
    symptoms = [s.strip().lower() for s in symptoms_str.split(",")]
    matches = []
    for key, syndrome in SYNDROMES.items():
        triad_lower = _SYNDROME_TRIADS_LOWER[key]
        matched = [s for s in symptoms if any(s in t or t in s for t in triad_lower)]
        if matched:
            matches.append({
                "syndrome": syndrome["name"],
                "matched_features": matched,
                "match_count": len(matched),
                "triad": syndrome["triad"],
                "key_distinction": syndrome["key_distinction"],
                "top_diagnostic_step": syndrome["diagnostic_steps"][0] if syndrome["diagnostic_steps"] else "",
                "icd10": syndrome.get("icd10"),
                "orpha": syndrome.get("orpha"),
            })
    matches.sort(key=lambda x: x["match_count"], reverse=True)
    return {
        "input_symptoms": symptoms,
        "matched_syndromes": matches,
        "note": "Differential built from syndrome triad matching. Use --type red_flag for symptom-specific differentials.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clinical diagnosis reference for rare-disease-diagnosis skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["syndrome", "differential", "red_flag", "occupational", "list"],
        help=(
            "Query type: "
            "'syndrome' (look up a named syndrome), "
            "'differential' (build diff from symptom list), "
            "'red_flag' (red-flag analysis for a single symptom), "
            "'occupational' (occupational exposure patterns), "
            "'list' (list all available items)"
        ),
    )
    parser.add_argument("--name", help="Syndrome name (for --type syndrome), partial match supported")
    parser.add_argument(
        "--symptoms",
        help="Comma-separated symptoms for --type differential (e.g. 'RA,splenomegaly,neutropenia')",
    )
    parser.add_argument("--symptom", help="Single symptom for --type red_flag")
    parser.add_argument("--exposure", help="Occupational exposure agent for --type occupational")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    return parser.parse_args()


def format_syndrome(s: dict) -> str:
    lines = _header(s["name"]) + [
        f"\nTRIAD: {' + '.join(s['triad'])}",
        f"\nKEY DISTINCTION:\n  {s['key_distinction']}",
        "\nMISDIAGNOSIS TRAPS:",
    ]
    for trap in s["misdiagnosis_traps"]:
        lines.append(f"  ! {trap}")
    lines.append("\nRED FLAGS:")
    for flag in s["red_flags"]:
        lines.append(f"  >> {flag}")
    lines.append("\nDIAGNOSTIC STEPS:")
    for step in s["diagnostic_steps"]:
        lines.append(f"  {step}")
    lines += [
        f"\nTREATMENT HINT:\n  {s['treatment_hint']}",
        f"\nICD-10: {s.get('icd10', 'N/A')}  |  ORPHA: {s.get('orpha', 'N/A')}",
        "",
    ]
    return "\n".join(lines)


def format_occupational(key: str, data: dict) -> str:
    lines = _header(f"Occupational Exposure: {key.upper()}") + [
        f"\nDISEASES: {', '.join(data['diseases'])}",
        f"\nLATENCY: {data['latency']}",
        "\nAT-RISK OCCUPATIONS:",
    ]
    for occ in data["at_risk_occupations"]:
        lines.append(f"  - {occ}")
    lines.append("\nKEY CLINICAL FINDINGS:")
    findings = data["key_findings"]
    if isinstance(findings, list):
        for f in findings:
            lines.append(f"  - {f}")
    else:
        for metal, finding in findings.items():
            lines.append(f"  [{metal.upper()}] {finding}")
    lines += [
        f"\nDIAGNOSTIC NOTE:\n  {data['diagnostic_note']}",
        "\nWORKUP:",
    ]
    for w in data["workup"]:
        lines.append(f"  - {w}")
    return "\n".join(lines)


def format_red_flag(data: dict) -> str:
    lines = _header(f"Red-Flag Analysis: {data['symptom']}") + ["\nDIFFERENTIAL DIAGNOSIS:"]
    for i, d in enumerate(data["differentials"], 1):
        lines.append(f"\n  {i}. {d['diagnosis']}")
        lines.append(f"     Additional features: {', '.join(d['additional_features'])}")
        lines.append(f"     Key test: {d['key_test']}")
        lines.append(f"     Pitfall: {d['pitfall']}")
    lines.append("\nURGENT WORKUP:")
    for w in data["urgent_workup"]:
        lines.append(f"  - {w}")
    return "\n".join(lines)


def format_differential(result: dict) -> str:
    lines = _header(f"Differential for: {', '.join(result['input_symptoms'])}")
    if not result["matched_syndromes"]:
        lines.append("\n  No syndrome triad matches found. Try --type red_flag for individual symptoms.")
    for m in result["matched_syndromes"]:
        lines.append(f"\n  [{m['match_count']} match(es)] {m['syndrome']}")
        lines.append(f"  Triad: {' + '.join(m['triad'])}")
        lines.append(f"  Matched on: {', '.join(m['matched_features'])}")
        lines.append(f"  Key distinction: {m['key_distinction']}")
        lines.append(f"  First step: {m['top_diagnostic_step']}")
        if m.get("orpha"):
            lines.append(f"  ORPHA: {m['orpha']}  ICD-10: {m.get('icd10', 'N/A')}")
    lines.append(f"\n  Note: {result['note']}")
    return "\n".join(lines)


def list_all() -> str:
    lines = ["\n=== SYNDROMES ==="]
    for key, s in SYNDROMES.items():
        lines.append(f"  {key:25s} → {s['name']}: {' + '.join(s['triad'])}")
    lines.append("\n=== OCCUPATIONAL EXPOSURES ===")
    for key, data in OCCUPATIONAL_EXPOSURES.items():
        lines.append(f"  {key:25s} → {', '.join(data['diseases'][:2])} ...")
    lines.append("\n=== RED-FLAG SYMPTOMS ===")
    for key, data in RED_FLAGS.items():
        lines.append(f"  {key:25s} → {data['symptom']}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    if args.type == "list":
        result_text = list_all()
        result_data = {
            "syndromes": list(SYNDROMES.keys()),
            "occupational": list(OCCUPATIONAL_EXPOSURES.keys()),
            "red_flags": list(RED_FLAGS.keys()),
        }

    elif args.type == "syndrome":
        _require_arg(args.name, "--name", "syndrome")
        _, syndrome = _fuzzy_find(args.name, SYNDROMES, "name")
        if syndrome is None:
            print(f"Error: No syndrome found matching '{args.name}'. Try --type list.", file=sys.stderr)
            sys.exit(1)
        result_text = format_syndrome(syndrome)
        result_data = syndrome

    elif args.type == "differential":
        _require_arg(args.symptoms, "--symptoms", "differential")
        result_data = build_differential(args.symptoms)
        result_text = format_differential(result_data)

    elif args.type == "red_flag":
        _require_arg(args.symptom, "--symptom", "red_flag")
        symptom_norm = args.symptom.lower().replace(" ", "_")
        _, data = _fuzzy_find(symptom_norm, RED_FLAGS, "symptom")
        if data is None:
            print(f"Error: No red-flag entry found for '{args.symptom}'. Try --type list.", file=sys.stderr)
            sys.exit(1)
        result_text = format_red_flag(data)
        result_data = data

    else:  # occupational
        _require_arg(args.exposure, "--exposure", "occupational")
        exp_lower = args.exposure.lower()
        exp_key, exp_data = _fuzzy_find(exp_lower, OCCUPATIONAL_EXPOSURES, "diseases")
        # _fuzzy_find matches on diseases[0] via name_field — but diseases is a list, not a string.
        # Fall back to key-only match if name_field lookup doesn't apply cleanly.
        if exp_data is None:
            for key, data in OCCUPATIONAL_EXPOSURES.items():
                if exp_lower in key or exp_lower in " ".join(data["diseases"]).lower():
                    exp_key, exp_data = key, data
                    break
        if exp_data is None:
            print(f"Error: No exposure entry found for '{args.exposure}'. Try --type list.", file=sys.stderr)
            sys.exit(1)
        result_text = format_occupational(exp_key, exp_data)
        result_data = exp_data

    if args.format == "json":
        print(json.dumps(result_data, indent=2, default=str))
    else:
        print(result_text)


if __name__ == "__main__":
    main()
