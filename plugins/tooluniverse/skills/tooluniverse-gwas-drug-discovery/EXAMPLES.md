# GWAS-to-Drug Discovery Examples

## Use Case 1: Novel Target Discovery for Rare Disease

**Scenario**: Identify druggable targets for Huntington's disease

**Steps**:
1. Get GWAS hits for Huntington's -> HTT, PDE10A, MSH3
2. Assess druggability -> PDE10A (phosphodiesterase) = high
3. Find existing PDE10A inhibitors -> Multiple tool compounds
4. Recommendation: Develop selective PDE10A inhibitor

**Clinical Context**:
- HTT (huntingtin) = difficult to drug (large, scaffold protein)
- PDE10A = modifier gene, GPCR-coupled, small molecule tractable
- Precedent: PDE5 inhibitors (sildenafil) already approved

## Use Case 2: Drug Repurposing for Common Disease

**Scenario**: Find repurposing opportunities for Alzheimer's disease

**Steps**:
1. Get GWAS targets -> APOE, CLU, CR1, PICALM, BIN1, TREM2
2. Find drugs targeting these -> Anti-inflammatory drugs (CR1, TREM2)
3. Match approved drugs -> Anakinra (IL-1R antagonist)
4. Rationale: TREM2 links inflammation to neurodegeneration

**Example Output**:
```
Repurposing Candidate: Anakinra
- Target: IL-1R -> affects TREM2 pathway
- Current use: Rheumatoid arthritis (approved)
- AD rationale: 3 GWAS genes in immune pathway
- Clinical phase: Phase II trial in progress
- Safety: Known profile, subcutaneous injection
```

## Use Case 3: Target Validation for Existing Drug Class

**Scenario**: Validate new diabetes targets related to GLP-1 pathway

**Steps**:
1. Get T2D GWAS genes -> TCF7L2, PPARG, KCNJ11, GLP1R
2. GLP1R validated -> Existing drug class (semaglutide, liraglutide)
3. Check related genes -> GIP, GIPR (glucose-dependent insulinotropic polypeptide)
4. Outcome: Dual GLP-1/GIP agonists (tirzepatide, approved 2022)

## Success Stories

- **PCSK9** (cholesterol) -> Alirocumab, Evolocumab (approved 2015)
- **IL-6R** (rheumatoid arthritis) -> Tocilizumab (approved 2010)
- **CTLA4** (autoimmunity) -> Abatacept (approved 2005)
- **CFTR** (cystic fibrosis) -> Ivacaftor (approved 2012)

**Genetic Evidence Doubles Success Rate**: Targets with genetic support have 2x higher probability of clinical approval (Nelson et al., Nature Genetics 2015).
