# Rare Disease Diagnosis Checklist

Pre-delivery verification checklist for rare disease diagnostic reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created: `[PATIENT_ID]_rare_disease_report.md`
- [ ] All 8 main sections present
- [ ] Executive summary completed (not `[Researching...]`)
- [ ] Data sources section populated

### Phase 1: Phenotype Standardization
- [ ] All clinical features converted to HPO terms
- [ ] HPO IDs provided for each term
- [ ] Core features distinguished from variable
- [ ] Age of onset documented
- [ ] Family history recorded (or "Unknown")
- [ ] Inheritance pattern suspected (AD/AR/XL/Unknown)

### Phase 2: Disease Matching
- [ ] ≥5 candidate diseases identified (or all if fewer match)
- [ ] Each disease has ORPHA ID
- [ ] Each disease has OMIM ID (if available)
- [ ] Phenotype match % calculated for each
- [ ] Diseases ranked by match score
- [ ] Inheritance pattern for each disease
- [ ] Causative genes listed for each disease
- [ ] Top 3 diseases have detailed feature comparison

### Phase 3: Gene Panel
- [ ] ≥5 genes in recommended panel (or all from top diseases)
- [ ] Each gene has evidence level (ClinGen: Definitive/Strong/Moderate)
- [ ] Constraint scores (pLI) provided
- [ ] Expression validation for relevant tissue
- [ ] Genes prioritized by tier (★★★/★★☆/★☆☆)
- [ ] Testing strategy recommended (single gene vs panel vs WES)
- [ ] Cost-effectiveness considered

### Phase 4: Variant Interpretation (if variants provided)
- [ ] ClinVar ID and classification retrieved
- [ ] gnomAD allele frequency checked
- [ ] Population-specific frequencies noted
- [ ] CADD/REVEL scores obtained
- [ ] ACMG criteria systematically applied
- [ ] Each criterion has evidence documented
- [ ] Preliminary classification stated
- [ ] Confidence in classification noted

### Phase 5: Structure Analysis (if VUS)
- [ ] NVIDIA_API_KEY availability documented
- [ ] Structure prediction method stated
- [ ] pLDDT confidence at variant position reported
- [ ] Domain location assessed
- [ ] Conservation data included
- [ ] Nearby pathogenic variants noted
- [ ] Structural evidence summarized
- [ ] Impact on ACMG classification stated

### Phase 6: Recommendations
- [ ] ≥3 specific next steps listed
- [ ] Priority order for actions
- [ ] Specialist referrals suggested (genetics, cardiology, etc.)
- [ ] Family screening recommendations
- [ ] Follow-up timeline suggested
- [ ] Genetic counseling mentioned

### Phase 7: Data Gaps
- [ ] All gaps aggregated in one section
- [ ] Reason for each gap documented
- [ ] Alternative approaches suggested

---

## Citation Requirements

### Every Section Must Include
- [ ] Source database name
- [ ] Tool used (in backticks)
- [ ] Specific identifiers (ORPHA, OMIM, HP, etc.)

### Format Examples
```markdown
*Source: Orphanet via `Orphanet_558` (ORPHA:558)*
*Source: OMIM via `OMIM_get_entry` (MIM:154700)*
*Source: HPO via `HPO_search_terms` (HP:0001166)*
*Source: ClinVar via `clinvar_get_variant_details` (VCV000012345)*
*Source: gnomAD via `gnomAD_get_variant_frequencies` (AF: 0.00001)*
*Source: NVIDIA NIM via `NvidiaNIM_alphafold2` (pLDDT: 85.3)*
```

---

## Evidence Grading

### All Diagnoses Must Have
- [ ] Evidence tier assigned (★★★ to ☆☆☆)
- [ ] Phenotype match % documented
- [ ] Genetic evidence level (if variant found)

### Tier Definitions
| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | ★★★ | Phenotype >80% + pathogenic variant OR clinical diagnosis met |
| T2 | ★★☆ | Phenotype 60-80% OR likely pathogenic variant |
| T3 | ★☆☆ | Phenotype 40-60% OR VUS in candidate gene |
| T4 | ☆☆☆ | Phenotype <40% OR no supporting genetic evidence |

---

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| HPO terms | ≥5 standardized terms |
| Candidate diseases | ≥5 ranked diseases (or all matching) |
| Disease details | Top 3 with full feature comparison |
| Gene panel | ≥5 genes with evidence levels |
| ACMG criteria | All applicable criteria evaluated |
| Recommendations | ≥3 specific next steps |

---

## Phenotype-Specific Checks

### Connective Tissue Phenotypes
- [ ] Cardiac features assessed (aortic root, mitral valve)
- [ ] Skeletal features documented (height, proportions)
- [ ] Ocular features checked (lens, myopia)
- [ ] Skin findings noted (striae, elasticity)
- [ ] Ghent criteria referenced (if Marfan suspected)

### Neurological Phenotypes
- [ ] Developmental milestones documented
- [ ] Seizure history (type, onset, frequency)
- [ ] MRI findings (if available)
- [ ] Cognitive assessment
- [ ] Movement disorders noted

### Metabolic Phenotypes
- [ ] Biochemical markers (if available)
- [ ] Dietary history relevant
- [ ] Acute decompensation episodes
- [ ] Treatment response history

---

## Output Files

### Required
- [ ] `[PATIENT_ID]_rare_disease_report.md` - Main report

### Optional (if applicable)
- [ ] `[PATIENT_ID]_gene_panel.csv` - Prioritized genes
- [ ] `[PATIENT_ID]_variant_interpretation.csv` - Variant details

### CSV Column Requirements
**gene_panel.csv**:
```
Gene,Evidence_Level,Constraint_pLI,Associated_Diseases,Priority_Tier
```

**variant_interpretation.csv**:
```
Variant,Gene,ClinVar_Class,gnomAD_AF,ACMG_Criteria,Classification
```

---

## Final Review

### Before Delivery
- [ ] No `[Researching...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] No empty sections (use "Not applicable" if needed)
- [ ] Executive summary synthesizes key findings
- [ ] Most likely diagnosis clearly stated
- [ ] Recommendations are actionable
- [ ] Report is understandable to referring clinician

### Common Issues to Avoid
- [ ] HPO terms without IDs
- [ ] Diseases without ORPHA/OMIM identifiers
- [ ] Variants without population frequency
- [ ] ACMG classification without documented criteria
- [ ] Recommendations without priority order
- [ ] Missing family history implications

---

## Urgent Findings Protocol

If any of these found, flag prominently:
- [ ] Pathogenic variant in actionable gene
- [ ] High suspicion for condition requiring immediate intervention
- [ ] Cardiac abnormality suggesting aortic pathology
- [ ] Metabolic emergency risk
- [ ] Cancer predisposition syndrome
