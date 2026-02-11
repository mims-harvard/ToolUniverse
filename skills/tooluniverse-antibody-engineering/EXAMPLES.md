# Antibody Engineering & Optimization - Examples

## Example 1: Mouse Antibody Humanization

### User Query
"Humanize this mouse anti-PD-L1 antibody while maintaining affinity"

**Input Sequences**:
```
>Mouse_VH
EVQLVESGGGLVQPGGSLRLSCAASGYTFTSYYMHWVRQAPGKGLEWVSGIIPIFGTANYAQKFQGRVTISADTSKNTAYLQMNSLRAEDTAVYYCARDDGSYSPFDYWGQGTLVTVSS

>Mouse_VL
DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPLTFGQGTKVEIK
```

### Expected Output

```markdown
# Antibody Humanization Report: Anti-PD-L1 mAb

**Generated**: 2026-02-09 | **Target**: PD-L1 (Q9NZQ7) | **Original**: Mouse antibody

---

## Executive Summary

Successfully humanized mouse anti-PD-L1 antibody with significant improvements:
- **Humanization**: 62% → 87% (VH), 68% → 90% (VL)
- **Predicted affinity retention**: 85-95% of original
- **Developability score**: 62 → 79 (Tier 1)
- **Immunogenicity risk**: High → Low

**Recommended Candidate**: VH_Humanized_v2 + VL_Humanized_v1

This variant balances high humanization (87%) with structural preservation through strategic backmutations. Ready for expression and in vitro validation.

---

## 1. Input Characterization

### 1.1 Sequence Analysis

| Chain | Length | Species | Humanness | Closest Human Germline | Identity |
|-------|--------|---------|-----------|------------------------|----------|
| **VH** | 118 aa | Mouse | 62% | IGHV1-69*01 | 87.2% |
| **VL** | 107 aa | Mouse | 68% | IGKV1-39*01 | 89.5% |

### 1.2 CDR Annotation (IMGT Numbering)

**Heavy Chain CDRs**:
| CDR | Sequence | Length | Canonical Class | Conservation |
|-----|----------|--------|-----------------|--------------|
| CDR-H1 | GYTFTSYYMH | 10 | H1-13-1 | Common |
| CDR-H2 | GIIPIFGTANY | 11 | H2-10-1 | Common |
| CDR-H3 | ARDDGSYSPFDYWG | 14 | Non-canonical | **Unique** |

**Light Chain CDRs**:
| CDR | Sequence | Length | Canonical Class | Conservation |
|-----|----------|--------|-----------------|--------------|
| CDR-L1 | RASQSISSYLN | 11 | L1-11-1 | Common |
| CDR-L2 | AASSLQS | 7 | L2-8-1 | Common |
| CDR-L3 | QQSYSTPLT | 9 | L3-9-cis7-1 | Common |

**Key Finding**: CDR-H3 is unique (14 aa, unusual DDGSY motif) - this is the primary binding determinant and must be preserved exactly.

### 1.3 Clinical Precedents

**Approved Anti-PD-L1 Antibodies**:
1. **Atezolizumab** (Tecentriq) - Fully human, IgG1
2. **Durvalumab** (Imfinzi) - Fully human, IgG1
3. **Avelumab** (Bavencio) - Fully human, IgG1

**Insight**: All approved anti-PD-L1 antibodies are fully human (not humanized), suggesting high bar for immunogenicity. Our humanization target: >85% framework identity.

*Source: IMGT, TheraSAbDab, sequence analysis*

---

## 2. Humanization Strategy

### 2.1 Framework Selection

**VH Framework Candidates**:

| Germline | Identity | CDR Compatibility | Clinical Use | Overall Score |
|----------|----------|-------------------|--------------|---------------|
| **IGHV1-69*01** | 87.2% | Excellent | 127 antibodies | **96/100** ★ |
| IGHV3-23*01 | 84.8% | Good | 89 antibodies | 91/100 |
| IGHV1-18*01 | 86.1% | Excellent | 54 antibodies | 90/100 |

**VL Framework Candidates**:

| Germline | Identity | CDR Compatibility | Clinical Use | Overall Score |
|----------|----------|-------------------|--------------|---------------|
| **IGKV1-39*01** | 89.5% | Excellent | 89 antibodies | **94/100** ★ |
| IGKV1-33*01 | 87.2% | Excellent | 76 antibodies | 92/100 |
| IGKV3-20*01 | 85.8% | Good | 45 antibodies | 88/100 |

**Selected**:
- VH: IGHV1-69*01 (most used in therapeutic antibodies)
- VL: IGKV1-39*01 (high identity, proven track record)

### 2.2 CDR Grafting & Backmutations

**Vernier Zone Analysis** (residues affecting CDR conformation):

| Position | Human | Mouse | Distance to CDR | Impact | Backmutation? |
|----------|-------|-------|-----------------|--------|---------------|
| VH-27 | T | A | CDR-H1 border | High | **YES** |
| VH-48 | I | V | VH-VL interface | High | **YES** |
| VH-67 | A | S | CDR-H2 support | Medium | Test both |
| VH-71 | R | K | CDR-H2 support | Low | No |
| VH-93 | A | T | CDR-H3 base | Medium | Test both |

**Backmutation Strategy**:
- **Version 1 (v1)**: Full humanization, no backmutations → 87% human
- **Version 2 (v2)**: Critical backmutations at 27, 48 → 85% human, better CDR support
- **Version 3 (v3)**: All backmutations (27, 48, 67, 93) → 82% human

### 2.3 Humanized Sequences

**VH_Humanized_v1** (Full humanization):
```
>VH_Humanized_v1 | IGHV1-69*01 framework | 87% human
EVQLVQSGAEVKKPGASVKVSCKASGYTFTSYYMHWVRQAPGQGLEWMGGIIPIFGTANY
AQKFQGRVTMTTDTSTSTAYMELRSLRSDDTAVYYCARARDDGSYSPFDYWGQGTLVTVSS
```

**VH_Humanized_v2** (With key backmutations):
```
>VH_Humanized_v2 | IGHV1-69*01 + backmutations | 85% human
EVQLVQSGAEVKKPGASVKVSCKASGYAFTSYYMHWVRQAPGQGLEWMVGIIPIFGTANY
AQKFQGRVTMTTDTSTSTAYMELRSLRSDDTAVYYCARARDDGSYSPFDYWGQGTLVTVSS
```
Changes: T27A, I48V (Vernier zone preservation)

**VL_Humanized_v1** (Full humanization):
```
>VL_Humanized_v1 | IGKV1-39*01 framework | 90% human
DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPS
RFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPLTFGQGTKVEIK
```

### 2.4 Humanization Metrics

| Variant | Framework Humanness | CDR Preservation | T-cell Epitopes | Aggregation | Overall |
|---------|---------------------|------------------|-----------------|-------------|---------|
| Original (Mouse) | 62% (VH), 68% (VL) | 100% | 12 | High | 62/100 |
| VH_v1 + VL_v1 | 87%, 90% | 100% | 5 | Medium | 74/100 |
| **VH_v2 + VL_v1** | **85%, 90%** | **100%** | **4** | **Low** | **79/100** ★ |
| VH_v3 + VL_v1 | 82%, 90% | 100% | 3 | Low | 77/100 |

**Recommendation**: VH_v2 + VL_v1 offers best balance.

*Source: IMGT germline database*

---

## 3. Structure Modeling & Validation

### 3.1 AlphaFold Predictions

**Structure Quality Comparison**:

| Variant | Mean pLDDT | VH pLDDT | VL pLDDT | CDR pLDDT | Pass? |
|---------|------------|----------|----------|-----------|-------|
| Original (Mouse) | 89.2 | 91.4 | 88.7 | 85.3 | ✓ |
| VH_v1 + VL_v1 | 87.1 | 88.9 | 88.2 | 82.8 | ✓ |
| **VH_v2 + VL_v1** | **88.7** | **90.5** | **88.3** | **84.6** | **✓** |
| VH_v3 + VL_v1 | 88.9 | 90.8 | 88.4 | 85.1 | ✓ |

**Interpretation**: VH_v2 maintains near-original structure quality (88.7 vs 89.2 pLDDT). Backmutations at positions 27 and 48 successfully preserve CDR geometry.

### 3.2 CDR Conformation Validation

**RMSD to Original Structure**:

| CDR | Original | v1 (Full) | v2 (Backmut) | v3 (All) | Status |
|-----|----------|-----------|--------------|----------|--------|
| CDR-H1 | - | 1.8 Å | 0.9 Å | 0.7 Å | v2: Good |
| CDR-H2 | - | 1.5 Å | 1.1 Å | 0.8 Å | v2: Good |
| CDR-H3 | - | 0.8 Å | 0.7 Å | 0.6 Å | All: Excellent |
| CDR-L1 | - | 0.9 Å | 0.9 Å | 0.9 Å | All: Excellent |
| CDR-L2 | - | 0.8 Å | 0.8 Å | 0.8 Å | All: Excellent |
| CDR-L3 | - | 1.0 Å | 1.0 Å | 1.0 Å | All: Excellent |

**Key Finding**: VH_v2 reduces CDR-H1 and CDR-H2 RMSD compared to full humanization (v1), validating backmutation strategy.

*Source: AlphaFold predictions*

---

## 4. Developability Assessment

### 4.1 Comprehensive Scores

| Property | Original | VH_v1+VL_v1 | **VH_v2+VL_v1** | VH_v3+VL_v1 |
|----------|----------|-------------|-----------------|-------------|
| **Aggregation risk** | 0.58 (Med) | 0.38 (Low) | **0.32 (Low)** | 0.35 (Low) |
| **PTM liability** | 5 sites | 3 sites | **2 sites** | 2 sites |
| **Thermal stability (Tm)** | 68°C | 71°C | **73°C** | 72°C |
| **pI** | 8.2 (VH) | 7.5 (VH) | **7.2 (VH)** | 7.4 (VH) |
| **Expression (predicted)** | 1.2 g/L | 1.7 g/L | **2.0 g/L** | 1.8 g/L |
| **Developability Score** | 62/100 | 74/100 | **79/100** | 77/100 |

### 4.2 PTM Site Mitigation

**Remaining PTM Sites in VH_v2**:
| Position | Motif | PTM Type | Risk | Mitigation |
|----------|-------|----------|------|------------|
| VH-54 | NG | Deamidation | Medium | Mutate to NQ (optional) |
| VL-28 | NS | Deamidation | Low | Monitor only |

**Recommendation**: Both sites are low-medium risk and in framework regions. Mitigation optional depending on stability data.

### 4.3 Immunogenicity Prediction

**T-Cell Epitope Analysis** (IEDB):

| Variant | Predicted Epitopes | High-Risk Epitopes | Risk Score | Category |
|---------|-------------------|-------------------|------------|----------|
| Original | 12 | 5 | 85 | High |
| VH_v1+VL_v1 | 5 | 2 | 45 | Medium |
| **VH_v2+VL_v1** | **4** | **1** | **38** | **Low-Medium** |
| VH_v3+VL_v1 | 3 | 1 | 32 | Low |

**VH_v2 Remaining Epitope**:
- Position VH 78-86: TDTSTSTA (framework residue cluster)
- Can be further deimmunized if needed: T84S mutation (human consensus)

*Source: Developability analysis, IEDB predictions*

---

## 5. Final Recommendations

### 5.1 Recommended Candidate

**VH_Humanized_v2 + VL_Humanized_v1**

**Rationale**:
- Optimal balance: 85-90% human framework with maintained binding
- Best developability score (79/100, Tier 1)
- Low immunogenicity risk (38, borderline low)
- Excellent predicted expression (2.0 g/L)
- Lowest aggregation risk (0.32)

**Final Sequences**:
```fasta
>VH_v2_AntiPDL1 | 85% human framework
EVQLVQSGAEVKKPGASVKVSCKASGYAFTSYYMHWVRQAPGQGLEWMVGIIPIFGTANY
AQKFQGRVTMTTDTSTSTAYMELRSLRSDDTAVYYCARARDDGSYSPFDYWGQGTLVTVSS

>VL_v1_AntiPDL1 | 90% human framework
DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPS
RFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPLTFGQGTKVEIK
```

### 5.2 Validation Plan

**Phase 1: Expression & Purification** (Weeks 1-3)
- Express in CHO cells (transient)
- Purify via Protein A
- Characterize: SEC, SDS-PAGE, mass spec

**Phase 2: Biophysical Characterization** (Weeks 3-5)
- Binding affinity: SPR (target KD <10 nM, ideally similar to mouse)
- Thermal stability: DSF (target Tm >70°C)
- Aggregation: SEC, DLS (target >95% monomer)

**Phase 3: Functional Validation** (Weeks 5-8)
- Cell-based binding assay (flow cytometry)
- Blocking assay (inhibit PD-1/PD-L1 interaction)
- T-cell activation assay (functional potency)

**Success Criteria**:
- Affinity: ≥70% of mouse parent (KD <10 nM)
- Stability: Tm >70°C, >95% monomer
- Function: EC50 within 2-3x of mouse parent

### 5.3 Backup Variants

| Variant | Profile | Use Case |
|---------|---------|----------|
| VH_v3 + VL_v1 | Lowest immunogenicity (32) | If ADA observed in v2 |
| VH_v1 + VL_v1 | Highest humanness (87%/90%) | If affinity maintained |
| Deimmunized v2 | T84S mutation added | If epitope score needs reduction |

### 5.4 Next Steps

1. **Gene synthesis** (Week 1): Order v2, v1, v3
2. **Transient expression** (Week 2-3): Test all three variants
3. **Characterization** (Week 3-6): Select best performer
4. **Stable cell line** (Month 2-4): Develop for lead candidate
5. **Scale-up** (Month 5-6): Produce material for in vivo studies

---

## Data Sources

| Tool | Query | Results |
|------|-------|---------|
| IMGT_search_genes | IGHV, IGKV (Homo sapiens) | Germline candidates |
| IMGT_get_sequence | IGHV1-69*01, IGKV1-39*01 | Framework sequences |
| TheraSAbDab_search_by_target | PD-L1 | 3 approved antibodies |
| AlphaFold_get_prediction | VH:VL complexes | Structure models |
| iedb_search_epitopes | Sequence scanning | T-cell epitopes |
```

---

## Example 2: Affinity Maturation (Single-Digit nM Target)

### User Query
"Improve affinity of this humanized anti-HER2 antibody from 15 nM to <5 nM"

**Input**: Humanized antibody with moderate affinity (KD = 15 nM)

### Expected Output (Key Sections)

```markdown
# Affinity Maturation Report: Anti-HER2 Antibody

**Original KD**: 15 nM | **Target KD**: <5 nM (>3x improvement) | **Target**: HER2 (P04626)

---

## Executive Summary

Successfully designed affinity-optimized variants with predicted 5-10x improvement:
- **Top variant**: CDR-H2_Y52W + CDR-H3_S100aY → Predicted KD 1.8 nM (8.3x)
- **Strategy**: Increased hydrophobic contacts and pi-stacking interactions
- **Developability**: Maintained (score 78 → 76, still Tier 1)
- **Validation**: 6 variants designed for experimental testing

---

## 1. Binding Interface Analysis

### 1.1 Current Interface Characterization

**Binding Properties**:
| Property | Value | Assessment |
|----------|-------|------------|
| Current KD | 15 nM | Moderate affinity |
| Buried surface area | 680 Å² | Below optimal (target >800 Å²) |
| Interface hotspots | 4 residues | Limited contacts |
| Dominant CDR | CDR-H3 (60%) | H3-focused binding |

**Hotspot Residues** (energy >1.5 kcal/mol):
| Residue | CDR | Contribution | Target Contact |
|---------|-----|--------------|----------------|
| Y100 (CDR-H3) | H3 | 2.8 kcal/mol | Phe domain IV |
| I52 (CDR-H2) | H2 | 1.9 kcal/mol | Leu domain IV |
| T28 (CDR-H1) | H1 | 1.6 kcal/mol | Ser domain IV |
| D100b (CDR-H3) | H3 | 1.5 kcal/mol | Arg domain IV |

### 1.2 Clinical Benchmark: Trastuzumab

| Antibody | KD | BSA | Clinical Status |
|----------|-----|-----|----------------|
| Trastuzumab | 0.1 nM | 950 Å² | Approved (Herceptin) |
| Pertuzumab | 0.5 nM | 920 Å² | Approved (Perjeta) |
| **Our antibody** | **15 nM** | **680 Å²** | **Pre-clinical** |

**Gap Analysis**: Need 150x affinity of trastuzumab unrealistic, but <5 nM is therapeutic threshold.

*Source: SAbDab, TheraSAbDab, interface analysis*

---

## 2. Affinity Optimization Strategy

### 2.1 Computational Mutation Screening

**Top Affinity Mutations** (predicted ΔΔG):

| Position | Original | Mutant | CDR | Predicted ΔΔG | KD Fold Improvement | Rationale |
|----------|----------|--------|-----|---------------|---------------------|-----------|
| H52 | I | W | H2 | -1.4 kcal/mol | **9.2x** | Large hydrophobic contact, pi-stacking |
| H100a | S | Y | H3 | -1.2 kcal/mol | **7.4x** | Pi-stacking with target Phe |
| H100b | D | E | H3 | -0.9 kcal/mol | **4.8x** | Optimized salt bridge to Arg |
| H28 | T | S | H1 | -0.7 kcal/mol | **3.3x** | Better H-bond geometry |
| H33 | A | Y | H1 | -0.6 kcal/mol | **2.7x** | New aromatic contact |
| L91 | Q | W | L3 | -0.5 kcal/mol | **2.3x** | Increased hydrophobic burial |

### 2.2 Designed Variants

**Single Mutants** (for testing individually):
1. H52W: Predicted KD 1.6 nM (9.4x)
2. H100aY: Predicted KD 2.0 nM (7.5x)
3. H100bE: Predicted KD 3.1 nM (4.8x)

**Combination Mutants** (if single mutants show improvement):
1. **H52W + H100aY**: Predicted KD **1.8 nM** (8.3x) - TOP CANDIDATE
2. H52W + H100bE: Predicted KD 2.5 nM (6.0x)
3. H100aY + H100bE: Predicted KD 2.8 nM (5.4x)

**Triple Mutant** (aggressive optimization):
1. H52W + H100aY + H100bE: Predicted KD 1.2 nM (12.5x) - if additivity holds

### 2.3 CDR-H3 Extension Strategy

**Alternative Approach**: Extend CDR-H3 for more contacts

Current CDR-H3: ARDLGDY (7 aa) - Short for HER2 binding
Proposed: ARDLGDYGSY (10 aa) - Add Gly-Ser-Tyr

**Rationale**:
- Trastuzumab CDR-H3: 12 aa (longer provides more contact area)
- Extension fills gap in interface (observed in structural model)
- Tyr provides additional pi-stacking

**Predicted improvement**: 3-5x (complementary to mutations)

---

## 3. Developability Impact Assessment

### 3.1 Developability Scores

| Variant | Aggregation | PTM | Stability | Expression | **Overall** | Change |
|---------|-------------|-----|-----------|------------|-------------|--------|
| Original | 72 | 78 | 75 | 82 | **78/100** | - |
| H52W | 68 | 78 | 74 | 80 | **76/100** | -2 |
| H100aY | 71 | 78 | 75 | 82 | **78/100** | 0 |
| **H52W+H100aY** | **69** | **78** | **74** | **80** | **76/100** | **-2** |

**Assessment**: Minor developability impact (-2 points). Still Tier 1 (>75).

### 3.2 Aggregation Impact

**H52W mutation**:
- Adds large hydrophobic Trp in CDR-H2
- Increases surface hydrophobicity slightly
- Risk: +0.04 aggregation score (68 vs 72)
- Mitigation: Not needed (still low risk)

**H100aY mutation**:
- Adds Tyr in CDR-H3 (buried in interface)
- No surface exposure → minimal aggregation impact
- Risk: Neutral (71 vs 72)

### 3.3 Stability Impact

**Predicted Tm Changes**:
- Original: 73°C
- H52W: 72°C (-1°C, acceptable)
- H100aY: 73°C (no change)
- H52W+H100aY: 72°C (-1°C, still >70°C target)

**Conclusion**: Stability maintained within acceptable range.

---

## 4. Testing Strategy

### 4.1 Phased Testing Plan

**Phase 1: Single Mutants** (Weeks 1-4)
- Express and purify: H52W, H100aY, H100bE
- Measure KD by SPR
- Select top 2 performers

**Phase 2: Combinations** (Weeks 5-8)
- Test combinations of best single mutants
- Assess additivity vs. synergy
- Measure developability (aggregation, stability)

**Phase 3: Optimization** (Weeks 9-12)
- Test CDR-H3 extension if needed
- Final developability characterization
- Produce material for in vivo studies

### 4.2 Success Criteria

| Milestone | Criteria | Decision |
|-----------|----------|----------|
| **Phase 1** | ≥1 single mutant with KD <8 nM (≥2x) | Proceed to Phase 2 |
| **Phase 2** | Combination with KD <5 nM (≥3x) | Success - scale up |
| **Phase 3** | Developability score >75, Tm >70°C | Clinical candidate |

### 4.3 Recommended Testing Order

1. **H100aY** (first) - Zero developability impact, good predicted improvement
2. **H52W** (second) - Highest predicted improvement, minor dev impact
3. **H100bE** (third) - Moderate improvement, backup option
4. **H100aY + H52W** (if both single mutants work) - Top combination
5. **CDR-H3 extension** (if needed) - Alternative strategy

---

## 5. Final Recommendations

### 5.1 Lead Candidate

**Variant: H100aY + H52W**
- Predicted KD: 1.8 nM (8.3x improvement, exceeds 3x target)
- Developability: 76/100 (maintained Tier 1)
- Risk: Low (both mutations well-tolerated)

**Sequence** (VH CDR regions changed):
```
CDR-H2: ...IIPIFGTANY → WPPIFGTANY (I52W)
CDR-H3: ...ARDSGDY → ARDYGDY (S100aY, renumbered)
```

### 5.2 Backup Candidates

1. **H100aY alone**: Predicted 2.0 nM, zero dev impact
2. **H52W alone**: Predicted 1.6 nM, minor dev impact
3. **Triple mutant** (H52W+H100aY+H100bE): Predicted 1.2 nM if additivity holds

### 5.3 Expected Outcomes

**Conservative Estimate** (50% of predicted improvement):
- Single mutants: 3-5x improvement → KD 3-5 nM
- Combination: 4-6x improvement → KD 2.5-3.8 nM
- **Still meets target** (<5 nM)

**Optimistic Estimate** (100% of predicted improvement):
- Combination: 8.3x improvement → KD 1.8 nM
- Exceeds target, competitive with clinical antibodies

---

## Data Sources

| Tool | Query | Results |
|------|-------|---------|
| AlphaFold | Antibody-HER2 complex | Interface analysis |
| TheraSAbDab | Anti-HER2 antibodies | Trastuzumab, Pertuzumab benchmarks |
| SAbDab | HER2 complex structures | PDB: 1N8Z (trastuzumab-HER2) |
| In silico screening | All amino acids at hotspots | Top 6 mutations |
```

---

## Example 3: Aggregation-Prone Antibody Redesign

### User Query
"This antibody aggregates at >50 mg/mL. Redesign to achieve >150 mg/mL formulation"

### Expected Output (Key Sections)

```markdown
# Aggregation Mitigation Report: mAb-X

**Original Concentration Limit**: 50 mg/mL | **Target**: >150 mg/mL | **Challenge**: Aggregation

---

## Executive Summary

Successfully identified and mitigated aggregation hotspots:
- **Root cause**: 3 aggregation-prone regions (APR) in VH framework
- **Strategy**: 5 targeted mutations to disrupt APRs without affecting binding
- **Result**: Aggregation score 0.68 → 0.22 (68% reduction)
- **Predicted max concentration**: >200 mg/mL (4x improvement)

**Recommended Candidate**: VH_AggMit_v2 with 3 critical mutations

---

## 1. Aggregation Analysis

### 1.1 Current Aggregation Profile

**SEC Analysis** (concentration-dependent):
| Concentration | Monomer % | Dimer % | HMW % | Assessment |
|---------------|-----------|---------|-------|------------|
| 10 mg/mL | 98.2% | 1.5% | 0.3% | Good |
| 50 mg/mL | 92.1% | 6.8% | 1.1% | Marginal |
| 100 mg/mL | 78.3% | 18.5% | 3.2% | Poor |
| 150 mg/mL | 65.4% | 28.7% | 5.9% | Unacceptable |

**Problem**: Concentration-dependent aggregation above 50 mg/mL

### 1.2 Aggregation-Prone Regions (APR)

**Identified APRs** (TANGO analysis):

| APR | Position | Sequence | TANGO Score | Region | Surface Exposed? |
|-----|----------|----------|-------------|--------|------------------|
| **APR1** | VH 85-92 | STSTAYMEL | **52** | FR3 | Partially (40%) |
| **APR2** | VH 18-24 | ASGYTFT | **38** | FR1/CDR-H1 | Yes (70%) |
| **APR3** | VL 78-84 | TLTISSL | **28** | FR3 | Yes (60%) |

**Hydrophobic Patches**:
- VH surface: 3 patches (>300 Å² each)
- VL surface: 1 patch (250 Å²)

**Charge Properties**:
- pI: VH 8.8 (high - prone to self-association)
- Net charge at pH 6: +4 (less than optimal)

### 1.3 Root Cause Analysis

**Primary Driver**: APR1 (STSTAYMEL in VH FR3)
- TANGO score 52 (high risk)
- Surface exposed (40%)
- Beta-aggregation motif

**Secondary Drivers**:
- APR2: Hydrophobic patch near CDR-H1
- High pI (8.8): Self-association at neutral pH
- Insufficient surface charge for electrostatic repulsion

*Source: TANGO, AGGRESCAN, surface analysis*

---

## 2. Aggregation Mitigation Strategy

### 2.1 Mutation Design

**APR1 Disruption** (VH 85-92: STSTAYMEL):

| Position | Original | Proposed | Rationale | Impact on Affinity? |
|----------|----------|----------|-----------|-------------------|
| T85 | T | **S** | Reduce beta-propensity | No (framework) |
| T86 | T | **K** | Add charge, break pattern | No (framework) |
| M91 | M | **Q** | Polar, reduces hydrophobicity | No (framework) |

**Expected TANGO reduction**: 52 → 18 (65% reduction)

**APR2 Disruption** (VH 18-24: ASGYTFT):

| Position | Original | Proposed | Rationale | Impact on Affinity? |
|----------|----------|----------|-----------|-------------------|
| A19 | A | **T** | Add polarity to patch | Low risk (FR1) |
| T24 | T | **S** | Minor polarity increase | Low risk (FR1) |

**Expected TANGO reduction**: 38 → 22 (42% reduction)

**pI Reduction** (reduce self-association):

| Position | Original | Proposed | Rationale | Impact on pI |
|----------|----------|----------|-----------|--------------|
| K73 | K | **E** | Lower pI, add negative charge | -0.3 units |
| R78 | R | **Q** | Lower pI | -0.2 units |

**Expected pI**: 8.8 → 8.3 (improved but still need formulation pH adjustment)

### 2.2 Designed Variants

**Variant 1 (Conservative)**: Disrupt APR1 only
- Mutations: T86K, M91Q
- Expected aggregation reduction: 40%
- Risk: Very low

**Variant 2 (Recommended)**: Disrupt APR1 + APR2
- Mutations: T85S, T86K, M91Q
- Expected aggregation reduction: 68%
- Risk: Low

**Variant 3 (Aggressive)**: All APRs + pI reduction
- Mutations: T85S, T86K, M91Q, A19T, K73E
- Expected aggregation reduction: 75%
- Risk: Medium (more mutations)

---

## 3. Developability Impact

### 3.1 Comprehensive Scores

| Property | Original | Variant 1 | **Variant 2** | Variant 3 |
|----------|----------|-----------|---------------|-----------|
| **Aggregation score** | 32 | 52 | **78** | 82 |
| PTM liability | 78 | 78 | 78 | 75 (K73E removes Lys) |
| Stability (Tm) | 72°C | 72°C | 71°C | 70°C |
| Expression | 80 | 80 | 80 | 78 |
| **Overall developability** | **68/100** | **74/100** | **80/100** | **79/100** |

**Recommendation**: Variant 2 offers best balance (80/100, Tier 1)

### 3.2 Predicted Formulation

**Original**:
- Max concentration: 50 mg/mL
- Viscosity at 50 mg/mL: 18 cP
- Stability: <1 year at 4°C

**Variant 2**:
- Max concentration: >200 mg/mL (predicted)
- Viscosity at 150 mg/mL: <15 cP (acceptable for SC)
- Stability: >2 years at 4°C (predicted)

---

## 4. Validation Plan

### 4.1 Testing Strategy

**Phase 1: Expression & Purification** (Weeks 1-3)
- Express all 3 variants
- Purify to >99% monomer
- Produce 100mg each for testing

**Phase 2: Aggregation Testing** (Weeks 3-6)
- SEC at multiple concentrations (10, 50, 100, 150, 200 mg/mL)
- DLS for particle size
- Viscosity measurements
- Stability: 4 weeks at 4°C, 25°C, 40°C

**Phase 3: Functional Validation** (Weeks 6-8)
- Binding affinity (SPR) - target <1.5x change
- Cell-based activity - target <2x EC50 change
- Thermal stability (DSF)

**Phase 4: Formulation** (Weeks 8-12)
- Optimize buffer, pH, excipients
- Long-term stability (3-6 months)
- Freeze/thaw cycles

### 4.2 Success Criteria

| Metric | Target | Decision |
|--------|--------|----------|
| Monomer at 150 mg/mL | >95% | Must pass |
| Viscosity at 150 mg/mL | <20 cP | Acceptable for SC |
| Affinity change | <2x | Maintain potency |
| Tm | >70°C | Adequate stability |

---

## 5. Final Recommendation

**Lead Candidate: Variant 2 (VH_AggMit_v2)**

**Mutations**:
```
VH: T85S, T86K, M91Q
VL: No changes
```

**Expected Performance**:
- Aggregation at 150 mg/mL: <5% (from 35%)
- Formulation concentration: 150-200 mg/mL
- Developability score: 80/100 (Tier 1)
- Affinity impact: <20% (acceptable)

**Recommended Formulation**:
- 150 mg/mL antibody
- 20 mM Histidine pH 6.0
- 0.02% Polysorbate 80
- 240 mM Sucrose
- Target: Stable >2 years at 2-8°C

---

## Data Sources

| Analysis | Tool/Method | Results |
|----------|-------------|---------|
| Aggregation prediction | TANGO, AGGRESCAN | 3 APRs identified |
| Surface analysis | PyMOL, AlphaFold structure | Hydrophobic patches mapped |
| pI calculation | Sequence analysis | pI 8.8 |
| Mutation design | In silico screening | 5 optimal mutations |
```

---

## Example 4: Bispecific Antibody Engineering

### User Query
"Design a bispecific antibody targeting PD-L1 and TIM-3 for cancer immunotherapy"

### Expected Output (Key Sections)

```markdown
# Bispecific Antibody Design Report: Anti-PD-L1 x Anti-TIM-3

**Format**: IgG-like bispecific | **Targets**: PD-L1 (Q9NZQ7) + TIM-3 (Q8TDQ0)

---

## Executive Summary

Successfully designed bispecific antibody targeting dual immune checkpoints:
- **Format**: CrossMAb (controlled Fab-arm exchange)
- **Arm 1**: Anti-PD-L1 (humanized, KD 3.2 nM)
- **Arm 2**: Anti-TIM-3 (humanized, KD 5.8 nM)
- **Fc**: IgG1 with silenced effector function (LALA-PG mutations)
- **Developability**: 74/100 (Tier 2, acceptable for bispecific)

**Key Innovation**: Dual checkpoint blockade provides synergistic anti-tumor activity

---

## 1. Target Analysis & Rationale

### 1.1 Target Biology

**PD-L1**:
- Function: Inhibits T-cell activation via PD-1 binding
- Expression: Tumor cells, immune cells
- Clinical validation: 3 approved antibodies (atezolizumab, durvalumab, avelumab)

**TIM-3**:
- Function: Exhaustion marker on T-cells, inhibits T-cell responses
- Expression: Activated T-cells, myeloid cells
- Clinical status: Phase I/II trials ongoing

**Rationale for Combination**:
- Complementary mechanisms: PD-L1 blocks tumor-T cell inhibition, TIM-3 reverses T-cell exhaustion
- Co-expression: 60% of tumors express both (STRING analysis)
- Synergy: Preclinical data shows 3-5x tumor growth inhibition vs. single agents

### 1.2 Co-Expression Analysis

**STRING Interaction Network**:
- PD-L1 (CD274) and TIM-3 (HAVCR2) co-expression score: 0.72 (high)
- Shared pathways: T-cell activation, immune checkpoint regulation
- Tumor types with high co-expression: Melanoma (78%), NSCLC (65%), RCC (58%)

**Clinical Precedent**:
- Several bispecific antibodies in development (e.g., RO7121661)
- Monotherapy combinations show enhanced efficacy vs. single agents

*Source: UniProt, STRING, TheraSAbDab, literature*

---

## 2. Bispecific Format Selection

### 2.1 Format Comparison

| Format | Advantages | Disadvantages | Suitability |
|--------|------------|---------------|-------------|
| **CrossMAb** | Native IgG-like, good PK, proven clinical | Complex manufacturing | **SELECTED** |
| IgG-scFv | Simpler than CrossMAb | Larger size, potential immunogenicity | Backup |
| Tandem scFv | Small, easy to produce | Poor PK, instability | Not suitable |
| DART | High affinity | Non-IgG format, short half-life | Not suitable |

**Selected**: CrossMAb with knob-into-hole Fc

### 2.2 CrossMAb Design

**Architecture**:
```
Arm 1 (Anti-PD-L1):  VH1-CH1 paired with VL1-CL (kappa)
                     ↓
Arm 2 (Anti-TIM-3):  VH2-CH1* paired with VL2-CL* (lambda)
                     ↓
                   Fc (IgG1-LALA-PG)
                   Knob-into-hole mutations
```

**Fc Engineering**:
- Knob (Chain A): S354C, T366W
- Hole (Chain B): Y349C, T366S, L368A, Y407V
- Effector silencing: L234A, L235A, P329G (LALA-PG)

**Rationale**:
- Knob-into-hole: Prevents homodimer formation (>95% heterodimer)
- CH1-CL domain crossover: Prevents mispaired light chains
- LALA-PG: Removes FcγR binding, prevents ADCC (want checkpoint blockade only)

---

## 3. Antibody Arm Design

### 3.1 Anti-PD-L1 Arm (Arm 1)

**Source**: Humanized from mouse antibody (Example 1)

| Property | Value |
|----------|-------|
| VH germline | IGHV1-69*01 |
| VL germline | IGKV1-39*01 (kappa) |
| Affinity (KD) | 3.2 nM |
| Humanness | 87% (VH), 90% (VL) |
| Developability | 79/100 |

**CDR Sequences**:
- CDR-H3: ARDDGSYSPFDYWG (14 aa, unique)
- Epitope: PD-L1 domain 19-113 (similar to atezolizumab)

### 3.2 Anti-TIM-3 Arm (Arm 2)

**Source**: De novo humanized antibody

| Property | Value |
|----------|-------|
| VH germline | IGHV3-23*01 |
| VL germline | IGLV2-14*01 (lambda) |
| Affinity (KD) | 5.8 nM |
| Humanness | 89% (VH), 92% (VL) |
| Developability | 76/100 |

**CDR Sequences**:
- CDR-H3: ARGSYYDAMDYWG (13 aa)
- Epitope: TIM-3 IgV domain (residues 22-118)

**Note**: Lambda light chain chosen to enable CH1-CL crossover in CrossMAb format

---

## 4. Developability Assessment

### 4.1 Bispecific Developability

**Complexity Factors**:
- 4 unique chains (2 heavy, 2 light) vs. 2 in normal IgG
- Assembly: Requires correct HC-LC pairing and HC-HC heterodimerization
- Aggregation risk: Higher than monospecific (more interfaces)

**Developability Scores**:

| Property | Arm 1 (PD-L1) | Arm 2 (TIM-3) | **Bispecific** | Target |
|----------|---------------|---------------|----------------|--------|
| Aggregation | 78 | 72 | **68** | >60 |
| PTM liability | 78 | 75 | **76** | >70 |
| Stability (Tm) | 73°C | 71°C | **70°C** | >68°C |
| Expression | 80 | 75 | **65** | >60 |
| **Overall** | **79/100** | **76/100** | **74/100** | **>70** |

**Assessment**: Tier 2 (70-75), acceptable for bispecific format

### 4.2 Assembly & Pairing

**Predicted Pairing Efficiency**:
- HC-HC heterodimerization (knob-into-hole): >95%
- HC-LC correct pairing (CH1-CL crossover): >90%
- Overall correct assembly: >85%

**Purification Strategy**:
- Step 1: Protein A (capture all IgG-like molecules)
- Step 2: Ion exchange (separate mispaired species)
- Expected yield: 60-70% (acceptable for bispecific)

### 4.3 Immunogenicity Assessment

**T-Cell Epitopes**:
- Arm 1: 4 predicted epitopes (low risk)
- Arm 2: 5 predicted epitopes (low-medium risk)
- Fc junctions: 2 additional epitopes from knob-into-hole mutations

**Overall Risk**: Medium (acceptable, monitoring required in clinic)

**Mitigation**:
- High humanization (87-92%) reduces risk
- LALA-PG mutations are validated in clinic (e.g., atezolizumab uses similar)
- Knob-into-hole epitopes: Low risk based on clinical precedent

---

## 5. Functional Design

### 5.1 Binding Characteristics

**Monovalent Binding** (CrossMAb = 1 arm per target):

| Target | Arm | KD (bivalent IgG) | KD (monovalent) | Avidity Effect |
|--------|-----|-------------------|-----------------|----------------|
| PD-L1 | 1 | 0.8 nM | **3.2 nM** | 4x loss (expected) |
| TIM-3 | 2 | 1.5 nM | **5.8 nM** | 4x loss (expected) |

**Rationale**: Monovalent binding acceptable for checkpoint inhibitors (functional antagonism, not receptor crosslinking)

### 5.2 Predicted Functional Activity

**Cell-Based Assays**:
- PD-L1 blockade: EC50 ~10 nM (target <20 nM)
- TIM-3 blockade: EC50 ~15 nM (target <30 nM)
- Dual blockade: Synergistic enhancement (3-5x vs. single agents)

**In Vivo Efficacy** (predicted):
- Tumor growth inhibition: 70-80% (vs. 40-50% for single agents)
- T-cell infiltration: 2-3x increase
- PK: t1/2 ~14 days (standard IgG)

---

## 6. Manufacturing Considerations

### 6.1 Expression Strategy

**Co-transfection** (4-plasmid system):
- Plasmid 1: VH1-CH1-Fc(knob)-LALA-PG
- Plasmid 2: VH2-CH1*-Fc(hole)-LALA-PG
- Plasmid 3: VL1-CL (kappa)
- Plasmid 4: VL2-CL* (lambda)

**Cell Line**: CHO-K1 or CHO-S

**Expected Titer**: 0.8-1.2 g/L (lower than monospecific, typical for bispecifics)

### 6.2 Purification & Analytics

**Purification** (3-4 steps):
1. Protein A affinity (capture)
2. Cation exchange (remove mispaired species)
3. Hydrophobic interaction chromatography (polish)
4. Viral inactivation (low pH hold)

**Critical Analytics**:
- Intact mass: Confirm correct assembly (4 chains)
- Reduced/non-reduced CE-SDS: Chain purity
- IEX or HIC: Separate bispecific from mispaired products
- Dual binding ELISA: Confirm both arms functional

---

## 7. Final Recommendations

### 7.1 Recommended Design

**Bispecific: BsAb-PDL1xTIM3-CrossMAb-v1**

**Composition**:
```
Heavy Chain 1 (Knob): VH1(anti-PD-L1) - CH1 - Fc(S354C,T366W,LALA-PG)
Heavy Chain 2 (Hole): VH2(anti-TIM-3) - CH1* - Fc(Y349C,T366S,L368A,Y407V,LALA-PG)
Light Chain 1: VL1(anti-PD-L1) - CL-kappa
Light Chain 2: VL2(anti-TIM-3) - CL-lambda*
```
*CH1-CL domain crossover for correct pairing

### 7.2 Development Timeline

| Phase | Duration | Activities | Milestones |
|-------|----------|------------|------------|
| Gene construction | 2 months | Synthesize 4 genes, clone vectors | Plasmids ready |
| Expression optimization | 3 months | Transient expression, optimize ratios | Titer >0.5 g/L |
| Stable cell line | 6 months | CHO cell line development | GMP-ready line |
| Characterization | 4 months | Analytics, potency, PK | IND-ready |
| **Total to IND** | **15 months** | - | - |

### 7.3 Clinical Strategy

**Indication**: Advanced solid tumors with PD-L1+/TIM-3+ expression
- Phase 1: Dose escalation, safety (n=30-40)
- Phase 1b: Expansion in melanoma, NSCLC, RCC (n=60-90)
- Phase 2: Efficacy vs. anti-PD-L1 monotherapy (n=150-200)

**Competitive Advantage**:
- Dual checkpoint blockade in single molecule
- Potentially improved efficacy vs. combination therapy
- Better PK/dosing vs. two separate antibodies

---

## Data Sources

| Tool | Query | Results |
|------|-------|---------|
| STRING_get_interactions | PD-L1, TIM-3 | Co-expression analysis |
| TheraSAbDab_search_by_target | PD-L1, TIM-3 | Clinical precedents |
| UniProt | Q9NZQ7, Q8TDQ0 | Target biology |
| AlphaFold | VH-VL complexes | Structure models |
| IMGT | IGHV, IGKV, IGLV genes | Germline sequences |
```

---

## Example 5: pH-Dependent Binding Optimization

### User Query
"Engineer pH-dependent binding into this anti-HER2 antibody for improved PK via FcRn recycling"

### Expected Output (Key Sections)

```markdown
# pH-Dependent Binding Engineering: Anti-HER2 Antibody

**Goal**: Bind at pH 7.4 (blood), release at pH 6.0 (endosome) | **Application**: Enhanced PK and tumor selectivity

---

## Executive Summary

Successfully engineered pH-dependent binding via histidine substitutions:
- **Strategy**: Introduce His residues at binding interface (pKa ~6.0)
- **Result**: 20-fold weaker binding at pH 6.0 vs. pH 7.4
- **PK benefit**: Predicted 2-3x longer half-life via enhanced FcRn recycling
- **Affinity maintained**: KD 2.1 nM at pH 7.4 (acceptable therapeutic range)

**Recommended Candidate**: pH-HER2-v3 with 3 His substitutions

---

## 1. pH-Dependent Binding Rationale

### 1.1 Mechanism

**FcRn Recycling**:
- Antibodies internalized into endosomes (pH 6.0)
- FcRn binding: Antibody rescued from lysosomal degradation
- FcRn dissociates at pH 7.4: Antibody released back to blood
- **Problem**: Antigen-bound antibody stays in endosome longer → faster clearance

**Solution**: pH-dependent antigen binding
- Bind antigen at pH 7.4 (blood, tumor)
- Release antigen at pH 6.0 (endosome)
- Free antibody recycled by FcRn → longer half-life
- **Benefit**: 2-3x half-life extension + tumor selectivity (acidic microenvironment)

### 1.2 Clinical Precedent

**Antibodies with pH-Dependent Binding**:
| Antibody | Target | pH Ratio (KD 7.4/6.0) | Half-life Extension | Status |
|----------|--------|----------------------|---------------------|--------|
| MEDI4276 | HER2 | 15x | ~2x | Phase I/II |
| M111 | EGFR | 25x | ~3x | Preclinical |

**Our Goal**: 10-20x pH ratio, 2-3x half-life improvement

*Source: Literature, TheraSAbDab*

---

## 2. Histidine Engineering Strategy

### 2.1 Histidine Properties

**pKa ~6.0**: Protonated (charged) at pH <6, deprotonated (neutral) at pH >7
- At pH 7.4: Neutral → favorable for binding (hydrophobic/pi-stacking)
- At pH 6.0: Protonated (+charge) → unfavorable if destabilizes interface

**Design Principle**: Place His at positions where protonation disrupts binding

### 2.2 Interface Analysis

**Current Binding Interface** (anti-HER2):

| Residue | CDR | Type | Target Contact | Energy | His Candidate? |
|---------|-----|------|----------------|--------|----------------|
| Y100 | H3 | Hydrophobic | HER2 Phe | 2.8 kcal/mol | **YES** - Tyr→His maintains pi-stacking at pH 7.4 |
| D100b | H3 | Charged | HER2 Arg | 1.9 kcal/mol | **YES** - Asp→His flips charge at pH 6.0 |
| T28 | H1 | Polar | HER2 Asp | 1.6 kcal/mol | **YES** - Thr→His adds charge at pH 6.0 |
| I52 | H2 | Hydrophobic | HER2 Leu | 1.5 kcal/mol | No - His too polar |

### 2.3 Designed Variants

**Variant 1 (Conservative)**: Single His substitution
- Mutation: D100bH (CDR-H3)
- Rationale: Charge flip (Asp- → His+) at pH 6.0 disrupts salt bridge
- Predicted pH ratio: 5-8x

**Variant 2 (Moderate)**: Two His substitutions
- Mutations: Y100H, D100bH (both CDR-H3)
- Rationale: Dual mechanism (pi-stacking loss + charge flip)
- Predicted pH ratio: 12-18x

**Variant 3 (Aggressive)**: Three His substitutions
- Mutations: T28H (CDR-H1), Y100H (CDR-H3), D100bH (CDR-H3)
- Rationale: Maximize pH sensitivity
- Predicted pH ratio: 20-30x

---

## 3. Computational Predictions

### 3.1 Affinity Predictions

**Variant 2 (Recommended)**:

| pH | Predicted KD | Fold Change | Assessment |
|----|--------------|-------------|------------|
| **7.4** | **2.1 nM** | 1.0x (baseline) | Therapeutic range (acceptable) |
| 7.0 | 4.2 nM | 2.0x | Moderate weakening |
| 6.5 | 12.5 nM | 6.0x | Significant weakening |
| **6.0** | **38 nM** | **18x** | **Strong pH dependence** ✓ |
| 5.5 | 95 nM | 45x | Very weak binding |

**pH Ratio**: 18x (target: 10-20x) → Meets design goal

### 3.2 Structure Predictions (AlphaFold)

**Variant 2 Structure Quality**:
| pH | Mean pLDDT | CDR pLDDT | Interface pLDDT | Status |
|----|------------|-----------|-----------------|--------|
| 7.4 | 87.9 | 84.2 | 86.1 | High confidence |
| 6.0 | 86.5 | 83.8 | 79.3 | Lower interface confidence (expected) |

**Interpretation**: Structure maintained, but interface destabilized at pH 6.0 (desired)

---

## 4. Developability Assessment

### 4.1 Impact on Developability

| Property | Original | Variant 1 | Variant 2 | Variant 3 |
|----------|----------|-----------|-----------|-----------|
| Affinity (pH 7.4) | 0.8 nM | 1.5 nM | **2.1 nM** | 3.8 nM |
| pH ratio | 1x | 6x | **18x** | 28x |
| Aggregation | 75 | 73 | **72** | 68 |
| Stability (Tm) | 73°C | 72°C | **71°C** | 69°C |
| **Developability** | **78/100** | **76/100** | **75/100** | **71/100** |

**Recommendation**: Variant 2 balances pH dependence (18x) with acceptable affinity (2.1 nM) and developability (75/100, Tier 1)

### 4.2 Histidine Stability

**His Oxidation Risk**:
- His residues susceptible to oxidation (especially if surface-exposed)
- CDR-H3 His: Buried in interface at pH 7.4 → Low oxidation risk
- CDR-H1 His (T28H): Partially exposed → Medium risk

**Mitigation** (if oxidation observed):
- Formulate with Met (sacrificial oxidation target)
- Use inert atmosphere during manufacturing
- Add EDTA to chelate metal ions

---

## 5. Predicted PK Improvement

### 5.1 PK Modeling

**Assumptions**:
- Standard FcRn-mediated recycling
- pH-dependent antigen release enhances recycling
- Tumor microenvironment pH: 6.5-7.0 (partial selectivity)

**Predicted Parameters**:

| Antibody | t1/2 (days) | Clearance (mL/day/kg) | AUC Fold | Tumor/Blood Ratio |
|----------|-------------|----------------------|----------|-------------------|
| Original | 14 | 4.5 | 1.0x | 1.5 |
| pH-Variant 2 | **32** | **2.0** | **2.3x** | **2.8** |

**Benefits**:
1. **Longer half-life**: 14 → 32 days (2.3x)
2. **Lower clearance**: Enhanced FcRn recycling
3. **Tumor selectivity**: 2.8x accumulation (acidic microenvironment)
4. **Dosing**: Potentially Q4W instead of Q3W

### 5.2 Tumor Selectivity

**pH Gradient**:
- Blood pH: 7.4
- Tumor microenvironment: 6.5-7.0 (acidic due to glycolysis)
- Normal tissue: 7.4

**Binding at Different pH**:
| Location | pH | KD | Binding Efficiency |
|----------|-----|--------|-------------------|
| Blood | 7.4 | 2.1 nM | 100% (baseline) |
| Tumor | 6.8 | 6.5 nM | 65% (moderate) |
| Tumor | 6.5 | 12.5 nM | 35% (lower) |
| Endosome | 6.0 | 38 nM | 10% (release) |

**Advantage**: Preferential accumulation in tumors (acidic) vs. normal tissue

---

## 6. Experimental Validation Plan

### 6.1 In Vitro Characterization

**Phase 1: pH-Dependent Binding** (Weeks 1-3)
- SPR at multiple pH (5.5, 6.0, 6.5, 7.0, 7.4)
- Calculate pH ratio: KD(pH 7.4) / KD(pH 6.0)
- Target: 10-20x ratio
- Cell-based binding: Flow cytometry at pH 7.4 vs 6.5

**Phase 2: Developability** (Weeks 3-6)
- Aggregation: SEC at pH 6.0 and 7.4
- Stability: DSF, long-term storage (4°C, 3 months)
- His oxidation: Forced degradation, LC-MS

**Phase 3: Functional Activity** (Weeks 6-8)
- Cell proliferation inhibition (pH 7.4)
- Antibody-dependent cellular cytotoxicity (ADCC)
- Internalization assay (pH switching)

### 6.2 In Vivo PK Studies

**Study Design**:
- Species: Cynomolgus monkey (human FcRn ortholog)
- Dose: 10 mg/kg IV
- Comparison: pH-variant vs. original antibody
- PK sampling: 0-56 days
- Endpoints: t1/2, CL, AUC, Vss

**Success Criteria**:
- t1/2 improvement: >1.5x (target 2-3x)
- Tumor accumulation: >1.5x (if xenograft model)

---

## 7. Final Recommendation

**Lead Candidate: pH-HER2-v2**

**Mutations**:
```
CDR-H3: Y100H, D100bH
```

**Performance Summary**:
| Metric | Value | Assessment |
|--------|-------|------------|
| Affinity (pH 7.4) | 2.1 nM | Therapeutic range |
| pH ratio | 18x | Excellent pH dependence |
| Predicted t1/2 | 32 days | 2.3x improvement |
| Developability | 75/100 | Tier 1 (acceptable) |
| Tumor selectivity | 2.8x | Enhanced |

**Next Steps**:
1. **Gene synthesis & expression** (Month 1)
2. **In vitro validation** (Month 2-3): Confirm pH-dependent binding
3. **PK study** (Month 4-6): Cynomolgus monkey, compare to original
4. **Efficacy study** (Month 7-9): Tumor xenograft, assess selectivity
5. **IND filing** (Month 12-18): If PK/efficacy confirmed

---

## Data Sources

| Tool | Query | Results |
|------|-------|---------|
| AlphaFold | Antibody-HER2 complex | Interface analysis |
| Literature | pH-dependent antibodies | Clinical precedent |
| In silico modeling | His mutations | pH-dependent KD predictions |
| PK modeling | FcRn recycling | Half-life predictions |
```
