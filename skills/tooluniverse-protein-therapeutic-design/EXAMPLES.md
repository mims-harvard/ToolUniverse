# Therapeutic Protein Designer - Examples

## Example 1: De Novo Binder Design

### User Query
"Design a small protein binder against PD-L1 for cancer immunotherapy"

### Expected Output

```markdown
# Therapeutic Protein Design Report: PD-L1 Binder

**Generated**: 2026-02-04 | **Target**: PD-L1 (Q9NZQ7)

---

## Executive Summary

Successfully designed 4 high-quality protein binders targeting the PD-1 binding interface of PD-L1. **Top candidate (Design_001)** is a compact 85-residue 3-helix bundle with:
- pLDDT: 88.5 (high confidence)
- pTM: 0.85 (excellent topology)
- Low aggregation propensity
- Favorable expression characteristics

**Recommended for experimental testing**: Design_001, Design_003, Design_005 (all Tier 1)

---

## 1. Target Characterization

### 1.1 Target Information

| Property | Value |
|----------|-------|
| **Target** | PD-L1 (Programmed death-ligand 1) |
| **UniProt** | Q9NZQ7 |
| **Structure** | PDB: 4ZQK (2.0 Å, X-ray) |
| **Binding site** | IgV domain, PD-1 interface |
| **Known therapeutics** | Atezolizumab, Durvalumab, Avelumab |

### 1.2 Target Structure Quality

| Metric | Value |
|--------|-------|
| Resolution | 2.0 Å |
| R-free | 0.228 |
| Completeness | 98.7% |
| Binding site pLDDT | N/A (experimental) |

### 1.3 Binding Epitope

**Selected interface**: PD-1 binding face (residues 54-68, 115-125)

| Hotspot Residue | Role | Conservation |
|-----------------|------|--------------|
| Y56 | Hydrophobic contact | 100% |
| D61 | Salt bridge | 98% |
| N63 | H-bond | 95% |
| V68 | Hydrophobic | 100% |
| R113 | Salt bridge | 92% |

*Source: PDB 4ZQK, ConSurf analysis*

---

## 2. Backbone Generation

### 2.1 Design Parameters

| Parameter | Value |
|-----------|-------|
| **Method** | RFdiffusion via NVIDIA NIM |
| **Design mode** | Unconditional (scaffolds for grafting) |
| **Diffusion steps** | 50 |
| **Target size** | 70-100 residues |
| **Number generated** | 10 backbones |

### 2.2 Generated Backbones

| Backbone | Length | Topology | SS Content | Quality |
|----------|--------|----------|------------|---------|
| BB_001 | 85 aa | 3-helix bundle | 72% α | ★★★ |
| BB_002 | 92 aa | β-sandwich | 45% β | ★★☆ |
| BB_003 | 78 aa | α/β mixed | 40% α, 25% β | ★★★ |
| BB_004 | 88 aa | 4-helix bundle | 78% α | ★★☆ |
| BB_005 | 95 aa | β-barrel | 55% β | ★★☆ |
| BB_006 | 82 aa | α/β roll | 35% α, 30% β | ★☆☆ |

### 2.3 Selected Backbones

**Selected for sequence design**: BB_001, BB_003, BB_004, BB_005

**Rationale**:
- BB_001: Compact, stable fold, ideal for binders
- BB_003: Versatile topology for interface optimization
- BB_004: Larger interface area possible
- BB_005: Different topology for diversity

*Source: NVIDIA NIM via `NvidiaNIM_rfdiffusion`*

---

## 3. Sequence Design

### 3.1 Design Parameters

| Parameter | Value |
|-----------|-------|
| **Method** | ProteinMPNN via NVIDIA NIM |
| **Temperature** | 0.1 (conservative) |
| **Sequences per backbone** | 8 |
| **Total sequences** | 32 |

### 3.2 All Designed Sequences (Ranked by MPNN Score)

| Rank | Backbone | ID | Length | MPNN Score |
|------|----------|-------|--------|------------|
| 1 | BB_001 | Design_001 | 85 | -1.89 |
| 2 | BB_003 | Design_003 | 78 | -1.92 |
| 3 | BB_001 | Design_002 | 85 | -2.01 |
| 4 | BB_004 | Design_008 | 88 | -2.05 |
| 5 | BB_005 | Design_005 | 95 | -2.08 |
| 6 | BB_003 | Design_004 | 78 | -2.12 |
| 7 | BB_004 | Design_009 | 88 | -2.15 |
| 8 | BB_001 | Design_006 | 85 | -2.18 |
| 9 | BB_005 | Design_007 | 95 | -2.21 |
| 10 | BB_003 | Design_010 | 78 | -2.25 |

### 3.3 Top Sequences

**Design_001** (Rank 1):
```
>Design_001 | BB_001 | MPNN=-1.89
MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH
GSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKL
```

**Design_003** (Rank 2):
```
>Design_003 | BB_003 | MPNN=-1.92
MKKYTCTVCGYIYNPEDGDPDDNGGGGGGGKVWKGGGGGGDPTSDELIK
ALQEASGTEVELKTKGDKFKKVS
```

*Source: NVIDIA NIM via `NvidiaNIM_proteinmpnn`*

---

## 4. Structure Validation

### 4.1 ESMFold Validation Results

| Design | pLDDT | pTM | RMSD | Status |
|--------|-------|-----|------|--------|
| Design_001 | 88.5 | 0.85 | 1.2 Å | ✓ PASS |
| Design_003 | 84.2 | 0.81 | 1.4 Å | ✓ PASS |
| Design_002 | 82.1 | 0.78 | 1.6 Å | ✓ PASS |
| Design_008 | 79.5 | 0.75 | 1.9 Å | ✓ PASS |
| Design_005 | 86.3 | 0.83 | 1.3 Å | ✓ PASS |
| Design_004 | 75.8 | 0.72 | 2.1 Å | ✓ PASS |
| Design_009 | 68.2 | 0.64 | 2.8 Å | ✗ FAIL |
| Design_006 | 71.4 | 0.69 | 2.4 Å | ✓ PASS |

### 4.2 Top Design: Design_001 Regional Breakdown

| Region | Residues | pLDDT | Role |
|--------|----------|-------|------|
| Helix 1 | 1-28 | 92.3 | Core |
| Loop 1 | 29-35 | 78.4 | Connector |
| Helix 2 | 36-58 | 91.8 | Core |
| Loop 2 | 59-65 | 75.2 | Potential interface |
| Helix 3 | 66-85 | 90.1 | Core |

**Assessment**: Excellent fold quality with confident core and flexible loops suitable for interface formation.

*Source: NVIDIA NIM via `NvidiaNIM_esmfold`*

---

## 5. Developability Assessment

### 5.1 Developability Scores

| Design | Aggregation | pI | MW (kDa) | Cys | Expression | Overall |
|--------|-------------|-----|----------|-----|------------|---------|
| Design_001 | 0.32 | 6.2 | 9.5 | 0 | High | ★★★ |
| Design_003 | 0.38 | 5.8 | 8.7 | 0 | High | ★★★ |
| Design_005 | 0.41 | 6.8 | 10.6 | 0 | High | ★★★ |
| Design_002 | 0.45 | 7.1 | 9.5 | 0 | Medium | ★★☆ |
| Design_008 | 0.52 | 5.4 | 9.8 | 2 | Medium | ★★☆ |

### 5.2 Expression Predictions

| Design | E. coli | Mammalian | Recommended |
|--------|---------|-----------|-------------|
| Design_001 | High (soluble) | High | E. coli |
| Design_003 | High (soluble) | High | E. coli |
| Design_005 | Medium | High | E. coli |

*Source: Sequence analysis, aggregation prediction*

---

## 6. Final Candidates

### 6.1 Ranked Candidate List

| Rank | Design | pLDDT | pTM | MPNN | Aggreg. | Tier | Recommendation |
|------|--------|-------|-----|------|---------|------|----------------|
| 1 | **Design_001** | 88.5 | 0.85 | -1.89 | 0.32 | ★★★ | TOP CHOICE |
| 2 | **Design_005** | 86.3 | 0.83 | -2.08 | 0.41 | ★★★ | High priority |
| 3 | **Design_003** | 84.2 | 0.81 | -1.92 | 0.38 | ★★★ | High priority |
| 4 | Design_002 | 82.1 | 0.78 | -2.01 | 0.45 | ★★☆ | Backup |
| 5 | Design_008 | 79.5 | 0.75 | -2.05 | 0.52 | ★★☆ | Backup |

### 6.2 Sequences for Testing

```fasta
>Design_001 | pLDDT=88.5 | pTM=0.85 | MPNN=-1.89 | Tier=T1
MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH
GSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKL

>Design_005 | pLDDT=86.3 | pTM=0.83 | MPNN=-2.08 | Tier=T1
MTTLAELKKLAELLPKLEELKKELLEALKKAELKKEVAELLKKLAKELLKE
LAKELLKKLAKELLKKELKEALKKALKELLKEALKKAVEEL

>Design_003 | pLDDT=84.2 | pTM=0.81 | MPNN=-1.92 | Tier=T1
MKKYTCTVCGYIYNPEDGDPDDNGGGGGGGKVWKGGGGGGDPTSDELIK
ALQEASGTEVELKTKGDKFKKVS
```

---

## 7. Experimental Recommendations

### 7.1 Expression and Purification

| Step | Protocol | Notes |
|------|----------|-------|
| **Expression** | E. coli BL21(DE3) | All designs cysteine-free |
| **Induction** | 0.5 mM IPTG, 18°C, 16h | Optimize for each |
| **Lysis** | Sonication in PBS | Add protease inhibitors |
| **Purification** | Ni-NTA (if His-tagged) | Or ion exchange |
| **Polishing** | Size exclusion | Superdex 75 |

### 7.2 Characterization Assays

| Assay | Purpose | Priority |
|-------|---------|----------|
| SEC-MALS | Oligomeric state | High |
| CD spectroscopy | Secondary structure | High |
| DSF/Thermal shift | Stability | High |
| BLI/SPR | PD-L1 binding | High |
| Crystallography | Structure validation | Medium |

### 7.3 Expected Challenges

1. **Loop flexibility** - May need optimization for binding
2. **Affinity maturation** - Initial designs may need improvement
3. **Specificity** - Test against related proteins (PD-L2)

---

## 8. Data Sources

| Tool | Purpose | Query |
|------|---------|-------|
| PDB | Target structure | 4ZQK |
| UniProt | Target sequence | Q9NZQ7 |
| NvidiaNIM_rfdiffusion | Backbone generation | 50 steps |
| NvidiaNIM_proteinmpnn | Sequence design | T=0.1 |
| NvidiaNIM_esmfold | Validation | All designs |
```

---

## Example 2: Enzyme Scaffold Design

### User Query
"Design a stable protein scaffold that could host a catalytic triad"

### Expected Output (Key Sections)

```markdown
## Executive Summary

Designed 5 stable α/β hydrolase-like scaffolds capable of hosting a Ser-His-Asp catalytic triad. **Top candidate (Scaffold_003)** features:
- Optimal geometry for triad placement
- High stability (pLDDT: 91.2)
- TIM-barrel-like fold for substrate access

---

## 2. Backbone Generation

### Design Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Topology | α/β hydrolase | Hosts catalytic triad |
| Size | 200-250 aa | Sufficient for active site |
| Cavity | Central | Substrate access |

### Generated Scaffolds

| Scaffold | Length | Topology | Cavity Volume | Quality |
|----------|--------|----------|---------------|---------|
| Scaffold_001 | 215 aa | 8-strand TIM barrel | 580 Å³ | ★★★ |
| Scaffold_003 | 228 aa | α/β hydrolase | 620 Å³ | ★★★ |
| Scaffold_005 | 240 aa | Rossmann-like | 450 Å³ | ★★☆ |

---

## 4. Active Site Design

### Catalytic Triad Placement

| Scaffold | Ser | His | Asp | Geometry |
|----------|-----|-----|-----|----------|
| Scaffold_003 | 152 | 237 | 209 | Optimal (3.1Å, 2.8Å) |
| Scaffold_001 | 145 | 220 | 192 | Good (3.3Å, 2.9Å) |

### Triad Quality Metrics

| Metric | Ideal | Scaffold_003 |
|--------|-------|--------------|
| Ser-His distance | 3.0 Å | 3.1 Å |
| His-Asp distance | 2.8 Å | 2.8 Å |
| Ser Oγ accessibility | Exposed | Exposed |
```

---

## Example 3: Miniprotein Design

### User Query
"Design a minimal stable fold under 50 amino acids"

### Expected Output (Key Sections)

```markdown
## Executive Summary

Designed ultra-stable miniproteins (35-50 aa) using constrained RFdiffusion. **Top design (Mini_002)** is a 42-residue designed fold with:
- pLDDT: 94.1 (exceptional)
- Three disulfide bonds for stability
- Predicted Tm > 90°C

---

## 2. Design Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Length | 35-50 aa | Miniprotein range |
| Disulfides | 2-3 | Stability enhancement |
| Topology | Constrained | Ensure compact fold |

---

## 4. Validation Results

| Design | Length | Disulfides | pLDDT | pTM | Predicted Tm |
|--------|--------|------------|-------|-----|--------------|
| Mini_002 | 42 | 3 (C8-C38, C15-C29, C22-C45) | 94.1 | 0.92 | >90°C |
| Mini_005 | 38 | 2 (C5-C35, C12-C28) | 91.8 | 0.89 | ~85°C |
| Mini_001 | 45 | 3 | 89.2 | 0.86 | ~80°C |

---

## 6. Final Candidate

```fasta
>Mini_002 | 42aa | 3SS | pLDDT=94.1 | Tier=T1
RCPEFVGCCNPACGPKYCRSCVRSGCVGCCPEFVGPCNPACKCR
```

**Notes**: 
- Express in oxidizing environment (periplasm or in vitro)
- Verify disulfide pairing by mass spec
- Test thermal stability by CD
```
