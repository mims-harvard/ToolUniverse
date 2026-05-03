# Target Intelligence Report Format Specification

This document defines the comprehensive report format for target intelligence reports. **ALL sections are REQUIRED** unless marked optional.

## Critical Requirements

### 1. Report File Creation
- **Create the report file FIRST** before any data collection
- File name: `[TARGET]_target_report.md` (e.g., `EGFR_target_report.md`)
- Initialize all 14 section headers with `[Researching...]` placeholders
- Update sections progressively as data is retrieved

### 2. Citation Requirements (MANDATORY)
**Every piece of data MUST cite its source.** Include:
- The database name (UniProt, PDB, ChEMBL, etc.)
- The tool used (`UniProt_get_entry_by_accession`, etc.)
- The query parameters (accession, gene symbol, etc.)

### 3. Source Block Format
At the end of each major section, add a source block:

```markdown
---
**Sources:**
- [Database]: `tool_name` (query_parameter)
- [Database]: `tool_name` (query_parameter)
---
```

## Report Template

```markdown
# Target Intelligence Report: [FULL PROTEIN NAME]

**Generated**: [Date] | **Query**: [Original query] | **Completeness**: [X/8 paths successful]

---

## 1. Executive Summary

[2-3 sentence overview of the target covering: what it is, its primary function, druggability status, and key clinical relevance]

**Bottom Line**: [One sentence: Is this a good drug target? Why/why not?]

---

## 2. Target Identifiers

| Identifier Type | Value | Database |
|-----------------|-------|----------|
| Gene Symbol | [SYMBOL] | HGNC |
| UniProt Accession | [P#####] | UniProtKB |
| Ensembl Gene ID | [ENSG###] | Ensembl |
| Entrez Gene ID | [#####] | NCBI Gene |
| ChEMBL Target ID | [CHEMBL###] | ChEMBL |
| HGNC ID | [HGNC:####] | HGNC |

**Aliases**: [List all known aliases/synonyms]

---

## 3. Basic Information

### 3.1 Protein Description
- **Recommended Name**: [Full protein name]
- **Alternative Names**: [List]
- **Gene Name**: [Symbol] ([Full gene name])
- **Organism**: [Species] (Taxonomy ID: [####])
- **Protein Length**: [###] amino acids
- **Molecular Weight**: [###] kDa
- **Isoforms**: [Number] known isoforms

### 3.2 Protein Function
[Detailed description of protein function - at least 3-4 sentences covering:
- Primary molecular function
- Biological process involvement
- Cellular role
- Signaling pathway context]

### 3.3 Subcellular Localization
- **Primary Location**: [e.g., Plasma membrane]
- **Additional Locations**: [List]
- **Topology**: [e.g., Single-pass type I membrane protein]

---

## 4. Structural Biology

### 4.1 Experimental Structures (PDB)
| PDB ID | Resolution | Method | Ligand | Description |
|--------|------------|--------|--------|-------------|
| [####] | [#.#Å] | [X-ray/Cryo-EM/NMR] | [Ligand or Apo] | [Brief description] |
[List top 5-10 most relevant structures]

**Total PDB Entries**: [###]
**Best Resolution**: [#.#Å] ([PDB ID])
**Structure Coverage**: [Complete/Partial - which domains?]

### 4.2 AlphaFold Prediction
- **Available**: [Yes/No]
- **Confidence**: [High/Medium/Low - pLDDT scores]
- **Model URL**: [AlphaFold DB link]

### 4.3 Domain Architecture
| Domain | Position | InterPro ID | Description |
|--------|----------|-------------|-------------|
| [Domain name] | [Start-End] | [IPR######] | [Function] |
[List all domains]

### 4.4 Key Structural Features
- **Active Sites**: [List with positions]
- **Binding Sites**: [List - substrate, cofactor, drug binding]
- **PTM Sites**: [Phosphorylation, glycosylation, etc. with positions]
- **Disulfide Bonds**: [List]

### 4.5 Structural Druggability Assessment
- **Binding Pockets**: [Identified pockets suitable for small molecules]
- **Allosteric Sites**: [Known or predicted]
- **Antibody Epitopes**: [Surface accessibility for biologics]

---

## 5. Function & Pathways

### 5.1 Gene Ontology Annotations

**Molecular Function (MF)**:
| GO Term | GO ID | Evidence |
|---------|-------|----------|
| [Term] | [GO:#######] | [IDA/IEA/etc.] |
[List top 5-10]

**Biological Process (BP)**:
| GO Term | GO ID | Evidence |
|---------|-------|----------|
| [Term] | [GO:#######] | [IDA/IEA/etc.] |
[List top 5-10]

**Cellular Component (CC)**:
| GO Term | GO ID | Evidence |
|---------|-------|----------|
| [Term] | [GO:#######] | [IDA/IEA/etc.] |
[List top 5]

### 5.2 Pathway Involvement
| Pathway | Database | Pathway ID |
|---------|----------|------------|
| [Pathway name] | [Reactome/KEGG/WikiPathways] | [ID] |
[List top 10 pathways]

### 5.3 Functional Summary
[Paragraph describing the target's role in cellular signaling, disease mechanisms, and biological importance]

---

## 6. Protein-Protein Interactions

### 6.1 Interaction Network Summary
- **Total Interactors (STRING, score >0.7)**: [###]
- **Experimentally Validated (IntAct)**: [###]
- **Complex Membership**: [List complexes]

### 6.2 Top Interacting Partners
| Partner | Score | Interaction Type | Evidence | Biological Context |
|---------|-------|------------------|----------|-------------------|
| [Gene] | [0.###] | [Physical/Functional] | [Experimental/Predicted] | [Context] |
[List top 15-20 interactors]

### 6.3 Protein Complexes
| Complex Name | Members | Function |
|--------------|---------|----------|
| [Complex] | [List] | [Function] |

### 6.4 Interaction Network Implications
[Paragraph on network topology, hub status, and implications for drugging]

---

## 7. Expression Profile

### 7.1 Tissue Expression (GTEx/HPA)
| Tissue | Expression Level (TPM) | Specificity |
|--------|------------------------|-------------|
| [Tissue] | [###] | [High/Medium/Low] |
[List top 10 expressing tissues]

**Tissue Specificity Score**: [Score] ([Broadly expressed/Tissue-specific/Tissue-enriched])

### 7.2 Cell Type Expression
[Single-cell data if available - top cell types]

### 7.3 Disease-Relevant Expression
| Cancer/Disease | Expression Change | Prognostic Value |
|----------------|-------------------|------------------|
| [Disease] | [Up/Down/Unchanged] | [Favorable/Unfavorable/None] |

### 7.4 Expression-Based Druggability
- **Tumor vs Normal**: [Differential expression ratio]
- **Therapeutic Window**: [Assessment based on expression pattern]

---

## 8. Genetic Variation & Disease

### 8.1 Genetic Constraint Scores
| Metric | Value | Interpretation |
|--------|-------|----------------|
| pLI | [0.##] | [Highly constrained/Tolerant] |
| LOEUF | [0.##] | [Interpretation] |
| Missense Z-score | [#.##] | [Interpretation] |
| pRec | [0.##] | [Interpretation] |

### 8.2 Disease Associations (Open Targets)
| Disease | Association Score | Evidence Types | EFO ID |
|---------|-------------------|----------------|--------|
| [Disease] | [0.##] | [Genetic/Literature/etc.] | [EFO_#######] |
[List top 10 diseases]

### 8.3 Pathogenic Variants (ClinVar)
| Variant | Clinical Significance | Condition | Review Status |
|---------|----------------------|-----------|---------------|
| [p.XXX###YYY] | [Pathogenic/Likely pathogenic] | [Condition] | [Stars] |
[List notable pathogenic variants]

**Total ClinVar Entries**: [###]
**Pathogenic/Likely Pathogenic**: [###]

### 8.4 Cancer Mutations (COSMIC/cBioPortal)
| Mutation | Frequency | Cancer Types | Functional Impact |
|----------|-----------|--------------|-------------------|
| [Mutation] | [#%] | [Cancers] | [Activating/Inactivating/Unknown] |
[List recurrent cancer mutations]

### 8.5 Genetic Evidence Summary
[Paragraph summarizing genetic validation of the target]

---

## 9. Druggability & Pharmacology

### 9.1 Tractability Assessment (Open Targets)
| Modality | Tractability | Bucket | Evidence |
|----------|--------------|--------|----------|
| Small Molecule | [✅/⚠️/❌] | [1-10] | [Clinical/Predicted] |
| Antibody | [✅/⚠️/❌] | [1-10] | [Clinical/Predicted] |
| PROTAC | [✅/⚠️/❌] | [1-10] | [Structural feasibility] |
| Other Modalities | [✅/⚠️/❌] | [1-10] | [Evidence] |

### 9.2 Approved Drugs
| Drug Name | Brand Name | Mechanism | Indication | Approval Year |
|-----------|------------|-----------|------------|---------------|
| [Drug] | [Brand] | [Inhibitor/Agonist/etc.] | [Indication] | [Year] |
[List all approved drugs]

### 9.3 Clinical Pipeline
| Drug | Phase | Indication | Trial Count | Status |
|------|-------|------------|-------------|--------|
| [Drug] | [Phase I/II/III] | [Indication] | [###] | [Active/Completed] |
[List drugs in clinical development]

**Total Clinical Trials**: [###]
**Active Trials**: [###]

### 9.4 Bioactivity Data (ChEMBL)
- **Total Bioactivity Records**: [###]
- **Compounds Tested**: [###]
- **Most Potent Compound**: [Name] (IC50/Ki: [###] nM)

| Compound | Activity Type | Value | Target |
|----------|---------------|-------|--------|
| [Compound] | [IC50/Ki/Kd] | [###] nM | [Target form] |
[List top 5 most potent compounds]

### 9.5 Chemical Probes
| Probe | Selectivity | Use | Source |
|-------|-------------|-----|--------|
| [Probe] | [Selective/Broad] | [Recommended use] | [SGC/etc.] |

### 9.6 Drug Resistance
[Known resistance mechanisms, mutations, or mechanisms if applicable]

---

## 10. Safety Profile

### 10.1 Target Safety Liabilities (Open Targets)
| Safety Concern | Evidence | Severity | Organ System |
|----------------|----------|----------|--------------|
| [Concern] | [Animal/Human/Both] | [High/Medium/Low] | [System] |

### 10.2 Mouse Knockout Phenotypes
| Phenotype | Zygosity | Viability | Source |
|-----------|----------|-----------|--------|
| [Phenotype] | [Homo/Hetero] | [Viable/Lethal] | [IMPC/MGI] |

### 10.3 Known Drug Adverse Events
| Adverse Event | Frequency | Drug Class | Mechanism |
|---------------|-----------|------------|-----------|
| [Event] | [Common/Uncommon/Rare] | [Class] | [On-target/Off-target] |

### 10.4 Safety Summary
[Paragraph summarizing safety considerations for targeting this protein]

---

## 11. Literature & Research Landscape

### 11.1 Publication Metrics
| Metric | Value |
|--------|-------|
| Total Publications | [###,###] |
| Publications (Last 5 Years) | [###,###] |
| Publications (Last Year) | [###,###] |
| Drug-Related Publications | [###,###] |
| Clinical Publications | [###,###] |

### 11.2 Research Trend
- **Trend**: [Increasing/Stable/Declining]
- **Peak Year**: [Year]
- **Current Activity**: [High/Medium/Low]

### 11.3 Key Research Areas
[List current hot topics in research for this target]

### 11.4 Notable Recent Publications
| PMID | Title | Year | Key Finding |
|------|-------|------|-------------|
| [PMID] | [Title] | [Year] | [Finding] |
[List 3-5 important recent papers]

---

## 12. Competitive Landscape

### 12.1 Market Status
- **First-in-Class Approved**: [Yes/No - Drug name if yes]
- **Best-in-Class Status**: [Assessment]
- **Patent Landscape**: [Crowded/Moderate/Open]

### 12.2 Differentiation Opportunities
[List potential differentiation strategies for new entrants]

---

## 13. Summary & Recommendations

### 13.1 Target Validation Scorecard
| Criterion | Score (1-5) | Evidence Level |
|-----------|-------------|----------------|
| Genetic Evidence | [#] | [Strong/Moderate/Weak] |
| Expression Relevance | [#] | [Strong/Moderate/Weak] |
| Functional Understanding | [#] | [Strong/Moderate/Weak] |
| Druggability | [#] | [Strong/Moderate/Weak] |
| Safety Profile | [#] | [Favorable/Caution/Concern] |
| Competitive Position | [#] | [Open/Moderate/Crowded] |

**Overall Target Score**: [##/30]

### 13.2 Key Strengths
1. [Strength 1]
2. [Strength 2]
3. [Strength 3]

### 13.3 Key Challenges/Risks
1. [Challenge 1]
2. [Challenge 2]
3. [Challenge 3]

### 13.4 Recommendations
| Priority | Category | Recommendation |
|----------|----------|----------------|
| 🔴 HIGH | [Category] | [Recommendation] |
| 🟡 MEDIUM | [Category] | [Recommendation] |
| 🟢 LOW | [Category] | [Recommendation] |
| ℹ️ INFO | [Category] | [Recommendation] |

### 13.5 Next Steps
[Suggested follow-up analyses or experiments]

---

## 14. Data Sources & Methodology

### 14.1 Databases Queried
| Database | Section(s) | Queries | Status |
|----------|------------|---------|--------|
| UniProtKB | 2, 3, 4, 8 | [accession] | ✅ Success |
| RCSB PDB | 4 | [PDB IDs queried] | ✅ Success |
| AlphaFold DB | 4 | [accession] | ✅ Success |
| InterPro | 4 | [accession] | ✅ Success |
| Gene Ontology | 5 | [gene_id] | ✅ Success |
| Reactome | 5 | [accession] | ✅ Success |
| KEGG | 5 | [gene_id] | ✅ Success |
| STRING | 6 | [protein_ids] | ✅ Success |
| IntAct | 6 | [accession] | ✅ Success |
| GTEx | 7 | [gencode_id] | ✅ Success |
| Human Protein Atlas | 7 | [ensembl_id] | ✅ Success |
| gnomAD | 8 | [gene_symbol] | ✅ Success |
| ClinVar | 8 | [gene] | ✅ Success |
| Open Targets | 8, 9, 10 | [ensembl_id] | ✅ Success |
| ChEMBL | 9 | [target_chembl_id] | ✅ Success |
| DGIdb | 9 | [genes] | ✅ Success |
| PubMed | 11 | [query] | ✅ Success |

### 14.2 Tools Used by Section
| Section | Tools Used |
|---------|------------|
| 2. Identifiers | `UniProt_search`, `UniProt_id_mapping`, `MyGene_get_gene_annotation` |
| 3. Basic Info | `UniProt_get_entry_by_accession`, `UniProt_get_function_by_accession`, `UniProt_get_subcellular_location_by_accession` |
| 4. Structure | `get_protein_metadata_by_pdb_id`, `alphafold_get_prediction`, `InterPro_get_protein_domains`, `UniProt_get_ptm_processing_by_accession` |
| 5. Function | `GO_get_annotations_for_gene`, `Reactome_map_uniprot_to_pathways`, `kegg_get_gene_info` |
| 6. Interactions | `STRING_get_protein_interactions`, `intact_get_interactions`, `intact_get_complex_details` |
| 7. Expression | `GTEx_get_median_gene_expression`, `HPA_get_comprehensive_gene_details_by_ensembl_id`, `HPA_get_subcellular_location` |
| 8. Variants | `gnomad_get_gene_constraints`, `clinvar_search_variants`, `OpenTargets_get_diseases_phenotypes_by_target_ensembl` |
| 9. Druggability | `OpenTargets_get_target_tractability_by_ensemblID`, `OpenTargets_get_associated_drugs_by_target_ensemblID`, `DGIdb_get_gene_druggability`, `ChEMBL_get_target_activities` |
| 10. Safety | `OpenTargets_get_target_safety_profile_by_ensemblID`, `OpenTargets_get_biological_mouse_models_by_ensemblID` |
| 11. Literature | `PubMed_search_articles`, `EuropePMC_search_articles`, `OpenTargets_get_publications_by_target_ensemblID` |

### 14.3 Data Freshness
- **Report Generated**: [YYYY-MM-DD HH:MM UTC]
- **UniProt Release**: [Release number if available]
- **PDB Last Updated**: [Date]
- **GTEx Version**: v8
- **gnomAD Version**: v4.0

### 14.4 Limitations & Data Gaps
[Document any issues encountered:]
- Tools that returned errors or empty results
- Sections with incomplete data
- Known data quality issues
- Databases that were unavailable

Example:
- ⚠️ IntAct returned no experimentally validated interactions
- ⚠️ Some ChEMBL activity data may include non-human orthologs
- ✅ All primary data sources queried successfully

---

## Appendix (Optional)

### A. Full Sequence
[Protein sequence in FASTA format if requested]

### B. Additional Structures
[Extended PDB list if many available]

### C. Complete Interaction List
[Full PPI list if requested]

### D. All Variants
[Complete variant list if requested]
```

---

## Section Completeness Checklist

For each report, verify ALL items:

### Required Sections
- [ ] Section 1: Executive Summary with bottom line
- [ ] Section 2: All identifier types (UniProt, Ensembl, Entrez, ChEMBL)
- [ ] Section 3: Basic info with function description (3-4 sentences)
- [ ] Section 4: Structural data (PDB count, domains, AlphaFold)
- [ ] Section 5: GO terms (5-10 per category) and pathways (top 10)
- [ ] Section 6: PPI (15-20 interactors, complexes)
- [ ] Section 7: Expression (top 10 tissues, specificity)
- [ ] Section 8: Variants (constraint scores, top 10 diseases, pathogenic variants)
- [ ] Section 9: Druggability (tractability, all drugs, clinical pipeline)
- [ ] Section 10: Safety (liabilities, mouse KO, adverse events)
- [ ] Section 11: Literature (5 metrics, trend, key papers)
- [ ] Section 12: Competitive landscape
- [ ] Section 13: Scorecard and recommendations
- [ ] Section 14: Data sources and methodology

### Data Minimums
- [ ] At least 5 PDB structures listed (if available)
- [ ] All protein domains included
- [ ] Top 10 GO terms per category
- [ ] Top 10 pathways
- [ ] Top 15-20 protein interactors
- [ ] Expression in top 10 tissues
- [ ] All 4 constraint scores (pLI, LOEUF, missense Z, pRec)
- [ ] Top 10 disease associations
- [ ] All approved drugs listed
- [ ] All safety concerns documented
- [ ] 5 publication metrics
- [ ] 3-5 recent key publications
- [ ] Scorecard with all 6 criteria
- [ ] At least 3 prioritized recommendations

### Quality Checks
- [ ] Executive summary is 2-3 sentences
- [ ] Function description is 3-4 sentences
- [ ] All tables have data (no empty tables)
- [ ] Paragraphs provide synthesis, not just lists
- [ ] Recommendations are actionable and prioritized
- [ ] Limitations section is honest about data gaps

---

## Section-Specific Guidance

### Section 1: Executive Summary
**Purpose**: Give reader the key takeaways in 30 seconds

Include:
1. What the target IS (protein class, function)
2. Clinical relevance (disease associations)
3. Druggability status (has drugs? tractable?)
4. One-line recommendation

Example:
> EGFR is a receptor tyrosine kinase that drives cell proliferation and is overexpressed in multiple cancers including NSCLC and glioblastoma. Multiple approved TKIs and monoclonal antibodies validate this as a highly druggable target, though resistance mutations remain a challenge.
>
> **Bottom Line**: Well-validated, druggable target with clinical precedence; new programs should focus on resistance-breaking or novel modalities.

### Section 4: Structural Biology
**Purpose**: Enable structure-based drug design decisions

Must include:
- Total PDB count and best resolution
- Coverage (which domains have structures?)
- AlphaFold availability and confidence
- Complete domain list with positions
- Key binding sites for drug design

### Section 9: Druggability
**Purpose**: Assess feasibility and competitive landscape

Must include:
- Tractability for ALL modalities (SM, Ab, PROTAC, other)
- Complete list of approved drugs
- Clinical pipeline (phase, indication, status)
- ChEMBL bioactivity summary
- Chemical probes if available

### Section 13: Recommendations
**Purpose**: Provide actionable next steps

Requirements:
- Use priority levels (HIGH/MEDIUM/LOW/INFO)
- Each recommendation must be actionable
- Include both opportunities and risks
- Suggest specific follow-up analyses

Example:
| Priority | Category | Recommendation |
|----------|----------|----------------|
| 🔴 HIGH | Validation | Strong genetic and clinical validation supports target |
| 🔴 HIGH | Competition | Crowded space - need clear differentiation strategy |
| 🟡 MEDIUM | Safety | Monitor for cardiotoxicity based on KO phenotype |
| 🟢 LOW | Structure | Additional cryo-EM of full-length protein would help |
| ℹ️ INFO | Literature | Review recent resistance mechanism papers |
