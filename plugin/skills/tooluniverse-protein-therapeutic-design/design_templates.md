# Protein Design: Report Templates and Output Formats

---

## Report Template

```markdown
# Therapeutic Protein Design Report: [TARGET]

**Generated**: [Date] | **Query**: [Original query] | **Status**: In Progress

---

## Executive Summary
[Designing...]

---

## 1. Target Characterization
### 1.1 Target Information
| Property | Value |
|----------|-------|
| **Target** | [Name] |
| **UniProt** | [ID] |
| **Structure source** | [PDB/EMDB/AlphaFold] |
| **Binding epitope** | [Description] |
| **Known binders** | [List] |

### 1.2 Epitope Analysis
| Residue Range | Type | Surface Area | Druggability |
|---------------|------|--------------|--------------|

### 1.2b Cryo-EM Structures (if membrane protein)
| EMDB ID | Resolution | PDB Model | Conformation |
|---------|------------|-----------|--------------|

---

## 2. Backbone Generation
### 2.1 Design Parameters
| Parameter | Value |
|-----------|-------|
| **Method** | RFdiffusion via NVIDIA NIM |
| **Design mode** | [mode] |
| **Diffusion steps** | [N] |

### 2.2 Generated Backbones
| Backbone | Length | Topology | Quality |
|----------|--------|----------|---------|

---

## 3. Sequence Design
### 3.1 Design Parameters
| Parameter | Value |
|-----------|-------|
| **Method** | ProteinMPNN via NVIDIA NIM |
| **Temperature** | [value] |
| **Sequences per backbone** | [N] |

### 3.2 Designed Sequences (Top 10)
| Rank | Backbone | Sequence ID | Length | MPNN Score | pI |
|------|----------|-------------|--------|------------|-----|

---

## 4. Structure Validation
| Sequence | pLDDT | pTM | RMSD to Design | Status |
|----------|-------|-----|----------------|--------|

---

## 5. Developability Assessment
| Design | Aggregation | pI | Cysteines | Expression | Overall |
|--------|-------------|-----|-----------|------------|---------|

---

## 6. Final Candidates
### 6.1 Ranked List
### 6.2 Sequences for Testing

---

## 7. Experimental Recommendations

---

## 8. Data Sources
```

---

## EMDB Structure Table (for membrane proteins)

When targeting membrane proteins, prioritize cryo-EM structures:

```markdown
### Cryo-EM Structures (EMDB)

| EMDB ID | Resolution | PDB Model | Conformation |
|---------|------------|-----------|--------------|
| EMD-12345 | 2.8 A | 7ABC | Active state |
| EMD-23456 | 3.1 A | 8DEF | Inactive state |

**Note**: Cryo-EM structures capture physiologically relevant conformations.
```

---

## Design Entry Format

```markdown
### Design: Binder_001

**Sequence**: MVLSPADKTN...
**Length**: 85 amino acids
**Target**: PD-L1 (UniProt: Q9NZQ7)
**Method**: RFdiffusion -> ProteinMPNN -> ESMFold validation

**Quality Metrics**:
| Metric | Value | Interpretation |
|--------|-------|----------------|
| pLDDT | 88.5 | High confidence |
| pTM | 0.82 | Good fold |
| ProteinMPNN score | -2.3 | Favorable |
| Predicted binding | Strong | Based on interface pLDDT |

*Source: NVIDIA NIM*
```
