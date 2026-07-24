# Clinical Trial Matching - Examples

## Example 1: NSCLC with EGFR L858R

**User Query**: "Find clinical trials for Stage IV non-small cell lung cancer with EGFR L858R mutation, failed platinum chemotherapy, ECOG 0-1"

**Skill Execution**:

### Phase 1: Patient Profile Standardization
- Disease: "non-small cell lung cancer" -> EFO_0003060 (non-small cell lung carcinoma)
- Gene: EGFR -> Ensembl: ENSG00000146648, Entrez: 1956
- Biomarker: EGFR L858R -> type: mutation, gene: EGFR, alteration: L858R
- FDA Biomarker: EGFR is FDA-recognized biomarker (afatinib, osimertinib, erlotinib, gefitinib)

### Phase 2: Trial Discovery
- Disease search: ~200+ trials for NSCLC
- Biomarker search: "EGFR L858R" -> 10-30 targeted trials
- Intervention search: "osimertinib" for NSCLC -> 20+ trials
- Combined and deduplicated: ~50-80 unique candidate trials

### Phase 3-6: Analysis
- Parse eligibility criteria for EGFR L858R requirements
- Check drug mechanisms for EGFR inhibitors
- Cross-reference FDA approvals (osimertinib for EGFR L858R NSCLC)
- Score molecular match: 40/40 for trials requiring EGFR L858R

### Expected Top Matches
Trials testing:
- EGFR TKIs (osimertinib, amivantamab-vmjw)
- EGFR TKI combinations (TKI + chemotherapy)
- Next-generation EGFR inhibitors
- EGFR-targeted ADCs or bispecific antibodies

---

## Example 2: Melanoma with BRAF V600E

**User Query**: "Patient has BRAF V600E melanoma, failed ipilimumab, looking for trials"

**Skill Execution**:

### Phase 1: Standardization
- Disease: melanoma -> EFO_0000756
- Gene: BRAF -> ENSG00000157764, CIViC ID: 5
- Biomarker: BRAF V600E -> type: mutation
- FDA: BRAF is FDA-recognized (dabrafenib, vemurafenib, encorafenib)

### Phase 2: Trial Discovery
- "melanoma BRAF V600E" -> BRAF-targeted trials
- "melanoma immunotherapy" -> post-ipilimumab options
- Combined targeted + immunotherapy options

### Expected Top Matches
- BRAF/MEK inhibitor combinations (dabrafenib + trametinib)
- Novel BRAF inhibitors
- Combination of BRAF inhibition + immunotherapy
- Anti-PD-1 after ipilimumab
- Novel immunotherapy combinations

---

## Example 3: Colorectal Cancer with KRAS G12C

**User Query**: "KRAS G12C colorectal cancer, Stage IV, failed FOLFOX + bevacizumab, microsatellite stable"

**Skill Execution**:

### Phase 1: Standardization
- Disease: colorectal cancer -> EFO_0005842
- Gene: KRAS -> ENSG00000133703, CIViC ID: 30
- Biomarkers: KRAS G12C (mutation), MSS (status)
- FDA: KRAS G12C targeted (sotorasib approved for NSCLC, under investigation for CRC)

### Phase 2: Trial Discovery
- "colorectal cancer KRAS G12C" -> specific trials
- "KRAS G12C" without disease filter -> cross-tumor trials
- "sotorasib" or "adagrasib" for CRC

### Expected Top Matches
- KRAS G12C inhibitor trials (sotorasib, adagrasib) for CRC
- KRAS G12C + anti-EGFR combinations
- Novel KRAS inhibitors
- Basket trials for KRAS G12C any solid tumor

---

## Example 4: Breast Cancer with HER2+

**User Query**: "HER2-positive breast cancer, failed trastuzumab + pertuzumab, brain metastases"

**Skill Execution**:

### Phase 1: Standardization
- Disease: breast cancer -> EFO_0000305
- Gene: HER2/ERBB2 -> ENSG00000141736, CIViC ID: 20
- Biomarker: HER2 amplification
- FDA: HER2 recognized (trastuzumab, pertuzumab, T-DXd, tucatinib)

### Phase 2: Trial Discovery
- "breast cancer HER2" + "brain metastases"
- "trastuzumab deruxtecan" (T-DXd) trials
- "tucatinib" trials (CNS-penetrant)
- Post-pertuzumab HER2+ trials

### Special Considerations
- Brain metastases eligibility (many trials exclude CNS disease)
- CNS-active agents prioritized (tucatinib, T-DXd)

---

## Example 5: NTRK Fusion (Basket Trial)

**User Query**: "Find trials for NTRK1 fusion, any solid tumor type"

**Skill Execution**:

### Phase 1: Standardization
- Gene: NTRK1 -> ENSG00000198400, CIViC ID: 197
- Biomarker: NTRK1 fusion
- FDA: NTRK recognized (larotrectinib, entrectinib - tissue-agnostic)

### Phase 2: Trial Discovery
- "NTRK fusion" + "basket" or "tumor agnostic"
- "larotrectinib" and "entrectinib" trials
- "NTRK" across all cancer types

### Expected Top Matches
- Larotrectinib/entrectinib expansion studies
- Next-generation TRK inhibitors (selitrectinib, repotrectinib)
- Basket trials requiring NTRK fusion
- Combination approaches with TRK inhibition

---

## Example 6: Geographic Search

**User Query**: "Find Phase II or III lung cancer trials near Boston"

**Skill Execution**:

### Phase 1: Standardization
- Disease: lung cancer -> EFO_0001071
- Geographic preference: Boston, Massachusetts

### Phase 2: Trial Discovery
- "lung cancer" Phase II/III
- Filter by Massachusetts locations

### Phase 3: Location Analysis
- Sites in Massachusetts: Dana-Farber, Massachusetts General, Beth Israel
- Nearby states: Connecticut, Rhode Island, New Hampshire

### Scoring
- Geographic feasibility weighted more heavily
- Massachusetts sites: 5/5 points
- Nearby New England sites: 3/5 points

---

## Output Format

Each example produces a comprehensive markdown report saved to a file with the following key sections:

1. **Executive Summary** with top 3 trials and scores
2. **Patient Profile** with standardized identifiers
3. **Ranked Trial List** with scoring breakdown
4. **Trial Categories** (targeted, immunotherapy, combination, basket)
5. **Alternative Options** (expanded access, off-label)
6. **Evidence Grading** and completeness checklist
