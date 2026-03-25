---
name: tooluniverse-target-research
description: Gather comprehensive biological target intelligence from 9 parallel research paths covering protein info, structure, interactions, pathways, expression, variants, drug interactions, and literature. Features collision-aware searches, evidence grading (T1-T4), explicit Open Targets coverage, and mandatory completeness auditing. Use when users ask about drug targets, proteins, genes, or need target validation, druggability assessment, or comprehensive target profiling.
---

# Comprehensive Target Intelligence Gatherer

Gather complete target intelligence by exploring 9 parallel research paths. Supports targets identified by gene symbol, UniProt accession, Ensembl ID, or gene name.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Tool parameter verification** - Verify params via `get_tool_info` before calling unfamiliar tools
3. **Evidence grading** - Grade all claims by evidence strength (T1-T4). See [EVIDENCE_GRADING.md](EVIDENCE_GRADING.md)
4. **Citation requirements** - Every fact must have inline source attribution
5. **Mandatory completeness** - All sections must exist with data minimums or explicit "No data" notes
6. **Disambiguation first** - Resolve all identifiers before research
7. **Negative results documented** - "No drugs found" is data; empty sections are failures
8. **Collision-aware literature search** - Detect and filter naming collisions
9. **English-first queries** - Always use English terms in tool calls, even if the user writes in another language. Translate gene names, disease names, and search terms to English. Only try original-language terms as a fallback if English returns no results. Respond in the user's language

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

**When NOT to use**: Simple protein lookup, drug-only queries, disease-centric queries, sequence retrieval, structure download -- use specialized skills instead.

---

## Phase 0: Tool Parameter Verification (CRITICAL)

**BEFORE calling ANY tool for the first time**, verify its parameters:

```python
tool_info = tu.tools.get_tool_info(tool_name="Reactome_map_uniprot_to_pathways")
# Reveals: takes `id` not `uniprot_id`
```

### Known Parameter Corrections

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` | `id` |
| `ensembl_get_xrefs` | `gene_id` | `id` |
| `GTEx_get_median_gene_expression` | `gencode_id` only | `gencode_id` + `operation="median"` |
| `OpenTargets_*` | `ensemblID` | `ensemblId` (camelCase) |
| `STRING_get_protein_interactions` | single ID | `protein_ids` (list), `species` |
| `intact_get_interactions` | gene symbol | `identifier` (UniProt accession) |

### GTEx Versioned ID Fallback (CRITICAL)

GTEx often requires versioned Ensembl IDs. If `ENSG00000123456` returns empty, try `ENSG00000123456.{version}` from `ensembl_lookup_gene`.

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show the search process or tool outputs to the user. Instead:
1. **Create the report file FIRST** (`[TARGET]_target_report.md`) with all section headers and `[Researching...]` placeholders. See [REPORT_FORMAT.md](REPORT_FORMAT.md) for template.
2. **Progressively update** each section as data is retrieved.
3. **Methodology in appendix only** - create separate `[TARGET]_methods_appendix.md` if requested.

### 2. Evidence Grading (MANDATORY)

Grade every claim by evidence strength using T1-T4 tiers. See [EVIDENCE_GRADING.md](EVIDENCE_GRADING.md) for tier definitions, required locations, and citation format.

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

Populates baseline data for Sections 5, 6, 8, 9, 10, 11 before specialized queries.

| Endpoint | Report Section | Data Type |
|----------|---------------|-----------|
| `OpenTargets_get_diseases_phenotypes_by_target_ensemblId` | 8 | Diseases/phenotypes |
| `OpenTargets_get_target_tractability_by_ensemblId` | 9 | Druggability assessment |
| `OpenTargets_get_target_safety_profile_by_ensemblId` | 10 | Safety liabilities |
| `OpenTargets_get_target_interactions_by_ensemblId` | 6 | PPI network |
| `OpenTargets_get_target_gene_ontology_by_ensemblId` | 5 | GO annotations |
| `OpenTargets_get_publications_by_target_ensemblId` | 11 | Literature |
| `OpenTargets_get_biological_mouse_models_by_ensemblId` | 8/10 | Mouse KO phenotypes |
| `OpenTargets_get_chemical_probes_by_target_ensemblId` | 9 | Chemical probes |
| `OpenTargets_get_associated_drugs_by_target_ensemblId` | 9 | Known drugs |

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

**Tools**: `UniProt_get_entry_by_accession` (PDB xrefs), `get_protein_metadata_by_pdb_id`, `PDB_search_similar_structures`, `alphafold_get_prediction`, `InterPro_get_protein_domains`, `UniProt_get_ptm_processing_by_accession`

**GPCR targets**: Also query `GPCRdb_get_structures` for active/inactive state data.

**Populates**: Section 4 (Structural Biology)

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the 3-step chain code.

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

GTEx with versioned ID fallback + HPA as backup. For comprehensive HPA data, also query cell line expression comparison.

**Tools**: `GTEx_get_median_gene_expression`, `HPA_get_rna_expression_by_source`, `HPA_get_comprehensive_gene_details_by_ensembl_id`, `HPA_get_subcellular_location`, `HPA_get_cancer_prognostics_by_gene`, `HPA_get_comparative_expression_by_gene_and_cellline`, `CELLxGENE_get_expression_data`

**Populates**: Section 7 (Expression Profile)

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for GTEx fallback and HPA extended expression code.

---

## PATH 6: Variants & Disease

Separate SNVs from CNVs in ClinVar results. Integrate DisGeNET for curated gene-disease association scores.

**Tools**: `gnomad_get_gene_constraints`, `clinvar_search_variants`, `OpenTargets_get_diseases_phenotypes_by_target_ensembl`, `DisGeNET_search_gene`, `civic_get_variants_by_gene`, `cBioPortal_get_mutations`

**Required**: All 4 constraint scores (pLI, LOEUF, missense Z, pRec).

**Populates**: Section 8 (Genetic Variation & Disease)

---

## PATH 7: Druggability & Target Validation

Comprehensive druggability assessment including TDL classification, binding data, screening data, and essentiality.

**Tools**: `OpenTargets_get_target_tractability_by_ensemblID`, `DGIdb_get_gene_druggability`, `DGIdb_get_drug_gene_interactions`, `ChEMBL_search_targets`, `ChEMBL_get_target_activities`, `Pharos_get_target`, `BindingDB_get_ligands_by_uniprot`, `PubChem_search_assays_by_target_gene`, `DepMap_get_gene_dependencies`, `OpenTargets_get_target_safety_profile_by_ensemblID`, `OpenTargets_get_biological_mouse_models_by_ensemblID`

**GPCR targets**: Also query `GPCRdb_get_ligands`.

**Populates**: Sections 9 (Druggability), 10 (Safety), 12 (Competitive Landscape)

### Key Data Sources for Druggability

| Source | What It Provides |
|--------|-----------------|
| Pharos TDL | Tclin/Tchem/Tbio/Tdark classification |
| BindingDB | Experimental Ki/IC50/Kd values |
| PubChem BioAssay | HTS screening hits and dose-response |
| DepMap | CRISPR essentiality across cancer cell lines |
| ChEMBL | Bioactivity records and compound counts |

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for detailed code and [REFERENCE.md](REFERENCE.md) for complete tool parameter tables.

---

## PATH 8: Literature & Research (Collision-Aware)

1. **Detect collisions** - Check if gene symbol has non-biological meanings
2. **Build seed queries** - Symbol in title with bio context, full name, UniProt accession
3. **Apply collision filter** - Add NOT terms for off-topic meanings
4. **Expand via citations** - For sparse targets (<30 papers), use citation network
5. **Classify by evidence tier** - T1-T4 based on title/abstract keywords

**Tools**: `PubMed_search_articles`, `PubMed_get_related`, `EuropePMC_search_articles`, `EuropePMC_get_citations`, `PubTator3_LiteratureSearch`, `OpenTargets_get_publications_by_target_ensemblID`

**Populates**: Section 11 (Literature & Research Landscape)

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for collision-aware search code.

---

## Retry Logic & Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `ChEMBL_get_target_activities` | `GtoPdb_search_ligands` | `OpenTargets drugs` |
| `intact_get_interactions` | `STRING_get_protein_interactions` | `OpenTargets interactions` |
| `GO_get_annotations_for_gene` | `OpenTargets GO` | `MyGene GO` |
| `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` | Document as unavailable |
| `gnomad_get_gene_constraints` | `OpenTargets constraint` | - |
| `DGIdb_get_drug_gene_interactions` | `OpenTargets drugs` | `GtoPdb` |

**NEVER silently skip failed tools.** Always document failures and fallbacks in the report.

---

## Completeness Audit (REQUIRED before finalizing)

Run the checklist in [EVIDENCE_GRADING.md](EVIDENCE_GRADING.md) before finalizing any report:
- Data minimums met for PPIs, expression, diseases, constraints, druggability
- Negative results documented explicitly
- T1-T4 grades in Executive Summary, Disease Associations, Key Papers, Recommendations
- Every data point has source attribution

---

## Report Template

Create `[TARGET]_target_report.md` with all 15 sections initialized. See [REPORT_FORMAT.md](REPORT_FORMAT.md) for the full template with section headers, table formats, and completeness checklist.

Initial file structure:
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

## Quick Reference: Tool Parameters

| Tool | Parameter | Notes |
|------|-----------|-------|
| `Reactome_map_uniprot_to_pathways` | `id` | NOT `uniprot_id` |
| `ensembl_get_xrefs` | `id` | NOT `gene_id` |
| `GTEx_get_median_gene_expression` | `gencode_id`, `operation` | Try versioned ID if empty |
| `OpenTargets_*` | `ensemblId` | camelCase, not `ensemblID` |
| `STRING_get_protein_interactions` | `protein_ids`, `species` | List format for IDs |
| `intact_get_interactions` | `identifier` | UniProt accession |

---

## Reference Files

| File | Contents |
|------|----------|
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Detailed code for identifier resolution, GPCR detection, each PATH implementation, retry logic |
| [EVIDENCE_GRADING.md](EVIDENCE_GRADING.md) | T1-T4 tier definitions, citation format, completeness audit checklist, data minimums |
| [REPORT_FORMAT.md](REPORT_FORMAT.md) | Full report template with all 15 sections, table formats, section-specific guidance |
| [REFERENCE.md](REFERENCE.md) | Complete tool reference (225+ tools) organized by category with parameters |
| [EXAMPLES.md](EXAMPLES.md) | Worked examples: EGFR full profile, KRAS druggability, target comparison, CDK4 validation, Alzheimer's targets |
