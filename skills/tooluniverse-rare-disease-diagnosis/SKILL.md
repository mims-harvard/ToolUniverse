---
name: tooluniverse-rare-disease-diagnosis
description: Provide differential diagnosis for patients with suspected rare diseases based on phenotype and genetic data. Matches symptoms to HPO terms, identifies candidate diseases from Orphanet/OMIM, prioritizes genes for testing, interprets variants of uncertain significance. Use when clinician asks about rare disease diagnosis, unexplained phenotypes, or genetic testing interpretation.
---

# Rare Disease Diagnosis Advisor

Systematic diagnosis support for rare diseases using phenotype matching, gene panel prioritization, and variant interpretation across Orphanet, OMIM, HPO, ClinVar, and structure-based analysis.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, update progressively
2. **Phenotype-driven** - Convert symptoms to HPO terms before searching
3. **Multi-database triangulation** - Cross-reference Orphanet, OMIM, OpenTargets
4. **Evidence grading** - Grade diagnoses by supporting evidence strength
5. **Actionable output** - Prioritized differential diagnosis with next steps
6. **Genetic counseling aware** - Consider inheritance patterns and family history
7. **English-first queries** - Always use English terms in tool calls (phenotype descriptions, gene names, disease names), even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

---

## When to Use

Apply when user asks:
- "Patient has [symptoms], what rare disease could this be?"
- "Unexplained developmental delay with [features]"
- "WES found VUS in [gene], is this pathogenic?"
- "What genes should we test for [phenotype]?"
- "Differential diagnosis for [rare symptom combination]"

---

## Report-First Approach (MANDATORY)

1. **Create the report file FIRST**: `[PATIENT_ID]_rare_disease_report.md` with all section headers and `[Researching...]` placeholders
2. **Progressively update** as you gather data
3. **Output separate data files**:
   - `[PATIENT_ID]_gene_panel.csv` - Prioritized genes for testing
   - `[PATIENT_ID]_variant_interpretation.csv` - If variants provided

Every finding MUST include source citation (ORPHA code, OMIM number, tool name).

See [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) for the full template and example outputs for each phase.

---

## Tool Parameter Corrections

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblID` | `ensemblId` |
| `ClinVar_get_variant_details` | `variant_id` | `id` |
| `MyGene_query_genes` | `gene` | `q` |
| `gnomad_get_variant` | `variant` | `variant_id` |

---

## Workflow Overview

```
Phase 1: Phenotype Standardization
  Convert symptoms to HPO terms, identify core vs. variable features, note onset/inheritance
      |
Phase 2: Disease Matching
  Search Orphanet, cross-reference OMIM, query DisGeNET -> Ranked differential diagnosis
      |
Phase 3: Gene Panel Identification
  Extract genes from top diseases, validate with ClinGen, check expression (GTEx)
      |
Phase 3.5: Expression & Tissue Context
  CELLxGENE cell-type expression, ChIPAtlas regulatory context
      |
Phase 3.6: Pathway Analysis
  KEGG pathways, Reactome processes, IntAct protein interactions
      |
Phase 4: Variant Interpretation (if provided)
  ClinVar lookup, gnomAD frequency, computational predictions (CADD, AlphaMissense, EVE, SpliceAI)
      |
Phase 5: Structure Analysis (for VUS)
  AlphaFold2 prediction, domain impact assessment (InterPro)
      |
Phase 6: Literature Evidence
  PubMed studies, BioRxiv/MedRxiv preprints, OpenAlex citation analysis
      |
Phase 7: Report Synthesis
  Prioritized differential, recommended testing, next steps
```

For detailed code examples and algorithms for each phase, see [DIAGNOSTIC_WORKFLOW.md](DIAGNOSTIC_WORKFLOW.md).

---

## Phase Summaries

### Phase 1: Phenotype Standardization

- Use `HPO_search_terms(query=symptom)` to convert each clinical description to HPO terms
- Classify features as Core (always present), Variable (>50%), Occasional (<50%), or Age-specific
- Record age of onset and family history for inheritance pattern hints

### Phase 2: Disease Matching

- **Orphanet**: `Orphanet_search_diseases(operation="search_diseases", query=keyword)` then `Orphanet_get_genes(operation="get_genes", orpha_code=code)` for each hit
- **OMIM**: `OMIM_search(operation="search", query=gene)` then `OMIM_get_entry` and `OMIM_get_clinical_synopsis` for details
- **DisGeNET**: `DisGeNET_search_gene(operation="search_gene", gene=symbol)` for gene-disease association scores
- Score phenotype overlap: Excellent (>80%), Good (60-80%), Possible (40-60%), Unlikely (<40%)

### Phase 3: Gene Panel Identification

- Extract genes from top candidate diseases
- **ClinGen validation** (critical): `ClinGen_search_gene_validity`, `ClinGen_search_dosage_sensitivity`, `ClinGen_search_actionability`
- ClinGen classification determines panel inclusion:
  - Definitive/Strong/Moderate: Include in panel
  - Limited: Include but flag
  - Disputed/Refuted: Exclude
- **Expression**: Use `MyGene_query_genes` for Ensembl ID, then `GTEx_get_median_gene_expression` to confirm tissue expression
- Prioritization scoring: Tier 1 (top disease gene +5), Tier 2 (multi-disease +3), Tier 3 (ClinGen Definitive +3), Tier 4 (tissue expression +2), Tier 5 (pLI >0.9 +1)

### Phase 3.5: Expression & Tissue Context

- **CELLxGENE**: `CELLxGENE_get_expression_data` and `CELLxGENE_get_cell_metadata` for cell-type specific expression
- **ChIPAtlas**: `ChIPAtlas_enrichment_analysis` and `ChIPAtlas_get_peak_data` for regulatory context (TF binding)
- Confirms candidate genes are expressed in disease-relevant tissues/cells

### Phase 3.6: Pathway Analysis

- **KEGG**: `kegg_find_genes(query="hsa:{gene}")` then `kegg_get_gene_info` for pathway membership
- **IntAct**: `intact_search_interactions(query=gene, species="human")` for protein-protein interactions
- Identify convergent pathways across candidate genes (strengthens candidacy)

### Phase 4: Variant Interpretation (if provided)

- **ClinVar**: `ClinVar_search_variants(query=hgvs)` for existing classifications
- **gnomAD**: `gnomad_get_variant(variant_id=id)` for population frequency
  - Ultra-rare (<0.00001), Rare (<0.0001), Low frequency (<0.01), Common (likely benign)
- **Computational predictions** (for VUS):
  - CADD: `CADD_get_variant_score` - PHRED >=20 supports PP3
  - AlphaMissense: `AlphaMissense_get_variant_score` - pathogenic classification = strong PP3
  - EVE: `EVE_get_variant_score` - score >0.5 supports PP3
  - SpliceAI: `SpliceAI_predict_splice` - delta score >=0.5 indicates splice impact
- **ACMG criteria**: PVS1 (null variant), PS1 (same AA change), PM2 (absent from pop), PP3 (computational), BA1 (>5% AF)
- Consensus from 2+ concordant predictors strengthens PP3 evidence

### Phase 5: Structure Analysis (for VUS)

- Perform when: VUS, missense in critical domain, novel variant, or additional evidence needed
- **AlphaFold2**: `alphafold_get_prediction(sequence=seq, algorithm="mmseqs2")` for structure prediction
- **Domain impact**: `InterPro_get_protein_domains(accession=uniprot_id)` to check functional domains
- Assess pLDDT confidence at variant position, domain location, structural role

### Phase 6: Literature Evidence

- **PubMed**: `PubMed_search_articles(query="disease AND genetics")` for published studies
- **Preprints**: `BioRxiv_list_recent_preprints`, `ArXiv_search_papers(category="q-bio")` for latest findings
- **Citations**: `openalex_search_works` for citation analysis of key papers
- Note: preprints are not peer-reviewed; flag accordingly

### Phase 7: Report Synthesis

- Compile all phases into final report with evidence grading
- Provide prioritized differential diagnosis with next steps
- Include specialist referral suggestions and family screening recommendations

---

## Evidence Grading

| Tier | Criteria | Example |
|------|----------|---------|
| **T1** (High) | Phenotype match >80% + gene match | Marfan with FBN1 mutation |
| **T2** (Medium-High) | Phenotype match 60-80% OR likely pathogenic variant | Good phenotype fit |
| **T3** (Medium) | Phenotype match 40-60% OR VUS in candidate gene | Possible diagnosis |
| **T4** (Low) | Phenotype <40% OR uncertain gene | Low probability |

---

## Completeness Checklist

**Phase 1 (Phenotype)**: All symptoms as HPO terms, core vs. variable distinguished, onset documented, family history noted

**Phase 2 (Disease Matching)**: >=5 candidates (or all matching), overlap % calculated, inheritance patterns, ORPHA + OMIM IDs

**Phase 3 (Gene Panel)**: >=5 genes prioritized, ClinGen evidence level per gene, expression validated, testing strategy recommended

**Phase 4 (Variants)**: ClinVar classification, gnomAD frequency, ACMG criteria applied, classification justified

**Phase 5 (Structure)**: Structure predicted (if VUS), pLDDT reported, domain impact assessed, structural evidence summarized

**Phase 6 (Recommendations)**: >=3 next steps, specialist referrals, family screening addressed

See [CHECKLIST.md](CHECKLIST.md) for the full interactive checklist.

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `get_joint_associated_diseases_by_HPO_ID_list` | `Orphanet_search_diseases` | PubMed phenotype search |
| `ClinVar_get_variant_details` | `gnomad_get_variant` | VEP annotation |
| `alphafold_get_prediction` | `alphafold_get_prediction` | UniProt features |
| `GTEx_get_expression_summary` | `HPA_search_genes_by_query` | Tissue-specific literature |
| `gnomad_get_variant` | `gnomad_get_variant` | 1000 Genomes |

---

## Reference Files

- [DIAGNOSTIC_WORKFLOW.md](DIAGNOSTIC_WORKFLOW.md) - Detailed code examples and algorithms for each phase
- [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) - Report template, phase output examples, CSV formats
- [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) - Complete tool documentation
- [CHECKLIST.md](CHECKLIST.md) - Interactive completeness checklist
- [EXAMPLES.md](EXAMPLES.md) - Worked diagnosis examples
