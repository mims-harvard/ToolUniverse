# Report Template & Evidence Grading

Report template, evidence grading system, and report section formatting examples.

## Report File Template

**File**: `[TARGET]_binder_discovery_report.md`

```markdown
# Small Molecule Binder Discovery: [TARGET]

**Generated**: [Date] | **Query**: [Original query] | **Status**: In Progress

---

## Executive Summary
[Researching...]

---

## 1. Target Validation
### 1.1 Target Identifiers
[Researching...]
### 1.2 Druggability Assessment
[Researching...]
### 1.3 Binding Site Analysis
[Researching...]

---

## 2. Known Ligand Landscape
### 2.1 ChEMBL Bioactivity Summary
[Researching...]
### 2.2 Approved Drugs & Clinical Compounds
[Researching...]
### 2.3 Chemical Probes
[Researching...]
### 2.4 SAR Insights
[Researching...]

---

## 3. Structural Information
### 3.1 Available Structures
[Researching...]
### 3.2 Binding Pocket Analysis
[Researching...]
### 3.3 Key Interactions
[Researching...]

---

## 4. Compound Expansion
### 4.1 Similarity Search Results
[Researching...]
### 4.2 Substructure Search Results
[Researching...]
### 4.3 Cross-Database Mining
[Researching...]

---

## 5. ADMET Filtering
### 5.1 Physicochemical Filters
[Researching...]
### 5.2 ADMET Predictions
[Researching...]
### 5.3 Structural Alerts
[Researching...]
### 5.4 Filter Summary
[Researching...]

---

## 6. Candidate Prioritization
### 6.1 Scoring Methodology
[Researching...]
### 6.2 Synthesis Feasibility
[Researching...]
### 6.3 Top 20 Candidates
[Researching...]

---

## 7. Recommendations
### 7.1 Immediate Actions
[Researching...]
### 7.2 Experimental Validation Plan
[Researching...]
### 7.3 Backup Strategies
[Researching...]

---

## 8. Data Gaps & Limitations
[Researching...]

---

## 9. Data Sources
[Will be populated as research progresses...]

---

## 10. Methods Summary

| Step | Tool | Purpose |
|------|------|---------|
| Sequence retrieval | UniProt_search | Get protein sequence |
| Structure prediction | NvidiaNIM_alphafold2 / NvidiaNIM_esmfold | 3D structure with pLDDT |
| Docking validation | NvidiaNIM_diffdock / NvidiaNIM_boltz2 | Validate binding pocket |
| Known ligands | ChEMBL_get_target_activities | Bioactivity data |
| Similarity search | ChEMBL_search_similar_molecules | Expand chemical space |
| De novo generation | NvidiaNIM_genmol / NvidiaNIM_molmim | Novel molecule design |
| ADMET filtering | ADMETAI_predict_* | Drug-likeness assessment |
| Candidate docking | NvidiaNIM_diffdock / NvidiaNIM_boltz2 | Final scoring |
```

---

## Evidence Grading System

| Tier | Symbol | Description | Example |
|------|--------|-------------|---------|
| **T0** | (4 stars) | Docking score > reference inhibitor | Better than erlotinib |
| **T1** | (3 stars) | Experimental IC50/Ki < 100 nM | ChEMBL bioactivity |
| **T2** | (2 stars) | Docking within 5% of reference OR IC50 100-1000 nM | High priority |
| **T3** | (1 star) | Structural similarity > 80% to T1 | Predicted active |
| **T4** | (0 stars) | Similarity 70-80%, scaffold match | Lower confidence |
| **T5** | (empty) | Generated molecule, ADMET-passed, no docking | Speculative |

### Docking-Enhanced Grading

When NVIDIA NIM docking is available:
- Docking > reference -> upgrade to T0
- Docking within 5% -> upgrade to T2
- Docking within 20% -> maintain current tier
- Docking >20% worse -> downgrade one tier

---

## Report Section Formatting Examples

### Druggability Assessment Example

```markdown
### 1.2 Druggability Assessment

| Factor | Assessment | Score | Source |
|--------|------------|-------|--------|
| Target class | Receptor tyrosine kinase | High | ChEMBL |
| Tractability bucket | 1 (approved drugs) | High | Open Targets |
| Known drugs | 15 approved | High | DGIdb |
| Binding site | ATP pocket (well-characterized) | High | PDB |

**Overall Druggability**: Highly druggable

*Sources: Open Targets, DGIdb, ChEMBL*
```

### Known Actives Example

```markdown
### 2.1 Known Active Compounds (ChEMBL)

**Total Bioactivity Points**: 2,847 (IC50: 1,234 | Ki: 892 | Kd: 456 | EC50: 265)
**Compounds with IC50 < 100 nM**: 156

| Compound | ChEMBL ID | IC50 (nM) | Max Phase | SMILES (truncated) |
|----------|-----------|-----------|-----------|-------------------|
| Erlotinib | CHEMBL553 | 2 | 4 | COc1cc2ncnc(Nc3ccc... |

*Source: ChEMBL via `ChEMBL_get_target_activities` (CHEMBL203)*
```

### Binding Site Example

```markdown
### 3.2 Binding Pocket Characterization

**Pocket Volume**: ~850 A3 (well-defined)
**Key Interaction Residues**:
- **Hinge region**: M793 (backbone H-bond donor/acceptor)
- **Gatekeeper**: T790 (small residue, allows access)
- **DFG motif**: D855 (active conformation)

**Druggability Assessment**: High (enclosed pocket, conserved interactions)
```

### ADMET Filter Summary Example

```markdown
### 5.4 Filter Summary

| Filter Stage | Input | Passed | Failed | Pass Rate |
|--------------|-------|--------|--------|-----------|
| Physicochemical (Lipinski) | 568 | 456 | 112 | 80% |
| Drug-likeness (QED > 0.3) | 456 | 398 | 58 | 87% |
| Bioavailability (> 0.3) | 398 | 312 | 86 | 78% |
| Toxicity filters | 312 | 267 | 45 | 86% |
| Structural alerts | 267 | 234 | 33 | 88% |
| **Final Candidates** | **568** | **234** | **334** | **41%** |
```

### Top Candidates Example

```markdown
### 6.3 Top 20 Candidate Compounds

| Rank | ID | SMILES | Sim. Score | ADMET | Novelty | Overall | Rationale |
|------|-----|--------|------------|-------|---------|---------|-----------|
| 1 | CPD-001 | Cc1ccc... | 0.82 | 4.5 | Novel scaffold | 4.2 | High similarity, clean ADMET |

**Scaffold Diversity**: 7 distinct scaffolds in top 20
**Commercial Availability**: 12/20 available for purchase
**Estimated Hit Rate**: 15-25% (based on similarity to actives)
```

### Therapeutic Antibody Landscape Example

```markdown
### 1.2.5 Therapeutic Antibody Landscape

| Antibody (INN) | Target | Format | Phase | PDB |
|----------------|--------|--------|-------|-----|
| Pembrolizumab | PD-1 | IgG4 | Approved | 5DK3 |

**Competitive Landscape**: 3 approved antibodies target this protein
**Strategic Implication**: Small molecule approach offers differentiation (oral dosing, CNS penetration, cost)

*Source: Thera-SAbDab via `TheraSAbDab_search_by_target`*
```

### Structure Prediction Example

```markdown
### 1.4 Structure Prediction Quality

**Method**: AlphaFold2 via NVIDIA NIM
**Mean pLDDT**: 90.94 (very high confidence)

| Confidence Level | Range | Fraction | Interpretation |
|------------------|-------|----------|----------------|
| Very High | >=90 | 74.3% | Highly reliable |
| Confident | 70-90 | 16.0% | Reliable |
| Low | 50-70 | 9.0% | Use caution |
| Very Low | <50 | 0.7% | Unreliable |

*Source: NVIDIA NIM via `NvidiaNIM_alphafold2`*
```

---

## Citation Format

Every section MUST include source attribution:

```markdown
*Source: ChEMBL via `ChEMBL_get_target_activities` (CHEMBL203)*
*Source: PDB via `get_protein_metadata_by_pdb_id` (1M17)*
*Source: ADMET-AI via `ADMETAI_predict_toxicity`*
*Source: NVIDIA NIM via `NvidiaNIM_alphafold2` (pLDDT: 90.94)*
*Source: NVIDIA NIM via `NvidiaNIM_diffdock` (confidence: 0.906)*
*Source: NVIDIA NIM via `NvidiaNIM_genmol` (100 molecules)*
```

---

## Data Output Files

In addition to the report:
- `[TARGET]_candidate_compounds.csv` - Prioritized compounds with: Rank, ID, SMILES, Similarity, ADMET_Score, Overall_Score, Source
- `[TARGET]_bibliography.json` - Literature references (optional)
