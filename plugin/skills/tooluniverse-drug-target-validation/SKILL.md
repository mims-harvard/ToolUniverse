---
name: tooluniverse-drug-target-validation
description: Quantitative drug-target validation pipeline. Scores druggability, selectivity, safety profile, ADMET feasibility, and structural tractability with a composite Target Validation Score (0-100) and GO/NO-GO recommendation. Use for go/no-go decisions on a target before commit-to-medchem, target prioritization across a list, and target-deselection rationale.
disable-model-invocation: true
---

# Drug Target Validation Pipeline

Validate drug target hypotheses using multi-dimensional computational evidence before committing to wet-lab work. Produces a quantitative Target Validation Score (0-100) with priority tier classification and GO/NO-GO recommendation.

## Reasoning Before Searching

A valid drug target must pass 4 gates in order. Failing an early gate makes later gates irrelevant:

1. **Genetic evidence linking it to disease**: Does human genetic data (GWAS, rare variant studies, Mendelian genetics) support this target's role? Genetic evidence is the strongest predictor of clinical success. Use OpenTargets and GWAS catalog before anything else. If no genetic link exists, the hypothesis is speculative — document this clearly.
2. **Druggability**: Can a molecule reach and modulate the target? Check structure availability (PDB, AlphaFold), binding pocket prediction (ProteinsPlus), target class (kinase, GPCR, nuclear receptor = favorable; transcription factor, scaffold protein = difficult), and existing chemical probes.
3. **Safety — essentiality in normal tissue**: Is the target expressed in critical tissues (heart, liver, bone marrow)? Is knockout lethal in mice? High expression in essential tissue or lethality in mouse models is a strong safety red flag even before any clinical data.
4. **Competitive landscape**: Are other drugs already approved or in late-stage trials for this target? If so, the bar is differentiation, not first-in-class. Check ChEMBL, DrugBank, and ClinicalTrials.gov early.

Do not proceed to Phase 3 (Chemical Matter) before completing Phase 1 (Disease Association). Gate 1 failures should prompt a NO-GO or pivot recommendation.

**LOOK UP DON'T GUESS**: Never assume a target is druggable based on its protein family alone, never assume expression is low in a tissue without checking GTEx or HPA, never assume no competitors without searching ClinicalTrials.gov.

**RUN THE ML MODELS, DON'T SKIP THEM**: When deep-learning predictors are available (ADMET-AI, ESMFold, AlphaFold, DoGSite, DynaMut2, DeepGO), **run them even when database lookups or experimental data already cover the same property**. The ML predictions provide an orthogonal, mechanistically-grounded estimate that's a first-class output of this skill — not a fallback. A target-validation report missing ML predictions is incomplete regardless of how much database evidence is present.

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Key Principles

1. **Report-first** - Create report file FIRST, then populate progressively
2. **Target disambiguation FIRST** - Resolve all identifiers before analysis
3. **Evidence grading** - Grade all evidence as T1 (experimental) to T4 (computational)
4. **Disease-specific** - Tailor analysis to disease context when provided
5. **Modality-aware** - Consider small molecule vs biologics tractability
6. **Safety-first** - Prominently flag safety concerns early
7. **Quantitative scoring** - Every dimension scored numerically (0-100 composite)
8. **Negative results documented** - "No data" is data; empty sections are failures
9. **Source references** - Every statement must cite tool/database
10. **English-first queries** - Always use English terms in tool calls; respond in user's language

## When to Use

Apply when users ask about:
- "Is [target] a good drug target for [disease]?"
- Target validation, druggability assessment, or target prioritization
- Safety risks of modulating a target
- Chemical starting points for target validation
- GO/NO-GO recommendation for a target

**Not for** (use other skills): general target biology (`tooluniverse-target-research`), drug compound profiling (`tooluniverse-drug-research`), variant interpretation (`tooluniverse-variant-interpretation`), disease research (`tooluniverse-disease-research`).

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **target** | Yes | Gene symbol, protein name, or UniProt ID | `EGFR`, `P00533` |
| **disease** | No | Disease/indication for context | `Non-small cell lung cancer` |
| **modality** | No | Preferred therapeutic modality | `small molecule`, `antibody`, `PROTAC` |

## Reference Files

- **SCORING_CRITERIA.md** - Detailed scoring matrices, evidence grading, priority tiers, score calculation
- **REPORT_TEMPLATE.md** - Full report template, completeness checklist, section format examples
- **TOOL_REFERENCE.md** - Verified tool parameters, known corrections, fallback chains, modality-specific guidance, phase-by-phase tool lists
- **QUICK_START.md** - Quick start guide

---

## Scoring Overview

**Total: 0-100 points** across 5 dimensions (details in SCORING_CRITERIA.md):

| Dimension | Max | Sub-dimensions |
|-----------|-----|----------------|
| Disease Association | 30 | Genetic (10) + Literature (10) + Pathway (10) |
| Druggability | 25 | Structure (10) + Chemical matter (10) + Target class (5) |
| Safety Profile | 20 | Expression (5) + Genetic validation (10) + ADRs (5) |
| Clinical Precedent | 15 | Based on highest clinical stage achieved |
| Validation Evidence | 10 | Functional studies (5) + Disease models (5) |

**Priority Tiers**: 80-100 = Tier 1 (GO) | 60-79 = Tier 2 (CONDITIONAL GO) | 40-59 = Tier 3 (CAUTION) | 0-39 = Tier 4 (NO-GO)

**Evidence Grades**: T1 (clinical proof) > T2 (functional studies) > T3 (associations) > T4 (predictions)

---

## Pipeline Phases

### Phase 0: Target Disambiguation (ALWAYS FIRST)

Resolve target to ALL identifiers before any analysis.

**Steps**:
1. `MyGene_query_genes` - Get initial IDs (Ensembl, UniProt, Entrez)
2. `ensembl_lookup_gene` - Get versioned Ensembl ID (species="homo_sapiens" REQUIRED)
3. `ensembl_get_xrefs` - Cross-references (HGNC, etc.)
4. `OpenTargets_get_target_id_description_by_name` - Verify OT target
5. `ChEMBL_search_targets` - Get ChEMBL target ID
6. `UniProt_get_function_by_accession` - Function summary (returns list of strings)
7. `UniProt_get_alternative_names_by_accession` - Collision detection

**Output**: Table of verified identifiers (Gene Symbol, Ensembl, UniProt, Entrez, ChEMBL, HGNC) plus protein function and target class.

### Phase 1: Disease Association (0-30 pts)

Quantify target-disease association from genetic, literature, and pathway evidence.

**Key tools**:
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` - Disease associations
- `OpenTargets_target_disease_evidence` - Detailed evidence (needs `efoId` + `ensemblId`)
- `OpenTargets_get_evidence_by_datasource` - Evidence by data source
- `gwas_get_snps_for_gene` / `gwas_search_studies` - GWAS evidence
- `gnomad_get_gene_constraints` - Genetic constraint (pLI, LOEUF)
- `PubMed_search_articles` - Literature (returns plain list of dicts)
- `OpenTargets_get_publications_by_target_ensemblID` - OT publications (uses `entityId`)

### Phase 2: Druggability (0-25 pts)

Assess whether the target is amenable to therapeutic intervention.

**Key tools**:
- `OpenTargets_get_target_tractability_by_ensemblID` - Tractability (SM, AB, PR, OC)
- `OpenTargets_get_target_classes_by_ensemblID` - Target classification
- `Pharos_get_target` - TDL: Tclin > Tchem > Tbio > Tdark
- `DGIdb_get_gene_druggability` - Druggability categories
- `alphafold_get_prediction` (param: `qualifier`) / `alphafold_get_summary`
- `ProteinsPlus_predict_binding_sites` - Pocket detection
- `OpenTargets_get_chemical_probes_by_target_ensemblID` - Chemical probes
- `OpenTargets_get_target_enabling_packages_by_ensemblID` - TEPs
- `TCDB_get_transporter` - For SLC/ABC transporter targets: TC classification, family, PDB structures (param: `uniprot_accession`)
- `TCDB_search_by_substrate` - Find transporters by substrate (param: `substrate_name`)

### Phase 3: Chemical Matter (feeds Phase 2 scoring)

Identify existing chemical starting points for target validation.

**Key tools**:
- `ChEMBL_search_targets` + `ChEMBL_get_target_activities` - Bioactivity data (note: `target_chembl_id__exact` with double underscore)
- `BindingDB_get_ligands_by_uniprot` - Binding data (affinity in nM)
- `PubChem_search_assays_by_target_gene` + `PubChem_get_assay_active_compounds` - HTS data
- `OpenTargets_get_associated_drugs_by_target_ensemblID` - Known drugs (`size` REQUIRED)
- `ChEMBL_search_mechanisms` - Drug mechanisms
- `DGIdb_get_gene_info` - Drug-gene interactions

#### Phase 3b: ADMET-AI Deep-Learning Profile (REQUIRED)

For each lead / approved compound identified above, run **all ten ADMET-AI Chemprop-GNN endpoints**. This is a required deliverable of the skill, not optional:

| Endpoint | Tool |
|---|---|
| Physicochemical (MW, logP, HBA/HBD, TPSA) | `ADMETAI_predict_physicochemical_properties` |
| Toxicity (AMES, DILI, LD50, carcinogens, skin sensitizers, ClinTox) | `ADMETAI_predict_toxicity` |
| BBB penetrance | `ADMETAI_predict_BBB_penetrance` |
| CYP interactions (1A2, 2C9, 2C19, 2D6, 3A4) | `ADMETAI_predict_CYP_interactions` |
| Bioavailability (HIA, PAMPA, Caco-2, F20/F30) | `ADMETAI_predict_bioavailability` |
| Clearance & distribution (hepatocyte, microsome, VDss, PPB) | `ADMETAI_predict_clearance_distribution` |
| Nuclear receptor activity (NR-AR, NR-AhR, NR-Aromatase, NR-ER, NR-PPAR-γ) | `ADMETAI_predict_nuclear_receptor_activity` |
| Stress response (SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53) | `ADMETAI_predict_stress_response` |
| Solubility, lipophilicity, hydration | `ADMETAI_predict_solubility_lipophilicity_hydration` |
| Metabolism | `ADMETAI_predict_metabolism` (if available) |

**Required output — ADMET head-to-head table**: when two or more candidate drugs exist (approved or late-stage), produce a side-by-side comparison table with every endpoint in the same row and a "Winner" column flagging which drug is safer. This table is the primary visual of the report and must not be abbreviated or summarized into prose.

**ADMET-AI fallback (IMPORTANT)**: If MCP calls to `ADMETAI_predict_*` fail, return empty, or timeout, run them via Bash + Python SDK instead:
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
for endpoint in ['physicochemical_properties','toxicity','BBB_penetrance','CYP_interactions',
                 'bioavailability','clearance_distribution','nuclear_receptor_activity',
                 'stress_response','solubility_lipophilicity_hydration']:
    r = tu.run_one_function({'name': f'ADMETAI_predict_{endpoint}',
                              'arguments': {'smiles_list': [SMILES_DRUG_A, SMILES_DRUG_B]}})
    print(f'{endpoint}: {r}')
```
This SDK path bypasses the CLI subprocess and avoids segfault issues with torch. Always try MCP first; use this fallback if MCP returns no data.

### Phase 4: Clinical Precedent (0-15 pts)

Assess clinical validation from approved drugs and clinical trials.

**Key tools**:
- `FDA_get_mechanism_of_action_by_drug_name` / `FDA_get_indications_by_drug_name`
- `drugbank_get_targets_by_drug_name_or_drugbank_id` (ALL params required: `query`, `case_sensitive`, `exact_match`, `limit`)
- `search_clinical_trials` (`query_term` REQUIRED)
- `OpenTargets_get_drug_warnings_by_chemblId` / `OpenTargets_get_drug_adverse_events_by_chemblId`

### Phase 5: Safety (0-20 pts)

Identify safety risks from expression, genetics, and known adverse events.

**Key tools**:
- `OpenTargets_get_target_safety_profile_by_ensemblID` - Safety liabilities
- `GTEx_get_median_gene_expression` - Tissue expression (`operation="median"` REQUIRED)
- `HPA_search_genes_by_query` / `HPA_get_comprehensive_gene_details_by_ensembl_id`
- `OpenTargets_get_biological_mouse_models_by_ensemblID` - KO phenotypes
- `FDA_get_adverse_reactions_by_drug_name` / `FDA_get_boxed_warning_info_by_drug_name`
- `OpenTargets_get_target_homologues_by_ensemblID` - Paralog risks

**Critical tissues to check**: heart, liver, kidney, brain, bone marrow.

### Phase 6: Pathway Context

Understand the target's role in biological networks and disease pathways.

**Key tools**:
- `Reactome_map_uniprot_to_pathways` (param: `id`, NOT `uniprot_id`)
- `STRING_get_protein_interactions` (param: `protein_ids` as array, `species=9606`)
- `intact_get_interactions` - Experimental PPI
- `OpenTargets_get_target_gene_ontology_by_ensemblID` - GO terms
- `STRING_functional_enrichment` - Enrichment analysis

**Assess**: pathway redundancy, compensation risk, feedback loops.

### Phase 7: Validation Evidence (0-10 pts)

Assess existing functional validation data.

**Key tools**:
- `DepMap_get_gene_dependencies` - Essentiality (score < -0.5 = essential)
- `PubMed_search_articles` - Search for CRISPR/siRNA/knockout studies
- `CTD_get_gene_diseases` - Gene-disease associations

### Phase 8: Structural Insights

Leverage structural biology for druggability and mechanism understanding. **ALWAYS run both the deep-learning predictors (ESMFold, DoGSite) AND retrieve experimental structures**, even when high-resolution PDB entries already exist. The ML models give an independent pLDDT/druggability score that is a required output of this phase.

**Required tool calls (every run)**:
- `ESMFold_predict_structure` — Meta ESM-2 language-model structure prediction from the UniProt sequence. Report: model pLDDT, worst-residue confidence, RMSD vs. reference PDB if available.
- `alphafold_get_prediction` / `alphafold_get_summary` — DeepMind AlphaFold model + per-residue pLDDT.
- `ProteinsPlus_predict_binding_sites` — DoGSite deep-learning pocket scoring. Report: top 3 pockets with volume, druggability score, residue composition.

**Supporting tools**:
- `UniProt_get_entry_by_accession` - Extract PDB cross-references
- `get_protein_metadata_by_pdb_id` / `pdbe_get_entry_summary` / `pdbe_get_entry_quality`
- `InterPro_get_protein_domains` / `InterPro_get_domain_details` - Domain architecture

### Phase 9: Literature Deep Dive

Comprehensive collision-aware literature analysis.

**Steps**:
1. **Collision detection**: Search `"{gene_symbol}"[Title]` in PubMed; if >20% off-topic, add filters (AND protein OR gene OR receptor)
2. **Publication metrics**: Total count, 5-year trend, drug-focused subset
3. **Key reviews**: `review[pt]` filter in PubMed
4. **Citation metrics**: `openalex_search_works` for impact data
5. **Broader coverage**: `EuropePMC_search_articles`

### Phase 10: Validation Roadmap (Synthesis)

Synthesize all phases into actionable output:
1. **Target Validation Score** (0-100) with component breakdown
2. **Priority Tier** (1-4) assignment
3. **GO/NO-GO Recommendation** with justification
4. **Recommended Validation Experiments**
5. **Tool Compounds for Testing**
6. **Biomarker Strategy**
7. **Key Risks and Mitigations**
8. **Deep-Learning Models Contributing** — explicit attribution table listing every ML predictor invoked during the run and what each produced. Example format:

| Model | Architecture | Contributed |
|---|---|---|
| AlphaFold | DeepMind iterative SE(3)-equivariant Transformer | Full-length 3D model; per-residue pLDDT 91.5 |
| ESMFold | Meta ESM-2 protein language model | Sequence→structure baseline; confidence vs. AlphaFold |
| DoGSite3 | CNN pocket scorer (ProteinsPlus) | Top-3 druggable pockets with volume and drug-score |
| ADMET-AI | Chemprop GNN ensemble (TDC) | 10 endpoints for sotorasib / adagrasib (table above) |
| DynaMut2 | Graph-based mutation stability predictor | ΔΔG for G12C vs. WT |
| DeepGO | Hierarchical GO-term classifier | Molecular-function predictions |

Only list models actually called during the run. This section makes the ML content first-class for a scientific or investor audience.

---

## Report Output

Create file: `[TARGET]_[DISEASE]_validation_report.md`

Use the full template from **REPORT_TEMPLATE.md**. Key sections:
- Executive Summary (score, tier, recommendation, key findings, critical risks)
- Validation Scorecard (all 12 sub-scores with evidence)
- Sections 1-14 covering each phase
- Completeness Checklist (mandatory before finalizing)

Complete the **Completeness Checklist** (in REPORT_TEMPLATE.md) before finalizing to verify all phases were covered, all scores justified, and negative results documented.
