# Precision Oncology - Examples

## Example 1: EGFR-Mutant NSCLC (First-Line)

### User Query
"Patient with stage IV NSCLC, molecular testing shows EGFR L858R mutation. What are the treatment options?"

### Expected Output

```markdown
# Precision Oncology Report

**Date**: 2026-02-04

## Patient Profile
- **Diagnosis**: Stage IV Non-Small Cell Lung Cancer (NSCLC)
- **Molecular Profile**: EGFR L858R mutation
- **Prior Therapy**: Treatment-naive

---

## Executive Summary

This patient has an EGFR L858R-driven NSCLC with multiple FDA-approved targeted therapy options. **Recommended first-line treatment: Osimertinib (Tagrisso)** based on FLAURA trial data showing superior PFS and OS compared to earlier-generation TKIs. Alternative options include erlotinib or gefitinib if osimertinib is unavailable.

---

## 1. Variant Interpretation

| Variant | Gene | Significance | Evidence Level | Clinical Implication |
|---------|------|--------------|----------------|---------------------|
| L858R | EGFR | Activating, oncogenic driver | ★★★ (Level A) | Sensitive to EGFR TKIs |

**Details**: L858R is the most common EGFR activating mutation (~40-45% of EGFR-mutant NSCLC). Located in exon 21, it increases kinase activity and sensitivity to EGFR tyrosine kinase inhibitors.

*Source: CIViC EID:883, ClinVar VCV000016610*

---

## 2. Treatment Recommendations

### First-Line Options

**1. Osimertinib (Tagrisso)** ★★★ RECOMMENDED
- **Approval**: FDA-approved first-line for EGFR-mutant NSCLC (2018)
- **Dosing**: 80 mg PO daily
- **Evidence**: FLAURA trial - mPFS 18.9 mo vs 10.2 mo (erlotinib/gefitinib), mOS 38.6 mo vs 31.8 mo
- **Advantages**: CNS penetration, activity against T790M if it emerges
- **Source**: FDA label, PMID:29151359

**2. Erlotinib (Tarceva)** ★★★
- **Approval**: FDA-approved for EGFR exon 19 del or L858R
- **Dosing**: 150 mg PO daily
- **Evidence**: EURTAC trial - mPFS 9.7 mo vs 5.2 mo (chemotherapy)
- **Source**: FDA label, PMID:22452896

**3. Gefitinib (Iressa)** ★★★
- **Approval**: FDA-approved for EGFR-mutant NSCLC
- **Dosing**: 250 mg PO daily
- **Evidence**: IPASS trial established EGFR-TKI paradigm
- **Source**: FDA label, PMID:19692680

### Second-Line (After Progression)

**If T790M emerges**: Switch to osimertinib (if not used first-line)
**If non-T790M resistance**: Consider combination strategies or clinical trials

---

## 3. Resistance Analysis

**Not applicable** - Patient is treatment-naive.

**Anticipated resistance mechanisms to monitor**:
- T790M mutation (~50-60% of osimertinib-naive patients on 1st/2nd gen TKIs)
- C797S mutation (after osimertinib)
- MET amplification
- HER2 amplification
- Small cell transformation

---

## 4. Clinical Trial Options

| NCT ID | Phase | Agent | Biomarker | Status |
|--------|-------|-------|-----------|--------|
| NCT04487080 | 2 | Amivantamab + lazertinib | EGFR-mutant | Recruiting |
| NCT05388669 | 3 | Patritumab deruxtecan | EGFR-mutant | Recruiting |
| NCT04862780 | 2 | Osimertinib + savolitinib | EGFR-mutant | Recruiting |

*Source: ClinicalTrials.gov, accessed 2026-02-04*

---

## 5. Next Steps

1. **Initiate osimertinib 80 mg daily** as first-line therapy
2. **Baseline brain MRI** given CNS tropism of NSCLC
3. **Educate patient** on common side effects (rash, diarrhea, QTc)
4. **Schedule reassessment** at 8-12 weeks with imaging
5. **Plan liquid biopsy** at progression for resistance profiling

---

## Data Sources

| Source | Query | Data Retrieved |
|--------|-------|----------------|
| CIViC | EGFR L858R | Evidence items (Level A, Predictive) |
| OpenTargets | ENSG00000146648 | Approved drugs (7) |
| ClinicalTrials.gov | EGFR NSCLC Recruiting | 47 trials |
```

---

## Example 2: Acquired Resistance (T790M)

### User Query
"Patient was on erlotinib for EGFR-mutant lung cancer for 14 months, now progressing. Liquid biopsy shows T790M. What next?"

### Expected Output

```markdown
# Precision Oncology Report

**Date**: 2026-02-04

## Patient Profile
- **Diagnosis**: Stage IV NSCLC, EGFR-mutant
- **Molecular Profile**: EGFR L858R + T790M (acquired)
- **Prior Therapy**: Erlotinib x 14 months → progression

---

## Executive Summary

Patient has developed T790M-mediated resistance, the most common mechanism after 1st/2nd generation EGFR TKIs. **Recommended: Switch to osimertinib**, a 3rd-generation TKI specifically designed for T790M. This is FDA-approved with strong Level A evidence.

---

## 1. Variant Interpretation

| Variant | Gene | Significance | Evidence Level | Clinical Implication |
|---------|------|--------------|----------------|---------------------|
| L858R | EGFR | Activating driver | ★★★ | Original sensitizing mutation |
| T790M | EGFR | Acquired resistance | ★★★ | Resistant to erlotinib, sensitive to osimertinib |

**Mechanism**: T790M substitutes threonine with bulkier methionine at the "gatekeeper" position (codon 790). This creates steric hindrance blocking erlotinib binding while the kinase remains active. Osimertinib covalently binds C797, bypassing T790M.

*Source: CIViC EID:1021, PMID:23948351*

---

## 2. Treatment Recommendations

### Recommended

**Osimertinib (Tagrisso)** ★★★
- **Approval**: FDA-approved for T790M+ NSCLC (2015, accelerated; 2017, regular)
- **Dosing**: 80 mg PO daily
- **Evidence**: AURA3 trial - mPFS 10.1 mo vs 4.4 mo (chemotherapy), ORR 71%
- **Source**: FDA label, PMID:27959700

### Alternatives (if osimertinib unavailable)

**Chemotherapy (platinum + pemetrexed)** ★★☆
- Standard salvage if targeted therapy not feasible
- mPFS ~5 months in this setting

---

## 3. Resistance Analysis

### Current Resistance Mechanism: T790M

**Structural basis**: T790M mutation substitutes the "gatekeeper" threonine-790 with methionine. The bulkier methionine side chain sterically blocks binding of 1st/2nd-generation reversible EGFR TKIs (erlotinib, gefitinib, afatinib).

[Structure-based visualization could be generated with NvidiaNIM if needed]

### Future Resistance Concerns (after osimertinib)

| Mechanism | Frequency | Detection | Options |
|-----------|-----------|-----------|---------|
| C797S (cis) | ~20% | Liquid biopsy | Combination strategies, trials |
| C797S (trans) | ~5% | Liquid biopsy | 1st-gen TKI may work |
| MET amp | ~15% | NGS, FISH | MET inhibitor combination |
| HER2 amp | ~5% | NGS, FISH | HER2-directed therapy |
| SCLC transformation | ~5% | Biopsy | Platinum-etoposide |

*Source: PMID:29106415*

---

## 4. Clinical Trial Options

| NCT ID | Phase | Agent | Rationale | Status |
|--------|-------|-------|-----------|--------|
| NCT04487080 | 2 | Amivantamab + lazertinib | EGFR/MET bispecific | Recruiting |
| NCT05338970 | 2 | BBT-176 | 4th-gen TKI | Recruiting |

---

## 5. Next Steps

1. **Start osimertinib 80 mg daily** immediately
2. **Reassess response** at 8 weeks with CT
3. **Repeat liquid biopsy** at progression to identify next resistance mechanism
4. **Consider clinical trial enrollment** proactively for post-osimertinib options
```

---

## Example 3: KRAS G12C (Limited Options)

### User Query
"Stage IV lung adenocarcinoma with KRAS G12C mutation, failed platinum-based chemotherapy. Options?"

### Expected Output

```markdown
# Precision Oncology Report

**Date**: 2026-02-04

## Patient Profile
- **Diagnosis**: Stage IV Lung Adenocarcinoma
- **Molecular Profile**: KRAS G12C
- **Prior Therapy**: Platinum-based chemotherapy (failed)

---

## Executive Summary

KRAS G12C is now a druggable target with FDA-approved inhibitors. **Recommended: Sotorasib (Lumakras) or adagrasib (Krazati)** as second-line treatment. Both are covalent KRAS G12C inhibitors with demonstrated clinical benefit.

---

## 1. Variant Interpretation

| Variant | Gene | Significance | Evidence Level | Clinical Implication |
|---------|------|--------------|----------------|---------------------|
| G12C | KRAS | Oncogenic driver | ★★★ | Targetable with G12C inhibitors |

**Details**: KRAS G12C is found in ~13% of NSCLC. The cysteine substitution at codon 12 creates a unique druggable pocket exploited by covalent inhibitors. Historically "undruggable" until sotorasib approval in 2021.

*Source: CIViC, PMID:34096690*

---

## 2. Treatment Recommendations

### First Choice (post-chemotherapy)

**1. Sotorasib (Lumakras)** ★★★
- **Approval**: FDA-approved (2021) for KRAS G12C NSCLC after prior therapy
- **Dosing**: 960 mg PO daily
- **Evidence**: CodeBreaK 100 - ORR 37%, mPFS 6.8 mo, mOS 12.5 mo
- **Source**: PMID:34096690

**2. Adagrasib (Krazati)** ★★★
- **Approval**: FDA-approved (2022) for KRAS G12C NSCLC after prior therapy
- **Dosing**: 600 mg PO BID
- **Evidence**: KRYSTAL-1 - ORR 43%, mPFS 6.5 mo
- **Advantage**: Better CNS penetration
- **Source**: PMID:36546659

### Combinations in Development

**Sotorasib + anti-EGFR** ★★☆
- Rationale: EGFR blockade may overcome adaptive resistance
- Evidence: Phase 1b data promising
- Status: Clinical trials ongoing

---

## 3. Resistance Analysis

### Anticipated Resistance Mechanisms

| Mechanism | Frequency | Strategy |
|-----------|-----------|----------|
| KRAS secondary mutations | ~20% | Novel KRAS inhibitors |
| KRAS amplification | ~10% | Dose escalation studies |
| RTK bypass (EGFR, MET) | ~25% | Combination strategies |
| PI3K/mTOR activation | ~15% | PI3K inhibitor combinations |

*Note: Resistance to G12C inhibitors is an active research area*

---

## 4. Clinical Trial Options

| NCT ID | Phase | Agent | Mechanism | Status |
|--------|-------|-------|-----------|--------|
| NCT04185883 | 3 | Sotorasib + pembrolizumab | G12C + PD-1 | Recruiting |
| NCT05198934 | 2 | Adagrasib + pembrolizumab | G12C + PD-1 | Recruiting |
| NCT04330664 | 1/2 | JDQ443 | Next-gen G12C | Recruiting |

---

## 5. Next Steps

1. **Initiate sotorasib or adagrasib** based on formulary/access
2. **If CNS disease present**: Prefer adagrasib (better CNS penetration)
3. **Baseline LFTs** - hepatotoxicity is a class effect
4. **Clinical trial consideration** for combination approaches
```

---

## Example 4: No Actionable Mutations

### User Query
"Stage IV lung adenocarcinoma, NGS panel shows no actionable mutations, PD-L1 <1%. What now?"

### Expected Output

```markdown
# Precision Oncology Report

## Executive Summary

No FDA-approved targeted therapy applies. Low PD-L1 limits single-agent immunotherapy benefit. **Recommended: Platinum-based chemotherapy ± immunotherapy** per standard guidelines.

## 1. Molecular Profile Analysis

| Finding | Clinical Implication |
|---------|---------------------|
| EGFR wild-type | Not eligible for EGFR TKIs |
| ALK negative | Not eligible for ALK inhibitors |
| ROS1 negative | Not eligible for ROS1 inhibitors |
| KRAS wild-type | Not eligible for G12C inhibitors |
| PD-L1 <1% | Limited benefit from single-agent IO |

## 2. Treatment Recommendations

**1. Carboplatin + pemetrexed + pembrolizumab** ★★★
- KEYNOTE-189: Benefit across PD-L1 subgroups
- mPFS 8.8 mo, mOS 22.0 mo

**2. Carboplatin + paclitaxel + bevacizumab + atezolizumab** ★★★
- IMpower150: Alternative chemo-IO regimen

## 3. Recommend Additional Testing

Consider:
- **RNA-based fusion panel** (may detect fusions missed by DNA-only)
- **ctDNA if tissue insufficient**
- **HER2 mutations** (emerging target)
- **NTRK fusions** (pan-tumor approval)
- **MET exon 14 skipping** (FDA-approved options)
```
