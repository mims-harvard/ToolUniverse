# Network Pharmacology Score Reference

## Score Components (0-100 total)

### Network Proximity (0-35 points)
- Strong proximity (Z < -2, p < 0.01): 35 points
- Moderate proximity (Z < -1, p < 0.05): 20 points
- Weak proximity (Z < -0.5): 10 points
- No proximity: 0 points

### Clinical Evidence (0-25 points)
- Approved for related indication: 25 points
- Active clinical trials: 15 points
- Completed trials with positive results: 10 points
- Preclinical only: 5 points

### Target-Disease Association (0-20 points)
- Strong genetic evidence (GWAS, rare variants): 20 points
- Moderate evidence (pathways, literature): 12 points
- Weak evidence (computational only): 5 points

### Safety Profile (0-10 points)
- FDA-approved, favorable safety: 10 points
- Known manageable adverse events: 7 points
- Significant safety concerns: 3 points
- Black box warning relevant to indication: 0 points

### Mechanism Plausibility (0-10 points)
- Clear pathway mechanism with functional evidence: 10 points
- Indirect mechanism via network neighbors: 6 points
- Purely computational prediction: 2 points

---

## Priority Tiers

| Score | Tier | Recommendation |
|-------|------|----------------|
| **80-100** | Tier 1 | High repurposing potential - proceed with experimental validation |
| **60-79** | Tier 2 | Good potential - needs mechanistic validation |
| **40-59** | Tier 3 | Moderate potential - high-risk/high-reward, needs extensive validation |
| **0-39** | Tier 4 | Low potential - consider alternative approaches |

---

## Evidence Grading System

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | [T1] | Human clinical proof, regulatory evidence | FDA-approved indication, Phase III trial, patient genomics |
| **T2** | [T2] | Functional experimental evidence | Bioactivity data (IC50 < 1 uM), CRISPR screen, animal model |
| **T3** | [T3] | Association/computational evidence | GWAS hit, network proximity, pathway enrichment, expression |
| **T4** | [T4] | Prediction, annotation, text-mining | AlphaFold prediction, database annotation, literature co-mention |

---

## Score Calculation Details

### 1. Network Proximity Score (0-35)
- Count direct drug target <-> disease gene interactions in PPI
- Count shared PPI partners
- Count shared pathways
- Map to Z-score equivalent based on overlap significance

### 2. Clinical Evidence Score (0-25)
- Search clinical trials for drug-disease pair
- Check approved indications for related diseases
- Check max clinical trial phase

### 3. Target-Disease Association Score (0-20)
- Average OpenTargets association score for drug targets in disease
- Weight by evidence type (genetic > functional > computational)

### 4. Safety Score (0-10)
- FDA approval status (+5)
- Black box warning (-3)
- Death reports proportion
- Off-target count penalty

### 5. Mechanism Plausibility Score (0-10)
- Known mechanism for related indication (+5)
- Pathway evidence (+3)
- Network path length to disease module (+2)

Total: sum of components (0-100)
