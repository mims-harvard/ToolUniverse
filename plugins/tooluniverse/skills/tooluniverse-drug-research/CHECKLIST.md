# Drug Research Report Checklist

Complete verification checklist before delivering any drug research report.

---

## Pre-Research Setup

### Report File Created
- [ ] File named `[DRUG]_drug_report.md`
- [ ] All 11 section headers present
- [ ] `[Researching...]` placeholders in each section
- [ ] Header includes: Generated date, Query, Status

### Compound Disambiguated
- [ ] PubChem CID established
- [ ] ChEMBL ID cross-referenced (or confirmed N/A)
- [ ] Canonical SMILES captured
- [ ] Naming ambiguity resolved (salt forms, isomers)
- [ ] All relevant identifiers documented

---

## Section-by-Section Verification

### Executive Summary
- [ ] 2-3 paragraphs synthesizing key findings
- [ ] Covers: What is it? What's it used for? Key characteristics?
- [ ] **Bottom Line**: One actionable sentence
- [ ] Written LAST (after all data collected)

### Section 1: Compound Identity
| Requirement | Status |
|-------------|--------|
| PubChem CID with link | [ ] |
| ChEMBL ID with link | [ ] |
| RxNorm CUI (if approved) | [ ] |
| PharmGKB ID (if exists) | [ ] |
| DailyMed Set ID (if approved) | [ ] |
| Canonical SMILES | [ ] |
| InChI Key | [ ] |
| Molecular formula | [ ] |
| Molecular weight | [ ] |
| IUPAC name | [ ] |
| Brand names (≥3 or "Generic only") | [ ] |
| Salt forms identified | [ ] |
| Data source citations | [ ] |

### Section 2: Chemical Properties
| Requirement | Status |
|-------------|--------|
| MW, LogP, TPSA in table | [ ] |
| H-bond donors/acceptors | [ ] |
| Rotatable bonds | [ ] |
| Lipinski assessment (violations) | [ ] |
| QED score with interpretation | [ ] |
| Solubility prediction | [ ] |
| Drug-likeness verdict | [ ] |
| Data source citations | [ ] |

### Section 3: Mechanism & Targets
| Requirement | Status |
|-------------|--------|
| Primary mechanism (2-3 sentences) | [ ] |
| Primary target(s) with UniProt | [ ] |
| Activity type (inhibitor/activator/etc.) | [ ] |
| Potency (IC50/EC50/Ki) | [ ] |
| Off-target activity addressed | [ ] |
| ChEMBL bioactivity summary | [ ] |
| Evidence grade on mechanism | [ ] |
| Data source citations | [ ] |

### Section 4: ADMET Properties
| Requirement | Status |
|-------------|--------|
| **4.1 Absorption** | |
| - Oral bioavailability prediction | [ ] |
| - Caco-2 OR PAMPA | [ ] |
| - P-gp substrate status | [ ] |
| **4.2 Distribution** | |
| - BBB penetrance prediction | [ ] |
| - VDss OR PPB | [ ] |
| **4.3 Metabolism** | |
| - CYP1A2 status | [ ] |
| - CYP2C9 status | [ ] |
| - CYP2C19 status | [ ] |
| - CYP2D6 status | [ ] |
| - CYP3A4 status | [ ] |
| **4.4 Excretion** | |
| - Clearance OR half-life | [ ] |
| **4.5 Toxicity** | |
| - AMES mutagenicity | [ ] |
| - hERG inhibition | [ ] |
| - Hepatotoxicity (DILI) | [ ] |
| - At least 1 other endpoint | [ ] |
| All predictions have risk interpretation | [ ] |
| Data source citations | [ ] |

### Section 5: Clinical Development
| Requirement | Status |
|-------------|--------|
| Development status (Approved/Investigational/etc.) | [ ] |
| Total trial count | [ ] |
| Trials by phase (table) | [ ] |
| Trials by status (completed/recruiting/etc.) | [ ] |
| Approved indications with year | [ ] |
| Investigational indications | [ ] |
| Key efficacy data with NCT references | [ ] |
| Evidence grades on efficacy claims | [ ] |
| Data source citations | [ ] |

### Section 6: Safety Profile
| Requirement | Status |
|-------------|--------|
| **6.1 Clinical AEs** | |
| - AEs from trial data (if available) | [ ] |
| **6.2 FAERS** | |
| - Total report count | [ ] |
| - Top 5 adverse reactions (table) | [ ] |
| - Serious vs non-serious ratio | [ ] |
| - Outcome distribution (fatal, recovered, etc.) | [ ] |
| OR "Insufficient FAERS data" noted | [ ] |
| **6.3 Black Box Warnings** | |
| - Listed with text OR "None" | [ ] |
| **6.4 Contraindications** | |
| - At least 3 listed OR "See labeling" | [ ] |
| **6.5 Drug Interactions** | |
| - At least 3 major interactions OR "None significant" | [ ] |
| Signal assessment narrative | [ ] |
| Data source citations | [ ] |

### Section 7: Pharmacogenomics
| Requirement | Status |
|-------------|--------|
| Pharmacogenes listed (table) OR "None identified" | [ ] |
| Gene roles explained (transporter, metabolizer, etc.) | [ ] |
| PharmGKB evidence levels | [ ] |
| CPIC guideline status | [ ] |
| DPWG guideline status | [ ] |
| Clinical annotations with variants | [ ] |
| Actionable recommendations (if any) | [ ] |
| Data source citations | [ ] |

### Section 8: Regulatory & Labeling
| Requirement | Status |
|-------------|--------|
| FDA approval status and year | [ ] |
| EMA approval status (if applicable) | [ ] |
| Other major markets (if applicable) | [ ] |
| Key label sections summarized | [ ] |
| Patent/exclusivity info OR "Not assessed" | [ ] |
| OR "Not approved - investigational" clearly stated | [ ] |
| Data source citations | [ ] |

### Section 9: Literature & Research
| Requirement | Status |
|-------------|--------|
| Total publication count | [ ] |
| 5-year and 1-year counts | [ ] |
| Research trend (increasing/stable/declining) | [ ] |
| Key research themes identified | [ ] |
| 3-5 notable recent publications with PMIDs | [ ] |
| Drug-related publication count | [ ] |
| Data source citations | [ ] |

### Section 10: Conclusions & Assessment
| Requirement | Status |
|-------------|--------|
| **10.1 Scorecard** | |
| - 5 criteria scored 1-5 | [ ] |
| - Rationale for each score | [ ] |
| - Overall score | [ ] |
| **10.2 Key Strengths** | |
| - At least 3 listed | [ ] |
| **10.3 Key Concerns** | |
| - At least 3 listed | [ ] |
| **10.4 Research Gaps** | |
| - At least 2 identified | [ ] |
| Confidence assessment (High/Medium/Low) | [ ] |

### Section 11: Data Sources & Methodology
| Requirement | Status |
|-------------|--------|
| All databases queried listed | [ ] |
| All tool names documented | [ ] |
| Query date | [ ] |
| Known limitations noted | [ ] |
| Failed queries documented | [ ] |

---

## Quality Checks

### Evidence Grading Applied
- [ ] Clinical trial evidence marked ★★★
- [ ] Limited clinical evidence marked ★★☆
- [ ] Preclinical evidence marked ★☆☆
- [ ] Computational/indirect evidence marked ☆☆☆
- [ ] No ungraded claims in mechanism/efficacy sections

### Citation Coverage
- [ ] Every table has source citation below
- [ ] Every factual claim has inline or block citation
- [ ] All tool names mentioned with parameters used
- [ ] Database IDs included (CID, ChEMBL ID, NCT, PMID)

### Data Completeness Tier
- [ ] ●●● Complete: All 11 sections with substantial data
- [ ] ●●○ Substantial: 8-10 sections substantial, others noted sparse
- [ ] ●○○ Basic: Identity + chemistry + partial pharmacology
- [ ] ○○○ Minimal: Identity only (flag to user)

### Formatting
- [ ] All tables render correctly
- [ ] No `[Researching...]` placeholders remaining
- [ ] Links work (PubChem, ChEMBL, ClinicalTrials.gov)
- [ ] Consistent formatting throughout
- [ ] Section numbers match template

---

## Pre-Delivery Final Check

- [ ] Executive summary reflects complete report
- [ ] Bottom line is actionable and specific
- [ ] No search process text visible in report
- [ ] No raw tool outputs in report
- [ ] All 11 sections present
- [ ] Data sources section complete
- [ ] Report file saved
- [ ] Optional: `[drug]_data.json` created with structured data

---

## Quick Fixes for Common Issues

| Issue | Fix |
|-------|-----|
| Missing ChEMBL ID | State "Not found in ChEMBL" in identity section |
| No FAERS data | Add "Insufficient adverse event reports in FAERS (<100 reports)" |
| No clinical trials | State "No registered trials on ClinicalTrials.gov as of [date]" |
| ADMET failed | Note "ADMET predictions unavailable - [reason]" |
| No PGx data | State "No pharmacogenomic associations documented in PharmGKB" |
| No CPIC guideline | State "No CPIC guideline available for this drug" |
| Compound not found | Return to user for clarification before proceeding |
| API timeout | Document failed query, use fallback, note limitation |
