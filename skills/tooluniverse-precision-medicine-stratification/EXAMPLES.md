# Precision Medicine Stratification - Examples

## Example 1: Breast Cancer with BRCA1 Mutation

**Input**:
```
Stratify this breast cancer patient: BRCA1 pathogenic variant (c.68_69delAG), ER+/HER2-, stage IIA, age 45, premenopausal. Family history: mother had ovarian cancer.
```

**Expected Analysis Flow**:
1. Disease: Breast carcinoma (EFO_0000305), Category: CANCER
2. BRCA1 c.68_69delAG -> ClinVar pathogenic (185del AG, founder mutation)
3. Molecular subtype: Luminal B, BRCA1+
4. Cancer risk: Stage IIA moderate, BRCA1 high penetrance
5. PGx: Check CYP2D6 for tamoxifen metabolism
6. Treatment: Platinum chemo benefit, PARP inhibitor eligible (olaparib/talazoparib)
7. Guideline: NCCN recommends genetic counseling, PARP inhibitor consideration
8. Trials: BRCA1+ breast cancer trials, PARP combination trials

**Expected Score**: ~55-65 (HIGH)
- Genetic: 30 (pathogenic BRCA1)
- Clinical: 15 (stage IIA)
- Molecular: 15 (BRCA1-associated features)
- PGx: depends on CYP2D6

**Key Recommendations**:
- 1st line: Surgery + chemotherapy (platinum-based benefit), endocrine therapy (if CYP2D6 normal: tamoxifen, if PM: aromatase inhibitor + ovarian suppression)
- Consider: PARP inhibitor (olaparib) per NCCN guidelines for BRCA+ breast cancer
- Risk-reducing surgery discussion (bilateral mastectomy, BSO)
- Family genetic counseling recommended

---

## Example 2: Type 2 Diabetes with PGx Concern

**Input**:
```
Precision medicine stratification: Type 2 diabetes, HbA1c 8.5%, CYP2C19 *2/*2 poor metabolizer, also on clopidogrel for CAD stent placed 3 months ago. Age 62, male, BMI 32, eGFR 65.
```

**Expected Analysis Flow**:
1. Disease: T2D (EFO_0001360) + CAD comorbidity, Category: METABOLIC
2. Genetic risk: Check T2D GWAS variants (TCF7L2, etc.)
3. Clinical risk: HbA1c 8.5% = high, CKD stage 2, obesity
4. CRITICAL PGx: CYP2C19 *2/*2 = poor metabolizer -> clopidogrel INEFFECTIVE
5. PharmGKB: CYP2C19 PM -> switch to ticagrelor or prasugrel (URGENT)
6. Comorbidity: T2D + CAD + CKD = high composite risk
7. T2D treatment: Consider SGLT2 inhibitors (cardio/renal benefit), metformin adjust for eGFR

**Expected Score**: ~55-65 (HIGH)
- Genetic: 15 (T2D polygenic risk, no monogenic)
- Clinical: 25 (HbA1c 8.5, CKD, CAD comorbidity)
- Molecular: 10 (polygenic T2D)
- PGx: 8 (CYP2C19 PM - CRITICAL for clopidogrel)

**Key Recommendations**:
- URGENT: Switch clopidogrel to ticagrelor 90mg BID or prasugrel 10mg daily (CYP2C19 PM)
- T2D: SGLT2 inhibitor (empagliflozin/dapagliflozin) for cardio-renal benefit
- Continue metformin (adjust for eGFR 65)
- Monitor: HbA1c q3 months, eGFR q6 months, platelet function test

---

## Example 3: NSCLC with Comprehensive Molecular Data

**Input**:
```
NSCLC adenocarcinoma patient: EGFR L858R mutation, TMB 25 mut/Mb, PD-L1 TPS 80%, stage IV with brain metastases, age 58, female, never-smoker. No T790M. What is the best treatment strategy?
```

**Expected Analysis Flow**:
1. Disease: NSCLC (EFO_0003060), Category: CANCER, Stage IV
2. EGFR L858R: Actionable driver mutation -> EGFR TKI eligible
3. TMB 25: TMB-high -> pembrolizumab eligible (tissue-agnostic)
4. PD-L1 80%: High PD-L1 -> ICI eligible
5. Brain mets: Osimertinib has CNS penetration (preferred EGFR TKI)
6. Conflict resolution: EGFR mutant NSCLC responds poorly to ICI alone
7. Treatment hierarchy: EGFR TKI first (osimertinib), ICI on progression

**Expected Score**: ~75-85 (VERY HIGH)
- Genetic: 25 (EGFR driver mutation)
- Clinical: 28 (stage IV, brain mets)
- Molecular: 20 (actionable EGFR + high TMB/PD-L1)
- PGx: 2 (no specific PGx concern for osimertinib)

**Key Recommendations**:
- 1st line: Osimertinib 80mg daily (preferred for EGFR L858R, CNS penetration)
- 2nd line (on progression): Check T790M resistance. If T790M+: already on osimertinib. If C797S or other: chemotherapy + anti-VEGF
- 3rd line: Consider ICI-based regimen or clinical trial
- Brain mets: SRS/WBRT if symptomatic, osimertinib often controls CNS disease
- Monitor: CT chest/brain q3 months, ctDNA liquid biopsy for resistance

---

## Example 4: Cardiovascular Risk with Pharmacogenomics

**Input**:
```
Cardiovascular risk stratification: LDL 190 mg/dL, total cholesterol 280, HDL 42, SLCO1B1*5 heterozygous (rs4149056 TC), family history of MI (father at age 48, brother at age 52). Age 50, male, non-smoker, BP 135/85.
```

**Expected Analysis Flow**:
1. Disease: CAD/FH evaluation (EFO_0001645), Category: CVD
2. Genetic: Check LDLR, APOB, PCSK9 for familial hypercholesterolemia
3. LDL 190 + family hx: Possible FH (Dutch Lipid Clinic Score)
4. ASCVD risk: Calculate based on age, sex, BP, lipids, family hx
5. PGx: SLCO1B1*5 hetero -> moderate statin myopathy risk (simvastatin most affected)
6. Treatment: Use rosuvastatin (lower SLCO1B1 interaction) or pravastatin
7. Consider PCSK9 inhibitor if LDL not at goal with statin alone

**Expected Score**: ~50-60 (HIGH)
- Genetic: 20 (family hx, possible FH, pending genetic confirmation)
- Clinical: 22 (LDL 190, family hx premature CVD, borderline BP)
- Molecular: 10 (pending FH gene testing)
- PGx: 5 (SLCO1B1*5 hetero -> statin selection impact)

**Key Recommendations**:
- Genetic testing for LDLR, APOB, PCSK9 (FH cascade screening)
- Statin: Rosuvastatin 20-40mg (preferred over simvastatin/atorvastatin due to SLCO1B1*5)
- If LDL not at goal (<70mg/dL for high risk): Add ezetimibe, then PCSK9 inhibitor
- Lifestyle: Mediterranean diet, exercise, BP management
- Monitor: Lipid panel q6 weeks until at goal, then q6-12 months. CK if muscle symptoms

---

## Example 5: Rare Disease (Marfan Syndrome)

**Input**:
```
Evaluate this patient for Marfan syndrome: FBN1 c.4082G>A (p.Cys1361Tyr) variant, tall stature (6'4"), arachnodactyly, aortic root diameter 4.2cm (Z-score 3.5), mild mitral valve prolapse, myopia. Age 28, male.
```

**Expected Analysis Flow**:
1. Disease: Marfan syndrome (Orphanet_558), Category: RARE/MONOGENIC
2. FBN1 c.4082G>A: Check ClinVar for pathogenicity (cysteine substitution in cbEGF domain)
3. Phenotype: Meets Ghent criteria (aortic Z>2 + FBN1 mutation = Marfan confirmed)
4. Aortic risk: 4.2cm root -> monitor closely, surgery if >5.0cm or rapid growth
5. No PGx relevant for beta-blocker/ARB therapy
6. Genetic counseling: Autosomal dominant, 50% recurrence risk

**Expected Score**: ~55-65 (HIGH)
- Genetic: 30 (pathogenic FBN1 mutation)
- Clinical: 18 (aortic dilation, MVP, but not yet surgical threshold)
- Molecular: 12 (cbEGF domain mutation = moderate-severe spectrum)
- PGx: 0 (beta-blockers/ARBs: no significant PGx)

**Key Recommendations**:
- Diagnosis: Confirmed Marfan syndrome (Ghent criteria met)
- 1st line: Losartan or beta-blocker (atenolol) for aortic root protection
- Monitoring: Annual echo for aortic root (more frequent if growing), ophthalmology annual
- Surgery threshold: Aortic root >5.0cm, or growth >0.5cm/year, or family hx of dissection
- Genetic counseling: AD inheritance, 50% risk to offspring
- Activity restrictions: Avoid competitive sports, heavy lifting, isometric exercise

---

## Example 6: Alzheimer's Risk Assessment

**Input**:
```
Precision medicine risk assessment for Alzheimer's: APOE e4/e4 homozygous, age 55, female, family history of early-onset Alzheimer's (mother at 62, maternal aunt at 65). No symptoms currently. Cognitive screening normal.
```

**Expected Analysis Flow**:
1. Disease: Alzheimer disease (MONDO_0004975), Category: NEUROLOGICAL
2. APOE e4/e4: Highest genetic risk (10-15x risk vs e3/e3)
3. Family history: Strong positive (first-degree, early onset)
4. Check: APP, PSEN1, PSEN2 for familial early-onset AD genes
5. Currently asymptomatic: Primary prevention window
6. Emerging therapies: Anti-amyloid antibodies (lecanemab, donanemab) in early AD
7. PGx: Check CYP2D6 for cholinesterase inhibitor metabolism (future use)

**Expected Score**: ~60-72 (HIGH)
- Genetic: 35 (APOE e4/e4 = highest genetic risk)
- Clinical: 15 (strong family hx, female sex, but currently asymptomatic)
- Molecular: 15 (APOE genotype + possible additional risk alleles)
- PGx: 2 (no current medications to evaluate)

**Key Recommendations**:
- Risk tier: HIGH (not yet Very High because currently asymptomatic)
- Prevention: Cardiovascular risk factor control (exercise, diet, BP, diabetes prevention)
- Monitoring: Cognitive screening annually, consider amyloid PET or CSF biomarkers at age 60
- Consider: Clinical trial enrollment for AD prevention studies (A4 study type)
- Genetic counseling: Discuss APOE implications, testing for APP/PSEN1/PSEN2
- Emerging: Anti-amyloid therapies (lecanemab) if/when MCI develops
- Lifestyle: Mediterranean diet, aerobic exercise, cognitive engagement, sleep hygiene
