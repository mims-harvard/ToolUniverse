# Drug Target Validation - Scoring Criteria

Detailed scoring matrices, evidence grading, and priority tier definitions for the Target Validation Score (0-100).

---

## Score Components (Total: 0-100)

### Disease Association (0-30 points)

| Sub-dimension | Range | Description |
|---------------|-------|-------------|
| Genetic evidence | 0-10 | GWAS, rare variants, somatic mutations |
| Literature evidence | 0-10 | Publications, clinical studies |
| Pathway evidence | 0-10 | Disease pathway involvement |

**Genetic Evidence (0-10)**:
- GWAS hits for specific disease: +3 per significant locus (max 6)
- Rare variant evidence (ClinVar pathogenic): +2
- Somatic mutations in disease: +2
- pLI > 0.9 (essential gene): +2

**Literature Evidence (0-10)**:
- >100 publications on target+disease: 10
- 50-100 publications: 7
- 10-50 publications: 5
- 1-10 publications: 3
- 0 publications: 0

**Pathway Evidence (0-10)**:
- OpenTargets overall score > 0.8: 10
- Score 0.5-0.8: 7
- Score 0.2-0.5: 4
- Score < 0.2: 1

---

### Druggability (0-25 points)

| Sub-dimension | Range | Description |
|---------------|-------|-------------|
| Structural tractability | 0-10 | Structure quality, binding pockets |
| Chemical matter | 0-10 | Known compounds, bioactivity data |
| Target class | 0-5 | Validated target family bonus |

**Structural Tractability (0-10)**:
- High-res co-crystal structure with ligand: 10
- PDB structure available, pockets detected: 7
- AlphaFold only, confident pocket prediction: 5
- AlphaFold low confidence / no structure: 2
- No structural data: 0

**Chemical Matter (0-10)**:
- Known drug-like compounds (IC50 < 100nM): 10
- Tool compounds (IC50 < 1uM): 7
- HTS hits only (IC50 > 1uM): 4
- No known ligands: 0

**Target Class Bonus (0-5)**:
- Validated druggable family (kinase, GPCR, nuclear receptor): 5
- Enzyme, ion channel: 4
- Protein-protein interaction, transporter: 2
- Novel/unknown class: 0

---

### Safety Profile (0-20 points)

| Sub-dimension | Range | Description |
|---------------|-------|-------------|
| Tissue expression selectivity | 0-5 | Expression in critical tissues |
| Genetic validation | 0-10 | Knockout phenotypes, human genetics |
| Known adverse events | 0-5 | Safety signals from modulators |

**Tissue Expression Selectivity (0-5)**:
- Target restricted to disease tissue: 5
- Low expression in heart/liver/kidney/brain: 4
- Moderate expression in 1-2 critical tissues: 2
- High expression in multiple critical tissues: 0

**Genetic Validation (0-10)**:
- Mouse KO viable, no severe phenotype: 10
- Mouse KO viable with mild phenotype: 7
- Mouse KO has concerning phenotype: 3
- Mouse KO lethal: 0
- No KO data, low pLI (<0.5): 5
- No KO data, high pLI (>0.9): 2

**Known Adverse Events (0-5)**:
- No known safety signals: 5
- Mild, manageable ADRs: 3
- Serious ADRs reported: 1
- Black box warning or drug withdrawal: 0

---

### Clinical Precedent (0-15 points)

- FDA-approved drug for SAME disease: 15
- FDA-approved drug for DIFFERENT disease: 12
- Phase 3 clinical trial: 10
- Phase 2 clinical trial: 7
- Phase 1 clinical trial: 5
- Preclinical compounds only: 3
- No clinical development: 0

**Adjustment factors**:
- Failed clinical program for safety: -3
- Drug withdrawal: -5
- Multiple approved drugs (validated class): +2

---

### Validation Evidence (0-10 points)

**Functional Studies (0-5)**:
- CRISPR KO shows disease-relevant phenotype: 5
- siRNA knockdown shows phenotype: 4
- Biochemical assay validates mechanism: 3
- Overexpression study only: 2
- No functional data: 0

**Disease Models (0-5)**:
- Patient-derived xenograft (PDX) response: 5
- Genetically engineered mouse model: 4
- Cell line model: 3
- In silico model only: 1
- No model data: 0

---

## Priority Tiers

| Score | Tier | Recommendation |
|-------|------|----------------|
| **80-100** | Tier 1 | Highly validated - proceed with confidence |
| **60-79** | Tier 2 | Good target - needs focused validation |
| **40-59** | Tier 3 | Moderate risk - significant validation needed |
| **0-39** | Tier 4 | High risk - consider alternatives |

---

## Evidence Grading System

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | [T1] | Direct mechanistic, human clinical proof | FDA-approved drug, crystal structure with mechanism, patient mutation |
| **T2** | [T2] | Functional studies, model organism | siRNA phenotype, mouse KO, biochemical assay, CRISPR screen |
| **T3** | [T3] | Association, screen hits, computational | GWAS hit, DepMap essentiality, expression correlation |
| **T4** | [T4] | Mention, review, text-mined, predicted | Review article, database annotation, AlphaFold prediction |

---

## Score Calculation (Pseudocode)

```python
def calculate_validation_score(phase_results):
    score = {
        'disease_genetic': 0,      # 0-10
        'disease_literature': 0,   # 0-10
        'disease_pathway': 0,      # 0-10
        'drug_structural': 0,      # 0-10
        'drug_chemical': 0,        # 0-10
        'drug_class': 0,           # 0-5
        'safety_expression': 0,    # 0-5
        'safety_genetic': 0,       # 0-10
        'safety_adverse': 0,       # 0-5
        'clinical': 0,             # 0-15
        'validation_functional': 0, # 0-5
        'validation_models': 0,    # 0-5
    }
    total = sum(score.values())

    if total >= 80:
        tier, rec = "Tier 1", "GO - Highly validated target"
    elif total >= 60:
        tier, rec = "Tier 2", "CONDITIONAL GO - Needs focused validation"
    elif total >= 40:
        tier, rec = "Tier 3", "CAUTION - Significant validation needed"
    else:
        tier, rec = "Tier 4", "NO-GO - Consider alternatives"

    return total, tier, rec, score
```

---

## Example Scores

### EGFR for NSCLC (well-validated target)
- Disease Association: ~28/30 (strong genetic + pathway + literature)
- Druggability: ~24/25 (kinase, many structures, abundant compounds)
- Safety: ~14/20 (widely expressed but manageable toxicity)
- Clinical Precedent: 15/15 (multiple approved drugs)
- Validation Evidence: ~9/10 (extensive functional data)
- **Total: ~90/100 = Tier 1**

### Novel understudied kinase
- Disease Association: ~8/30 (limited GWAS, few publications)
- Druggability: ~15/25 (kinase family bonus, AlphaFold structure)
- Safety: ~12/20 (limited data, unknown KO phenotype)
- Clinical Precedent: 0/15 (no clinical development)
- Validation Evidence: ~2/10 (minimal functional data)
- **Total: ~37/100 = Tier 4**
