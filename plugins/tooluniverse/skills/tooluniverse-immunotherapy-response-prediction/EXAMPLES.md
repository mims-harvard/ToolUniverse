# Immunotherapy Response Prediction - Examples

## Example 1: High-Biomarker NSCLC (Expected: HIGH Response)

**Input**: "NSCLC patient, TMB 25 mut/Mb, PD-L1 TPS 80%, no STK11/EGFR mutations. Predict ICI response."

**Expected Score Breakdown**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 25 (High) | 30 |
| MSI | Unknown | 10 |
| PD-L1 | 80% (High) | 20 |
| Neoantigens | Est. moderate | 10 |
| Resistance | None | 0 |
| Sensitivity | None | 0 |
| **TOTAL** | | **70** |

**Expected Recommendation**: Pembrolizumab monotherapy (KEYNOTE-024: 44.8% ORR, 10.3mo PFS with PD-L1>=50%)

---

## Example 2: Melanoma with BRAF V600E

**Input**: "Melanoma, BRAF V600E, TP53 R175H, TMB 15 mut/Mb, PD-L1 50%, MSS"

**Expected Score Breakdown**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 15 (Intermediate) | 20 |
| MSI | MSS | 5 |
| PD-L1 | 50% | 20 |
| Neoantigens | Moderate (~10-20) | 10 |
| Resistance | None ICI-specific | 0 |
| Sensitivity | None | 0 |
| **TOTAL** | | **55** |

**Expected Recommendation**: MODERATE response. Consider:
1. ICI first if no rapid progression risk: pembrolizumab or nivolumab
2. BRAF/MEK targeted (dabrafenib+trametinib) if rapid response needed
3. Nivolumab + ipilimumab for aggressive approach

---

## Example 3: MSI-High Colorectal Cancer

**Input**: "Colorectal cancer, MSI-high, TMB 40 mut/Mb"

**Expected Score Breakdown**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 40 (High) | 30 |
| MSI | MSI-H | 25 |
| PD-L1 | Unknown | 10 |
| Neoantigens | High (MSI-H) | 15 |
| Resistance | None | 0 |
| Sensitivity | High TMB/MSI-H | 5 |
| **TOTAL** | | **85** |

**Expected Recommendation**: HIGH response. Pembrolizumab first-line (KEYNOTE-177: 43.8% ORR, 16.5mo PFS)

---

## Example 4: Low-Biomarker NSCLC with Resistance

**Input**: "NSCLC, TMB 2 mut/Mb, PD-L1 <1%, STK11 loss of function mutation"

**Expected Score Breakdown**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 2 (Very Low) | 5 |
| MSI | Unknown | 10 |
| PD-L1 | <1% | 5 |
| Neoantigens | Low | 5 |
| Resistance | STK11 loss | -10 |
| Sensitivity | None | 0 |
| **TOTAL** | | **15** |

**Expected Recommendation**: LOW response. ICI monotherapy unlikely effective.
1. Platinum-based chemotherapy preferred
2. Consider ICI + chemotherapy combination (may have modest benefit)
3. Clinical trial enrollment

---

## Example 5: Bladder Cancer Moderate Profile

**Input**: "Bladder cancer, TMB 12 mut/Mb, PD-L1 CPS 10, no resistance mutations"

**Expected Score Breakdown**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 12 (Intermediate) | 20 |
| MSI | Unknown | 10 |
| PD-L1 | 10% (Positive) | 12 |
| Neoantigens | Moderate | 10 |
| Resistance | None | 0 |
| Sensitivity | None | 0 |
| **TOTAL** | | **52** |

**Expected Recommendation**: MODERATE response.
1. Pembrolizumab (second-line, KEYNOTE-045: 21.1% ORR)
2. Atezolizumab (second-line option)
3. Avelumab maintenance after platinum

---

## Example 6: RCC (Renal Cell Carcinoma)

**Input**: "Clear cell RCC, no specific mutations reported, PD-L1 positive"

**Expected Score Breakdown**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | Unknown | 15 (neutral, RCC context) |
| MSI | Unknown | 10 |
| PD-L1 | Positive (1-49%) | 12 |
| Neoantigens | Unknown | 8 |
| Resistance | None known | 0 |
| Sensitivity | None | 0 |
| **TOTAL** | | **45** |

**Expected Recommendation**: MODERATE response (RCC is ICI-responsive despite low TMB).
1. Nivolumab + ipilimumab (CheckMate-214: 42% ORR for intermediate/poor risk)
2. Pembrolizumab + axitinib (KEYNOTE-426: 59% ORR)
3. Nivolumab + cabozantinib (CheckMate-9ER)

Note: RCC is a special case where TMB is not as predictive.

---

## Example 7: HNSCC with CPS

**Input**: "Head and neck squamous cell carcinoma, PD-L1 CPS 25, TMB 8 mut/Mb"

**Expected Score**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 8 (Low) | 10 |
| MSI | Unknown | 10 |
| PD-L1 | CPS 25 (High) | 20 |
| Neoantigens | Low-Moderate | 8 |
| Resistance | None | 0 |
| **TOTAL** | | **48** |

**Expected Recommendation**: MODERATE response. Pembrolizumab monotherapy (KEYNOTE-048: CPS>=20, 23.3% ORR mono, 36% combo)

---

## Example 8: Edge Case - Conflicting Biomarkers

**Input**: "NSCLC, TMB 30 mut/Mb (high), PD-L1 <1% (negative), JAK2 mutation"

**Expected Score**:
| Component | Value | Score |
|-----------|-------|-------|
| TMB | 30 (High) | 30 |
| MSI | Unknown | 10 |
| PD-L1 | <1% | 5 |
| Neoantigens | Moderate-High | 12 |
| Resistance | JAK2 mutation | -10 |
| **TOTAL** | | **47** |

**Expected Recommendation**: MODERATE but with caveats. High TMB suggests neoantigen load, but JAK2 mutation may impair IFN-gamma signaling. Consider combination ICI or clinical trial.
