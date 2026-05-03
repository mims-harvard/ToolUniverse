---
name: tooluniverse-target-research
description: Gather comprehensive biological target intelligence from 9 parallel research paths covering protein info, structure, interactions, pathways, expression, variants, drug interactions, and literature. Features collision-aware searches, evidence grading (T1-T4), explicit Open Targets coverage, and mandatory completeness auditing. Use when users ask about drug targets, proteins, genes, or need target validation, druggability assessment, or comprehensive target profiling.
---

# Comprehensive Target Intelligence Gatherer

Gather complete target intelligence by exploring 9 parallel research paths. Supports targets identified by gene symbol, UniProt accession, Ensembl ID, or gene name.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Tool parameter verification** - Verify params via `get_tool_info` before calling unfamiliar tools
3. **Evidence grading** - Grade all claims by evidence strength (T1-T4)
4. **Citation requirements** - Every fact must have inline source attribution
5. **Mandatory completeness** - All sections must exist with data minimums or explicit "No data" notes
6. **Disambiguation first** - Resolve all identifiers before research
7. **Negative results documented** - "No drugs found" is data; empty sections are failures
8. **Collision-aware literature search** - Detect and filter naming collisions
9. **English-first queries** - Always use English terms in tool calls, even if the user writes in another language. Translate gene names, disease names, and search terms to English. Only try original-language terms as a fallback if English returns no results. Respond in the user's language

---

## LOOK UP, DON'T GUESS

When asked about a specific protein or gene target, look it up in UniProt/Ensembl/OpenTargets BEFORE reasoning about it. Verify the gene name, function, and disease associations from databases. When you're not sure about a fact, your first instinct should be to SEARCH for it using tools, not to reason harder from memory.

---

## When to Use This Skill

Apply when users:
- Ask about a drug target, protein, or gene
- Need target validation or assessment
- Request druggability analysis
- Want comprehensive target profiling
- Ask "what do we know about [target]?"
- Need target-disease associations
- Request safety profile for a target

**When NOT to use**: Simple protein lookup, drug-only queries, disease-centric queries, sequence retrieval, structure download — use specialized skills instead.

---

## Target Evaluation Reasoning Framework

Evaluating a drug target requires reasoning across four interconnected questions. Answer all four before forming a recommendation.

**1. Is there genetic evidence linking this target to the disease?**
Genetic evidence is the strongest predictor of drug success — targets with human genetic support have approximately twice the clinical success rate as those without (Nelson et al. 2015). Ask: Are there GWAS associations connecting this gene to the disease? Do rare loss-of-function or gain-of-function variants cause or protect against the disease? Does the mouse knockout phenotype match the human disease (from OpenTargets mouse models)? OpenTargets assigns genetic evidence scores; a score > 0.7 indicates strong support. ClinVar rare variant evidence and DisGeNET curated gene-disease association scores add complementary layers. A target with no genetic link to the disease of interest carries a fundamental validation risk that cannot be resolved by downstream data.

**2. Is the target druggable?**
Druggability has two components: structural accessibility and prior chemical matter. Structural accessibility means the target has a binding pocket where a small molecule or biologic can engage — surface-exposed receptors, enzymes with well-defined active sites, and protein-protein interaction interfaces with hot spots are tractable. Intrinsically disordered proteins and transcription factors with flat, featureless binding surfaces are typically harder. Pharos TDL classification provides a tiered assessment: Tclin (approved drug), Tchem (known active compounds), Tbio (biological function known but no drugs), Tdark (poorly characterized). If ChEMBL or BindingDB have compounds with IC50 < 1μM, the target is chemically tractable. Chemical probes (from OpenTargets chemical probes endpoint) confirm a target can be modulated, which is distinct from drug-like compounds. For GPCRs, check GPCRdb for curated agonists and antagonists.

**3. Is the target safe to modulate?**
Safety concerns arise from two sources. First, on-target effects: if the target is essential in normal tissues (mouse KO is lethal, or gnomAD pLI is high / LOEUF is low), full inhibition will produce toxicity — the question becomes whether a partial agonist or tissue-targeted delivery can provide a therapeutic window. Second, off-target effects: does the gene have family members that could be inadvertently hit? The OpenTargets safety profile aggregates known toxicity annotations, and DepMap essentiality scores tell you which cancer cell lines require this gene for survival (useful but not directly translatable to normal tissues). Expression specificity matters: a target expressed only in the disease-relevant tissue is far safer than one expressed ubiquitously in critical organs (heart, kidney, brain).

**4. What is the competitive landscape?**
A target with approved drugs may already be validated but competitive; a target with clinical-stage programs from competitors establishes feasibility while creating IP barriers. An entirely novel target with no drug history requires more extensive internal validation. Assess: number of ChEMBL bioactivity records (chemical matter depth), approved drugs from OpenTargets drug associations, and literature activity trends (recent paper count and key research groups). A dark target (Tdark) with strong genetic evidence but no chemical matter is a high-risk, high-reward opportunity.

**Synthesizing the four dimensions**: The ideal target has strong genetic evidence (GWAS + rare variant), a tractable binding site (Tclin or Tchem), acceptable safety profile (tissue-specific expression, non-lethal KO), and manageable competition. Gaps in any dimension represent validation tasks, not disqualifiers — but they must be acknowledged. A target with perfect druggability but no genetic link to disease is a tractability exercise, not a validated therapeutic hypothesis.

---

## Phase 0: Tool Parameter Verification (CRITICAL)

**BEFORE calling ANY tool for the first time**, verify its parameters:

```python
tool_info = tu.tools.get_tool_info(tool_name="Reactome_map_uniprot_to_pathways")
# Reveals: takes `id` not `uniprot_id`
```

Known parameter corrections:
- `Reactome_map_uniprot_to_pathways`: param is `id` (not `uniprot_id`)
- `ensembl_get_xrefs`: param is `id` (not `gene_id`)
- `GTEx_get_median_gene_expression`: requires `gencode_id` + `operation="median"`; try versioned Ensembl ID if empty
- `OpenTargets_*`: param is `ensemblId` (camelCase, not `ensemblID`)
- `STRING_get_protein_interactions`: takes `protein_ids` (list) + `species`
- `intact_get_interactions`: takes `identifier` (UniProt accession, not gene symbol)

---

## Critical Workflow Requirements

**Report-First (MANDATORY)**: Create `[TARGET]_target_report.md` with all section headers and `[Researching...]` placeholders before starting research. Update progressively. Do not show raw tool outputs to the user.

**Evidence Grading (MANDATORY)**: Grade every claim T1-T4. T1 = clinical/genetic data; T2 = curated databases or multiple studies; T3 = computational or single study; T4 = annotation or catalog entry.

---

## Core Strategy: 9 Research Paths

```
Target Query (e.g., "EGFR" or "P00533")
|
+- IDENTIFIER RESOLUTION (always first)
|   +- Check if GPCR -> GPCRdb_get_protein
|
+- PATH 0: Open Targets Foundation (ALWAYS FIRST - fills gaps in all other paths)
|
+- PATH 1: Core Identity (names, IDs, sequence, organism)
|   +- InterProScan_scan_sequence for novel domain prediction
+- PATH 2: Structure & Domains (3D structure, domains, binding sites)
|   +- If GPCR: GPCRdb_get_structures (active/inactive states)
+- PATH 3: Function & Pathways (GO terms, pathways, biological role)
+- PATH 4: Protein Interactions (PPI network, complexes)
+- PATH 5: Expression Profile (tissue expression, single-cell)
+- PATH 6: Variants & Disease (mutations, clinical significance)
|   +- DisGeNET_search_gene for curated gene-disease associations
+- PATH 7: Drug Interactions (known drugs, druggability, safety)
|   +- Pharos_get_target for TDL classification (Tclin/Tchem/Tbio/Tdark)
|   +- BindingDB_get_ligands_by_uniprot for known ligands
|   +- PubChem_search_assays_by_target_gene for HTS data
|   +- If GPCR: GPCRdb_get_ligands (curated agonists/antagonists)
|   +- DepMap_get_gene_dependencies for target essentiality
+- PATH 8: Literature & Research (publications, trends)
```

For detailed code implementations of each path, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

---

## Identifier Resolution (Phase 1)

Resolve ALL identifiers before any research path. Required IDs:
- **UniProt accession** (for protein data, structure, interactions)
- **Ensembl gene ID** + versioned ID (for Open Targets, GTEx)
- **Gene symbol** (for DGIdb, gnomAD, literature)
- **Entrez gene ID** (for KEGG, MyGene)
- **ChEMBL target ID** (for bioactivity)
- **Synonyms/full name** (for collision-aware literature search)

After resolution, check if target is a GPCR via `GPCRdb_get_protein`. See [IMPLEMENTATION.md](IMPLEMENTATION.md) for resolution and GPCR detection code.

---

## PATH 0: Open Targets Foundation (ALWAYS FIRST)

Run OpenTargets endpoints first to populate baseline data before specialized queries:
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` → disease associations (Section 8)
- `OpenTargets_get_target_tractability_by_ensemblID` → druggability assessment (Section 9)
- `OpenTargets_get_target_safety_profile_by_ensemblID` → safety liabilities (Section 10)
- `OpenTargets_get_target_interactions_by_ensemblID` → PPI network (Section 6)
- `OpenTargets_get_target_gene_ontology_by_ensemblID` → GO annotations (Section 5)
- `OpenTargets_get_publications_by_target_ensemblID` → literature (Section 11)
- `OpenTargets_get_biological_mouse_models_by_ensemblID` → mouse KO phenotypes (Sections 8/10)
- `OpenTargets_get_chemical_probes_by_target_ensemblID` → chemical probes (Section 9)
- `OpenTargets_get_associated_drugs_by_target_ensemblID` → known drugs (Section 9)

---

## PATH 1: Core Identity

**Tools**: `UniProt_get_entry_by_accession`, `UniProt_get_function_by_accession`, `UniProt_get_recommended_name_by_accession`, `UniProt_get_alternative_names_by_accession`, `UniProt_get_subcellular_location_by_accession`, `MyGene_get_gene_annotation`

**Populates**: Sections 2 (Identifiers), 3 (Basic Information)

---

## PATH 2: Structure & Domains

Use 3-step structure search chain (do NOT rely solely on PDB text search):
1. **UniProt PDB cross-references** (most reliable)
2. **Sequence-based PDB search** (catches missing annotations)
3. **Domain-based search** (for multi-domain proteins)
4. **AlphaFold** (always check)

**Tools**: `UniProt_get_entry_by_accession` (PDB xrefs), `RCSBData_get_entry`, `PDB_search_similar_structures`, `alphafold_get_prediction`, `InterPro_get_protein_domains`, `UniProt_get_ptm_processing_by_accession`

**GPCR targets**: Also query `GPCRdb_get_structures` for active/inactive state data.

**Populates**: Section 4 (Structural Biology)

---

## PATH 3: Function & Pathways

**Tools**: `GO_get_annotations_for_gene`, `Reactome_map_uniprot_to_pathways`, `kegg_get_gene_info`, `WikiPathways_search`, `enrichr_gene_enrichment_analysis`

**Populates**: Section 5 (Function & Pathways)

---

## PATH 4: Protein Interactions

**Tools**: `STRING_get_protein_interactions`, `intact_get_interactions`, `intact_get_complex_details`, `BioGRID_get_interactions`, `HPA_get_protein_interactions_by_gene`

**Minimum**: 20 interactors OR documented explanation.

**Populates**: Section 6 (Protein-Protein Interactions)

---

## PATH 5: Expression Profile

GTEx with versioned ID fallback + HPA as backup.

**Tools**: `GTEx_get_median_gene_expression`, `HPA_get_rna_expression_by_source`, `HPA_get_comprehensive_gene_details_by_ensembl_id`, `HPA_get_subcellular_location`, `HPA_get_cancer_prognostics_by_gene`, `HPA_get_comparative_expression_by_gene_and_cellline`, `CELLxGENE_get_expression_data`

**Reasoning**: Expression specificity directly informs safety. Note whether expression is enriched in the disease-relevant tissue vs. critical organs. Ubiquitous essential expression narrows the therapeutic window.

**Populates**: Section 7 (Expression Profile)

---

## PATH 6: Variants & Disease

Separate SNVs from CNVs in ClinVar results. Integrate DisGeNET for curated gene-disease association scores.

**Tools**: `gnomad_get_gene_constraints`, `ClinVar_search_variants`, `OpenTargets_get_diseases_phenotypes_by_target_ensembl`, `DisGeNET_search_gene`, `civic_get_variants_by_gene`, `cBioPortal_get_mutations`

**Required constraint scores**: pLI (probability of loss-of-function intolerance), LOEUF (loss-of-function observed/expected upper bound), missense Z-score, pRec (recessive probability). High pLI (> 0.9) or low LOEUF (< 0.35) indicates the gene is intolerant to loss-of-function — a major safety flag for inhibitory therapeutic strategies.

**Populates**: Section 8 (Genetic Variation & Disease)

---

## PATH 7: Druggability & Target Validation

**Tools**: `OpenTargets_get_target_tractability_by_ensemblID`, `DGIdb_get_gene_druggability`, `DGIdb_get_drug_gene_interactions`, `ChEMBL_search_targets`, `ChEMBL_get_target_activities`, `Pharos_get_target`, `BindingDB_get_ligands_by_uniprot`, `PubChem_search_assays_by_target_gene`, `DepMap_get_gene_dependencies`, `OpenTargets_get_target_safety_profile_by_ensemblID`, `OpenTargets_get_biological_mouse_models_by_ensemblID`

**GPCR targets**: Also query `GPCRdb_get_ligands`.

**Reasoning**: Pharos TDL tells you where the target sits in the knowledge landscape. BindingDB Ki/IC50/Kd values tell you whether the target has been demonstrated tractable experimentally. DepMap essentiality tells you whether cancer cells require this gene (proxy for toxicity risk, not a definitive answer).

**Populates**: Sections 9 (Druggability), 10 (Safety), 12 (Competitive Landscape)

---

## PATH 8: Literature & Research (Collision-Aware)

1. **Detect collisions** - Check if gene symbol has non-biological meanings
2. **Build seed queries** - Symbol in title with bio context, full name, UniProt accession
3. **Apply collision filter** - Add NOT terms for off-topic meanings
4. **Expand via citations** - For sparse targets (<30 papers), use citation network
5. **Classify by evidence tier** - T1-T4 based on title/abstract keywords

**Tools**: `PubMed_search_articles`, `PubMed_get_related`, `EuropePMC_search_articles`, `EuropePMC_get_citations`, `PubTator3_LiteratureSearch`, `OpenTargets_get_publications_by_target_ensemblID`

**Populates**: Section 11 (Literature & Research Landscape)

---

## Retry Logic & Fallback Chains

- `ChEMBL_get_target_activities` fails → `GtoPdb_search_ligands` → `OpenTargets drugs`
- `intact_get_interactions` fails → `STRING_get_protein_interactions` → `OpenTargets interactions`
- `GO_get_annotations_for_gene` fails → `OpenTargets GO` → `MyGene GO`
- `GTEx_get_median_gene_expression` fails → `HPA_get_rna_expression_by_source` → document as unavailable
- `gnomad_get_gene_constraints` fails → `OpenTargets constraint` endpoint
- `DGIdb_get_drug_gene_interactions` fails → `OpenTargets drugs` → `GtoPdb_search_ligands`

**NEVER silently skip failed tools.** Always document failures and fallbacks in the report.

---

## Completeness Audit (REQUIRED before finalizing)

Before finalizing any report:
- Data minimums met for PPIs, expression, diseases, constraints, druggability
- Negative results documented explicitly
- T1-T4 grades in Executive Summary, Disease Associations, Key Papers, Recommendations
- Every data point has source attribution

---

## Report Template

Create `[TARGET]_target_report.md` with all 15 sections initialized. See [REPORT_FORMAT.md](REPORT_FORMAT.md) for the full template.

```
## 1. Executive Summary          ## 9. Druggability & Pharmacology
## 2. Target Identifiers         ## 10. Safety Profile
## 3. Basic Information          ## 11. Literature & Research
## 4. Structural Biology         ## 12. Competitive Landscape
## 5. Function & Pathways        ## 13. Summary & Recommendations
## 6. Protein-Protein Interactions ## 14. Data Sources & Methodology
## 7. Expression Profile         ## 15. Data Gaps & Limitations
## 8. Genetic Variation & Disease
```

---

## Synthesis: Target Assessment Framework

After completing all 9 PATHs, synthesize findings into a GO/NO-GO recommendation in the Executive Summary. Score each dimension:

- **Genetic evidence**: Strong (GWAS + rare variant + functional) / Moderate (GWAS or rare variant only) / Weak (expression change only) / None
- **Disease association**: Based on OpenTargets score (> 0.7 strong, 0.3-0.7 moderate, < 0.3 weak)
- **Druggability**: Approved drug exists / Tractable (known binding site, chemical probes) / Predicted tractable (structural pocket) / Undruggable
- **Safety**: Non-essential gene (viable KO, low pLI) / Essential with phenotype / Lethal KO or high pLI / Known toxicity target
- **Selectivity**: Disease-specific or enriched expression / Ubiquitous / Expressed in critical organs
- **Structural data**: High-res crystal with ligand / AlphaFold confident (pLDDT > 80) / Homology model / No structural info

Total score guides recommendation: strong target (all dimensions favorable), promising with defined validation tasks (2-3 gaps), speculative (multiple critical gaps), or deprioritize (no genetic link and poor druggability).

---

## Reference Files

| File | Contents |
|------|----------|
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Detailed code for identifier resolution, GPCR detection, each PATH implementation, retry logic |
| [EVIDENCE_GRADING.md](EVIDENCE_GRADING.md) | T1-T4 tier definitions, citation format, completeness audit checklist, data minimums |
| [REPORT_FORMAT.md](REPORT_FORMAT.md) | Full report template with all 15 sections, table formats, section-specific guidance |
| [REFERENCE.md](REFERENCE.md) | Complete tool reference (225+ tools) organized by category with parameters |
| [EXAMPLES.md](EXAMPLES.md) | Worked examples: EGFR full profile, KRAS druggability, target comparison, CDK4 validation, Alzheimer's targets |
