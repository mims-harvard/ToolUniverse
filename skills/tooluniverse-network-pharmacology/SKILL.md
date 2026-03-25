---
name: tooluniverse-network-pharmacology
description: Construct and analyze compound-target-disease networks for drug repurposing, polypharmacology discovery, and systems pharmacology. Builds multi-layer networks from ChEMBL, OpenTargets, STRING, DrugBank, Reactome, FAERS, and 60+ other ToolUniverse tools. Calculates Network Pharmacology Scores (0-100), identifies repurposing candidates, predicts mechanisms, and analyzes polypharmacology. Use when users ask about drug repurposing via network analysis, multi-target drug effects, compound-target-disease networks, systems pharmacology, or polypharmacology.
---

# Network Pharmacology Pipeline

Construct and analyze compound-target-disease (C-T-D) networks to identify drug repurposing opportunities, understand polypharmacology, and predict drug mechanisms using systems pharmacology approaches.

**IMPORTANT**: Always use English terms in tool calls (drug names, disease names, target names), even if the user writes in another language. Only try original-language terms as a fallback if English returns no results. Respond in the user's language.

---

## When to Use This Skill

Apply when users:
- Ask "Can [drug] be repurposed for [disease] based on network analysis?"
- Want to understand multi-target (polypharmacology) effects of a compound
- Need compound-target-disease network construction and analysis
- Ask about network proximity between drug targets and disease genes
- Want systems pharmacology analysis of a drug or target
- Ask about drug repurposing candidates ranked by network metrics
- Need mechanism prediction for a drug in a new indication
- Want to identify hub genes in disease networks as therapeutic targets
- Ask about disease module coverage by a compound's targets

**NOT for** (use other skills instead):
- Simple drug repurposing without network analysis -> Use `tooluniverse-drug-repurposing`
- Single target validation -> Use `tooluniverse-drug-target-validation`
- Adverse event detection only -> Use `tooluniverse-adverse-event-detection`
- General disease research -> Use `tooluniverse-disease-research`
- GWAS interpretation -> Use `tooluniverse-gwas-snp-interpretation`

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **entity** | Yes | Compound name/ID, target gene symbol/ID, or disease name/ID | `metformin`, `EGFR`, `Alzheimer disease` |
| **entity_type** | No | Type hint: `compound`, `target`, or `disease` (auto-detected if omitted) | `compound` |
| **analysis_mode** | No | `compound-to-disease`, `disease-to-compound`, `target-centric`, `bidirectional` (default) | `bidirectional` |
| **secondary_entity** | No | Second entity for focused analysis (e.g., disease for compound input) | `Alzheimer disease` |

---

## Network Pharmacology Score (0-100)

| Component | Max Points | Criteria for Max |
|-----------|-----------|-----------------|
| Network Proximity | 35 | Z < -2, p < 0.01 |
| Clinical Evidence | 25 | Approved for related indication |
| Target-Disease Association | 20 | Strong genetic evidence (GWAS, rare variants) |
| Safety Profile | 10 | FDA-approved, favorable safety |
| Mechanism Plausibility | 10 | Clear pathway mechanism with functional evidence |

### Priority Tiers

| Score | Tier | Recommendation |
|-------|------|----------------|
| **80-100** | Tier 1 | High repurposing potential - proceed with experimental validation |
| **60-79** | Tier 2 | Good potential - needs mechanistic validation |
| **40-59** | Tier 3 | Moderate potential - high-risk/high-reward |
| **0-39** | Tier 4 | Low potential - consider alternative approaches |

### Evidence Grading

| Tier | Criteria | Examples |
|------|----------|----------|
| **T1** | Human clinical proof, regulatory evidence | FDA-approved, Phase III trial |
| **T2** | Functional experimental evidence | IC50 < 1 uM, CRISPR screen |
| **T3** | Association/computational evidence | GWAS hit, network proximity |
| **T4** | Prediction, annotation, text-mining | AlphaFold, literature co-mention |

> Full scoring details: [SCORING_REFERENCE.md](SCORING_REFERENCE.md)

---

## Key Principles

1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Entity disambiguation FIRST** - Resolve all identifiers before analysis
3. **Bidirectional network** - Construct C-T-D network comprehensively from both directions
4. **Network metrics** - Calculate proximity, centrality, module overlap quantitatively
5. **Rank candidates** - Prioritize by composite Network Pharmacology Score
6. **Mechanism prediction** - Explain HOW drug could work for disease via network paths
7. **Clinical feasibility** - FDA-approved drugs ranked higher than preclinical
8. **Safety context** - Flag known adverse events and off-target liabilities
9. **Evidence grading** - Grade all evidence T1-T4
10. **Negative results documented** - "No data" is data; empty sections are failures
11. **Source references** - Every finding must cite the source tool/database
12. **Completeness checklist** - Mandatory section at end showing analysis coverage

---

## Workflow Overview

### Phase 0: Entity Disambiguation and Report Setup
- Create report file immediately
- Resolve entity to all required IDs (ChEMBL, DrugBank, PubChem CID, Ensembl, MONDO/EFO)
- Tools: `OpenTargets_get_drug_chembId_by_generic_name`, `drugbank_get_drug_basic_info_by_drug_name_or_id`, `PubChem_get_CID_by_compound_name`, `OpenTargets_get_target_id_description_by_name`, `OpenTargets_get_disease_id_description_by_name`

### Phase 1: Network Node Identification
- **Compound nodes**: Drug targets, mechanism of action, current indications
- **Target nodes**: Disease-associated genes, GWAS targets, druggability levels
- **Disease nodes**: Related diseases, hierarchy, phenotypes
- Tools: `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`, `OpenTargets_get_associated_targets_by_drug_chemblId`, `drugbank_get_targets_by_drug_name_or_drugbank_id`, `DGIdb_get_drug_gene_interactions`, `CTD_get_chemical_gene_interactions`, `OpenTargets_get_associated_targets_by_disease_efoId`, `Pharos_get_target`

### Phase 2: Network Edge Construction
- **C-T edges**: Bioactivity data (ChEMBL, DrugBank, BindingDB)
- **T-D edges**: Genetic/functional associations (OpenTargets evidence, GWAS, CTD)
- **C-D edges**: Clinical trials, CTD chemical-disease, literature co-mentions
- **T-T edges**: PPI network (STRING, IntAct, OpenTargets interactions, HumanBase)
- Tools: `ChEMBL_get_target_activities`, `OpenTargets_target_disease_evidence`, `GWAS_search_associations_by_gene`, `search_clinical_trials`, `CTD_get_chemical_diseases`, `STRING_get_interaction_partners`, `STRING_get_network`, `intact_search_interactions`, `humanbase_ppi_analysis`

### Phase 3: Network Analysis
- Node degree, hub identification, betweenness centrality
- Network modules (drug module vs disease module), module overlap
- Shortest paths between drug targets and disease genes
- Network proximity Z-score calculation
- Functional enrichment (STRING, Enrichr, Reactome)
- Tools: `STRING_functional_enrichment`, `STRING_ppi_enrichment`, `enrichr_gene_enrichment_analysis`, `ReactomeAnalysis_pathway_enrichment`

### Phase 4: Drug Repurposing Predictions
- Identify drugs targeting disease genes (disease-to-compound mode)
- Find diseases associated with drug targets (compound-to-disease mode)
- Rank candidates by composite Network Pharmacology Score
- Predict mechanisms via shared pathways and network paths
- Tools: `OpenTargets_get_associated_drugs_by_target_ensemblID`, `drugbank_get_drug_name_and_description_by_target_name`, `drugbank_get_pathways_reactions_by_drug_or_id`

### Phase 5: Polypharmacology Analysis
- Multi-target profiling (primary vs off-targets)
- Disease module coverage calculation
- Target family analysis and selectivity
- Tools: `OpenTargets_get_target_classes_by_ensemblID`, `DGIdb_get_gene_druggability`, `OpenTargets_get_target_tractability_by_ensemblID`

### Phase 6: Safety and Toxicity Context
- Adverse event profiling (FAERS disproportionality, OpenTargets AEs)
- Target safety (gene constraints, expression, safety profiles)
- FDA warnings, black box status
- Tools: `FAERS_calculate_disproportionality`, `FAERS_filter_serious_events`, `FAERS_count_death_related_by_drug`, `FDA_get_warnings_and_cautions_by_drug_name`, `OpenTargets_get_drug_adverse_events_by_chemblId`, `OpenTargets_get_target_safety_profile_by_ensemblID`, `gnomad_get_gene_constraints`

### Phase 7: Validation Evidence
- Clinical trials for drug-disease pair
- Literature evidence (PubMed, EuropePMC)
- ADMET predictions if SMILES available
- Pharmacogenomics data
- Tools: `search_clinical_trials`, `clinical_trials_get_details`, `PubMed_search_articles`, `EuropePMC_search_articles`, `ADMETAI_predict_toxicity`, `PharmGKB_get_drug_details`

### Phase 8: Report Generation
- Compute Network Pharmacology Score from components
- Generate report using template
- Include completeness checklist

> Full step-by-step code examples: [ANALYSIS_PROCEDURES.md](ANALYSIS_PROCEDURES.md)
> Report template: [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md)

---

## Critical Tool Parameter Notes

- **DrugBank tools**: ALL require `query`, `case_sensitive`, `exact_match`, `limit` (4 params, ALL required)
- **FAERS analytics tools**: ALL require `operation` parameter
- **FAERS count tools**: Use `medicinalproduct` NOT `drug_name`
- **OpenTargets tools**: Return nested `{data: {entity: {field: ...}}}` structure
- **PubMed_search_articles**: Returns plain list of dicts, NOT `{articles: [...]}`
- **ReactomeAnalysis_pathway_enrichment**: Takes space-separated `identifiers` string, NOT array
- **ensembl_lookup_gene**: REQUIRES `species='homo_sapiens'` parameter

> Full tool parameter reference and response structures: [TOOL_REFERENCE.md](TOOL_REFERENCE.md)

---

## Fallback Strategies

| Phase | Primary Tool | Fallback 1 | Fallback 2 |
|-------|-------------|-----------|-----------|
| Compound ID | OpenTargets drug lookup | ChEMBL search | PubChem CID lookup |
| Target ID | OpenTargets target lookup | ensembl_lookup_gene | MyGene_query_genes |
| Disease ID | OpenTargets disease lookup | ols_search_efo_terms | CTD_get_chemical_diseases |
| Drug targets | OpenTargets drug mechanisms | DrugBank targets | DGIdb interactions |
| Disease targets | OpenTargets disease targets | CTD gene-diseases | GWAS associations |
| PPI network | STRING interactions | OpenTargets interactions | IntAct interactions |
| Pathways | ReactomeAnalysis enrichment | enrichr enrichment | STRING functional enrichment |
| Clinical trials | search_clinical_trials | ClinicalTrials_search_studies | PubMed clinical |
| Safety | FAERS + FDA | OpenTargets AEs | DrugBank safety |
| Literature | PubMed search | EuropePMC search | OpenTargets publications |

---

## Reference Files

| File | Contents |
|------|----------|
| [ANALYSIS_PROCEDURES.md](ANALYSIS_PROCEDURES.md) | Full code examples for each phase (Phases 0-8) |
| [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) | Markdown template for final report output |
| [SCORING_REFERENCE.md](SCORING_REFERENCE.md) | Detailed scoring rubric and computation method |
| [TOOL_REFERENCE.md](TOOL_REFERENCE.md) | Tool signatures, response structures, troubleshooting |
| [USE_PATTERNS.md](USE_PATTERNS.md) | Common analysis patterns and edge case strategies |
| [QUICK_START.md](QUICK_START.md) | Quick-start guide with minimal examples |

---

## Related Skills

- [tooluniverse-drug-repurposing](../tooluniverse-drug-repurposing/SKILL.md) - Drug repurposing without network analysis
- [tooluniverse-drug-target-validation](../tooluniverse-drug-target-validation/SKILL.md) - Target validation
- [tooluniverse-adverse-event-detection](../tooluniverse-adverse-event-detection/SKILL.md) - Adverse event detection
- [tooluniverse-systems-biology](../tooluniverse-systems-biology/SKILL.md) - Systems biology
- [tooluniverse-protein-interactions](../tooluniverse-protein-interactions/SKILL.md) - Protein interactions
