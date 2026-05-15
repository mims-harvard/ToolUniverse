# Clinical Variant Interpreter - Examples

## Example 1: Pathogenic BRCA1 Variant

### User Query
"Interpret the clinical significance of BRCA1 c.5266dupC"

### Expected Output

```markdown
# Variant Interpretation Report: BRCA1 c.5266dupC

**Generated**: 2026-02-04 | **Analyst**: ToolUniverse Variant Interpreter

---

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_007294.4:c.5266dupC (p.Gln1756ProfsTer74) |
| **Gene** | BRCA1 |
| **Classification** | **PATHOGENIC** ★★★ |
| **Evidence Strength** | Very Strong (multiple independent lines) |
| **Key Finding** | Frameshift variant in established LOF gene; well-documented pathogenic variant |

**Clinical Action Required**: Hereditary breast/ovarian cancer risk management indicated.

---

## 1. Variant Identity

| Property | Value |
|----------|-------|
| Gene | BRCA1 |
| Chromosome | 17 |
| Position | 17:43057051 (GRCh38) |
| Transcript | NM_007294.4 (MANE Select) |
| cDNA change | c.5266dupC |
| Protein change | p.Gln1756ProfsTer74 |
| Consequence | Frameshift |
| Exon | 20 of 23 |

**Note**: Also known as 5382insC (legacy notation)

*Source: `EnsemblVar_get_variant_consequences`, `MyVariant_query_variants`*

---

## 2. Population Data

### gnomAD v4.0 Frequencies

| Population | Allele Frequency | Allele Count |
|------------|------------------|--------------|
| **Overall** | 0.00006 | 45 |
| European (Non-Finnish) | 0.00012 | 38 |
| Ashkenazi Jewish | 0.011 | 89 |
| African/African American | 0.00001 | 2 |
| Latino/Admixed American | 0.00002 | 3 |
| East Asian | 0 | 0 |
| South Asian | 0 | 0 |

**Homozygotes**: 0
**Hemizygotes**: N/A (autosomal gene)

**Interpretation**: Elevated in Ashkenazi Jewish population (founder variant). Overall frequency consistent with disease prevalence when accounting for reduced penetrance and carrier frequency.

*Source: `gnomad_search_variants`, accessed 2026-02-04*

---

## 3. Clinical Database Evidence

### ClinVar

| Property | Value |
|----------|-------|
| VCV ID | VCV000017661 |
| Classification | Pathogenic |
| Review Status | ★★★★ (Expert panel reviewed) |
| Submitters | 47 |
| Last Evaluated | 2024-12-15 |
| Conditions | Hereditary breast/ovarian cancer syndrome |

**Expert Panel**: ENIGMA consortium - criteria met for Pathogenic

### OMIM

| Gene-Disease | Inheritance | MIM# |
|--------------|-------------|------|
| Breast-ovarian cancer, familial 1 | AD | 604370 |
| Fanconi anemia, complementation group S | AR | 617883 |

### ClinGen

| Assessment | Status |
|------------|--------|
| Gene-Disease Validity | DEFINITIVE for HBOC |
| Dosage Sensitivity | Haploinsufficient |
| LOF Mechanism | Established |

*Sources: ClinVar VCV000017661, OMIM #113705, ClinGen*

---

## 4. Computational Predictions

**Note**: Computational predictors not applicable to frameshift variants (by definition, these are loss-of-function).

| Predictor | Score | Not Applicable Reason |
|-----------|-------|----------------------|
| SIFT | N/A | Frameshift |
| PolyPhen-2 | N/A | Frameshift |
| CADD | 35 (Phred) | High deleteriousness |

**NMD Prediction**: Predicted to undergo nonsense-mediated decay (PTC at codon 1829, well before last exon junction)

*Source: `MyVariant_query_variants`*

---

## 5. Structural Analysis

**Structural impact assessment not required** for truncating variants where LOF is established mechanism.

**Protein Context**:
- Truncation at codon 1756 (of 1863)
- Removes C-terminal BRCT domains
- BRCT domains essential for DNA repair function
- Even if translated, protein would be non-functional

*Source: UniProt P38398, InterPro domain annotations*

---

## 6. Literature Evidence

### Functional Studies

| Study | Finding | PMID |
|-------|---------|------|
| Carvalho et al., 2007 | LOF in HDR assay | 17308087 |
| Moghadasi et al., 2018 | Absent protein | 29446198 |
| Multiple studies | Segregates with cancer | Multiple |

### Clinical Reports

- Founder variant in Ashkenazi Jewish population
- Extensive clinical documentation (>500 families)
- Co-segregation in >100 affected individuals

**PS3 Evidence**: Strong - multiple functional studies demonstrating loss of DNA repair function

*Source: `PubMed_search_articles`*

---

## 7. ACMG Classification

### Evidence Codes Applied

| Code | Strength | Rationale |
|------|----------|-----------|
| **PVS1** | Very Strong | Null variant (frameshift) in gene where LOF is established mechanism |
| **PS4** | Strong | >5 affected individuals documented |
| **PM2** | Supporting | Absent/extremely rare in general population (outside founders) |
| **PP5** | Supporting | Expert panel (ENIGMA) reports pathogenic |

### Evidence Summary

| Pathogenic | Benign |
|------------|--------|
| 1 Very Strong (PVS1) | None |
| 1 Strong (PS4) | |
| 2 Supporting (PM2, PP5) | |

### Classification: **PATHOGENIC**

**Rationale**: Meets ACMG criteria for Pathogenic (1 Very Strong + 1 Strong + 2 Supporting). Well-established pathogenic variant with multiple lines of independent evidence.

**Confidence**: ★★★ (High) - Expert panel reviewed, extensive clinical data

---

## 8. Clinical Recommendations

### For Affected Individual

| Category | Recommendation |
|----------|----------------|
| **Confirmation** | No re-testing needed; well-documented variant |
| **Cancer screening** | NCCN high-risk breast/ovarian protocols |
| **Risk-reducing options** | Discuss prophylactic mastectomy, salpingo-oophorectomy |
| **Medical management** | Consider PARP inhibitor eligibility if cancer |
| **Genetic counseling** | Discuss implications, reproductive options |

### For Family Members

| Relationship | Action |
|--------------|--------|
| First-degree relatives | Offer cascade testing |
| At-risk children | Consider testing at 18-25 years |
| Partners | Reproductive counseling if planning children |

### Testing Recommendations

- Cascade genetic testing for first-degree relatives
- Consider panel testing for other cancer genes if clinically indicated
- Tumor testing for PARP inhibitor eligibility if cancer present

---

## 9. Limitations & Uncertainties

| Factor | Status |
|--------|--------|
| Classification certainty | High - well-documented |
| Penetrance | Incomplete (~70% breast, ~40% ovarian by age 70) |
| Modifier genes | May influence risk |
| Environmental factors | May modify risk |

**No significant limitations** - This is a well-characterized pathogenic variant with extensive clinical documentation.

---

## Data Sources

| Tool | Purpose | Result |
|------|---------|--------|
| `clinvar_search_variants` | Classification lookup | VCV000017661 |
| `gnomad_search_variants` | Population frequency | AF=0.00006 |
| `MyVariant_query_variants` | Aggregated annotations | Complete |
| `PubMed_search_articles` | Literature evidence | 47 relevant papers |
| `OMIM_search` | Gene-disease | HBOC confirmed |
```

---

## Example 2: VUS Missense Requiring Structural Analysis

### User Query
"Interpret TP53 p.R175C - it's reported as a VUS"

### Expected Output

```markdown
# Variant Interpretation Report: TP53 p.R175C

**Generated**: 2026-02-04 | **Analyst**: ToolUniverse Variant Interpreter

---

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_000546.6:c.523C>T (p.Arg175Cys) |
| **Gene** | TP53 |
| **Classification** | **LIKELY PATHOGENIC** ★★☆ |
| **Evidence Strength** | Moderate (structural + computational + clinical) |
| **Key Finding** | Hotspot residue in DNA-binding domain; R175 is known pathogenic position (R175H documented) |

**Reclassified from VUS based on structural analysis and PM5 evidence.**

---

## 1. Variant Identity

| Property | Value |
|----------|-------|
| Gene | TP53 |
| Chromosome | 17 |
| Position | 17:7674220 (GRCh38) |
| Transcript | NM_000546.6 (MANE Select) |
| cDNA change | c.523C>T |
| Protein change | p.Arg175Cys |
| Consequence | Missense |
| Exon | 5 of 11 |

*Source: `EnsemblVar_get_variant_consequences`, `MyVariant_query_variants`*

---

## 2. Population Data

### gnomAD v4.0 Frequencies

| Population | Allele Frequency | Allele Count |
|------------|------------------|--------------|
| **Overall** | 0 | 0 |
| European (Non-Finnish) | 0 | 0 |
| African/African American | 0 | 0 |
| Latino/Admixed American | 0 | 0 |
| East Asian | 0 | 0 |
| South Asian | 0 | 0 |

**Homozygotes**: 0

**Interpretation**: Absent from gnomAD (>140,000 individuals). Supports PM2 (absent from controls).

*Source: `gnomad_search_variants`, accessed 2026-02-04*

---

## 3. Clinical Database Evidence

### ClinVar

| Property | Value |
|----------|-------|
| VCV ID | VCV000376642 |
| Classification | VUS (outdated) |
| Review Status | ★★ (criteria provided) |
| Submitters | 3 |
| Conditions | Li-Fraumeni syndrome |

**Note**: ClinVar classification may require update based on structural evidence.

### Critical Context: R175 Position

| Variant at R175 | ClinVar Classification |
|-----------------|------------------------|
| p.R175H | Pathogenic (★★★★) |
| p.R175G | Pathogenic |
| p.R175L | Pathogenic |
| p.R175S | Pathogenic |
| **p.R175C** | VUS (being reclassified) |

**PM5 Applies**: Multiple different missense changes at R175 are pathogenic.

### OMIM

| Gene-Disease | Inheritance |
|--------------|-------------|
| Li-Fraumeni syndrome | AD |
| Various cancers | Somatic |

*Sources: ClinVar, OMIM #191170*

---

## 4. Computational Predictions

| Predictor | Score | Interpretation |
|-----------|-------|----------------|
| SIFT | 0.00 | Damaging |
| PolyPhen-2 | 1.00 | Probably damaging |
| CADD | 29.5 (Phred) | Top 0.1% deleterious |
| REVEL | 0.92 | Pathogenic range |

**Concordance**: 4/4 predictors indicate damaging → **PP3 applies**

*Source: `MyVariant_query_variants`*

---

## 5. Structural Analysis

### Structure Information

| Property | Value |
|----------|-------|
| Structure used | PDB: 2OCJ (1.8 Å) |
| Domain | DNA-binding domain (DBD) |
| Position pLDDT | N/A (experimental structure) |
| Resolution | 1.8 Å |

### R175 Structural Context

| Feature | Assessment |
|---------|------------|
| **Location** | DNA-binding domain core |
| **Solvent accessibility** | Buried (RSA = 5%) |
| **Secondary structure** | Loop L2 (critical for zinc coordination) |
| **Zinc coordination** | 4.2 Å from Zn²⁺ binding site |
| **Conservation** | 100% in vertebrates |

### Structural Impact Analysis

| Factor | Wildtype (Arg) | Mutant (Cys) | Impact |
|--------|----------------|--------------|--------|
| Charge | +1 (basic) | 0 (neutral) | Charge loss in buried position |
| Side chain volume | Large | Small | Potential cavity |
| H-bonding | 5 H-bonds | 1 H-bond | Loss of stabilizing interactions |
| Zinc coordination | Proximal | Potential interference | May affect zinc binding |

### Structural Conclusion

**PM1 applies (moderate)**: 
- R175 is in a critical structural region
- Known mutational hotspot
- Zinc coordination region essential for DNA binding
- Structural analysis supports pathogenicity

*Sources: PDB 2OCJ, structural analysis*

---

## 6. Literature Evidence

### Functional Studies (at R175 position)

| Study | Variant | Finding | PMID |
|-------|---------|---------|------|
| Kato et al., 2003 | R175H | Loss of transactivation | 12826609 |
| Bullock et al., 2000 | R175H | Destabilized, unfolded | 10788335 |
| Joerger et al., 2006 | R175 mutations | Disrupt zinc binding | 16630891 |

### R175C-Specific Evidence

- Limited direct functional data for R175C specifically
- Same position as extensively characterized R175H
- Mechanism (zinc coordination disruption) likely conserved

**PS3**: Not directly applicable (no R175C-specific functional study)
**PS1**: Not applicable (amino acid change differs from R175H)

*Source: `PubMed_search_articles`*

---

## 7. ACMG Classification

### Evidence Codes Applied

| Code | Strength | Rationale |
|------|----------|-----------|
| **PM2** | Moderate | Absent from gnomAD (>140,000 individuals) |
| **PM5** | Moderate | Different missense at same position (R175H) is pathogenic |
| **PM1** | Moderate | Critical DNA-binding domain, zinc coordination region |
| **PP3** | Supporting | All 4 predictors concordantly damaging |

### Evidence Summary

| Pathogenic | Benign |
|------------|--------|
| 0 Very Strong | None |
| 0 Strong | |
| 3 Moderate (PM2, PM5, PM1) | |
| 1 Supporting (PP3) | |

### Classification: **LIKELY PATHOGENIC**

**Rationale**: 3 Moderate + 1 Supporting meets ACMG criteria for Likely Pathogenic. Strong structural evidence at known hotspot position supports classification upgrade from VUS.

**Confidence**: ★★☆ (Moderate) - Structural evidence strong, but lacks direct R175C functional data

---

## 8. Clinical Recommendations

### For Affected Individual

| Category | Recommendation |
|----------|----------------|
| **Confirmation** | Consider orthogonal confirmation |
| **Clinical management** | Li-Fraumeni screening protocol |
| **Cancer surveillance** | Comprehensive multi-organ screening |
| **Genetic counseling** | Discuss uncertainty, manage expectations |

### Family Testing Considerations

- Likely Pathogenic classification supports cascade testing
- Counsel families about classification confidence level
- Consider research enrollment for functional studies

### Recommended Surveillance (Li-Fraumeni Protocol)

| Modality | Frequency | Starting Age |
|----------|-----------|--------------|
| Breast MRI | Annual | 20-25 |
| Colonoscopy | Every 2-5 years | 25 |
| Skin exam | Annual | 18 |
| Whole-body MRI | Consider annual | 25 |

---

## 9. Limitations & Uncertainties

| Factor | Impact |
|--------|--------|
| **No direct functional data** | Classification relies on position analogy |
| **ClinVar discordance** | Our Likely Pathogenic vs ClinVar VUS |
| **Phenocopy risk** | Environmental factors could explain cancer |

**Recommendation**: Consider this classification provisional pending functional studies. Reanalyze when new data available.

---

## Data Sources

| Tool | Purpose | Result |
|------|---------|--------|
| `clinvar_search_variants` | Classification | VCV000376642 (VUS) |
| `gnomad_search_variants` | Population freq | 0 (absent) |
| `MyVariant_query_variants` | Predictions | All damaging |
| `RCSBData_get_entry` | Structure | 2OCJ |
| `PubMed_search_articles` | Literature | R175 studies |
```

---

## Example 3: Likely Benign Common Variant

### User Query  
"What is the significance of the CFTR p.M470V variant?"

### Expected Output (Key Sections)

```markdown
# Variant Interpretation Report: CFTR p.M470V

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_000492.4:c.1408A>G (p.Met470Val) |
| **Gene** | CFTR |
| **Classification** | **BENIGN** ★★★ |
| **Evidence Strength** | Very Strong (population frequency) |
| **Key Finding** | Common variant (14% global AF); well-established benign polymorphism |

---

## 2. Population Data

### gnomAD v4.0 Frequencies

| Population | Allele Frequency |
|------------|------------------|
| **Overall** | 0.14 (14%) |
| European | 0.22 |
| East Asian | 0.03 |
| African | 0.08 |

**Interpretation**: Far too common to cause rare disease like CF (prevalence 1/3,000). **BA1 applies**.

---

## 7. ACMG Classification

### Evidence Codes Applied

| Code | Strength | Rationale |
|------|----------|-----------|
| **BA1** | Stand-Alone | AF >5% in gnomAD |
| **BS1** | Strong | AF far exceeds disease frequency |
| **BP4** | Supporting | Benign computational predictions |

### Classification: **BENIGN**

**Rationale**: BA1 alone is sufficient for Benign classification. This is a well-established benign polymorphism.

---

## 8. Clinical Recommendations

### For Individual
- This variant is **NOT** disease-causing
- Do not use for CF carrier screening interpretation
- No clinical follow-up needed based on this variant

### Important Notes
- May be found in compound heterozygosity with pathogenic variants
- Presence does NOT modify carrier status determined by other variants
```

---

## Example 4: Novel Variant with Limited Data

### User Query
"Interpret SCN5A c.4813+3A>G - novel splice variant"

### Expected Output (Key Sections)

```markdown
# Variant Interpretation Report: SCN5A c.4813+3A>G

## Executive Summary

| Field | Value |
|-------|-------|
| **Variant** | NM_000335.5:c.4813+3A>G |
| **Gene** | SCN5A |
| **Classification** | **VUS - FAVOR PATHOGENIC** ★☆☆ |
| **Evidence Strength** | Limited (splice prediction only) |
| **Key Finding** | Near-splice variant in cardiac arrhythmia gene; SpliceAI predicts donor loss |

**Action**: Functional RNA studies recommended before clinical use.

---

## 4. Computational Predictions

### Splice Predictions

| Tool | Score | Prediction |
|------|-------|------------|
| SpliceAI donor loss | 0.89 | High impact predicted |
| MaxEntScan (WT) | 8.2 | Strong donor site |
| MaxEntScan (Mut) | 4.1 | Weakened |

**Interpretation**: +3 position variants can affect splicing. SpliceAI score of 0.89 suggests high likelihood of splice disruption.

---

## 7. ACMG Classification

### Evidence Codes Applied

| Code | Strength | Rationale |
|------|----------|-----------|
| **PM2** | Supporting | Absent from gnomAD |
| **PP3** | Supporting | SpliceAI predicts splice disruption |
| **PM4** | Supporting | If causes in-frame deletion, alters protein |

### Classification: **VUS (Favor Pathogenic)**

**Rationale**: Insufficient evidence for Likely Pathogenic (would need 1 Strong + 1 Moderate or 3 Moderate). Splice prediction is suggestive but not confirmed.

---

## 8. Clinical Recommendations

### Recommended Studies
1. **RNA studies** - RT-PCR from patient sample to confirm aberrant splicing
2. **Family segregation** - Test affected relatives
3. **Functional studies** - Minigene assay if RNA unavailable

### Clinical Management
- Classification is VUS: Do NOT use for clinical decisions
- Continue phenotype-based cardiac management
- Offer participation in research studies

### Reclassification Potential
- RNA showing exon skipping → Upgrade to Likely Pathogenic (PVS1)
- Segregation in 2+ affected → Add PP1
```
