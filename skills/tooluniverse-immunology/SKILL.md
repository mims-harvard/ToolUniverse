---
name: tooluniverse-immunology
description: Immunology research workflows using ToolUniverse tools. Covers antibody-antigen structural analysis (SAbDab, TheraSAbDab), immune protein interactions (IntAct, BioGRID), epitope and T-cell/B-cell assay data (IEDB), immunoglobulin gene databases (IMGT), cytokine/receptor signaling (OpenTargets, GWAS), clinical safety data for immune diseases (FAERS, clinical trials), autoimmune disease genetics (Orphanet), and immune pathway analysis (KEGG, Reactome). Use when researchers ask about antibody targets, immune signaling networks, autoimmune genetics, immunotherapy safety, epitope discovery, or immune pathway enrichment.
---

# Immunology Research Skill

Multi-database immunology analysis covering antibody structures, immune protein interactions, epitope databases, autoimmune genetics, immunotherapy safety, and immune pathway analysis.

**KEY PRINCIPLES**:
1. **Multi-layer evidence** - Cross-reference structural, genetic, interaction, and clinical data
2. **Source-referenced** - Cite the database for every claim
3. **Actionable** - Prioritize findings by clinical or experimental relevance
4. **Immune-specific** - Use immunology-specific databases (IEDB, IMGT, SAbDab) before generic ones
5. **English-first queries** - Always use English gene/protein names in tool calls

---

## When to Use

Apply when user asks about:
- Antibody structure, binding, or therapeutic antibody research
- Immune protein-protein interactions (cytokines, receptors, signaling)
- Epitope discovery, T-cell/B-cell assay data
- Immunoglobulin gene families (V/D/J segments)
- Autoimmune or immune-mediated disease genetics
- Immunotherapy drug safety signals
- Immune signaling pathway enrichment
- Tumor immune microenvironment estimation

---

## Tool Inventory

### Antibody / Structural (SAbDab + TheraSAbDab)

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `SAbDab_get_structure` | `pdb_id` (str, e.g. "1AHW") | Structure details, chain info, download URL |
| `SAbDab_get_summary` | `pdb_id` (str) | Summary data for an antibody PDB entry |
| `SAbDab_search_structures` | `query` (str, e.g. "PD-1") | Browse URL only (no JSON results) |
| `TheraSAbDab_search_therapeutics` | `query` (str, e.g. "pembrolizumab") | Therapeutic antibody info: INN, target, format, phase |
| `TheraSAbDab_search_by_target` | `target` (str, e.g. "HER2") | All therapeutic antibodies for a target antigen |
| `TheraSAbDab_get_all_therapeutics` | (none) | Full list of all therapeutic antibodies |

> **Note**: `SAbDab_search_structures` returns a browse URL, not structured data. Use `SAbDab_get_structure` with a known PDB ID for structured results.

### Epitope and Immune Assays (IEDB)

**Search tools** (all accept `limit`, `offset`, `filters` dict for PostgREST queries):

| Tool | Extra Parameters | Returns |
|------|-----------------|---------|
| `iedb_search_epitopes` | `sequence_contains` (str), `structure_type` (str) | Epitope records with structure_id |
| `iedb_search_tcell_assays` | `sequence_contains` (str), `mhc_class` (str), `qualitative_measure` (str) | T-cell assay records |
| `iedb_search_bcell` | (filters only) | B-cell assay records |
| `iedb_search_mhc` | (filters only) | MHC binding/ligand records |
| `iedb_search_antigens` | (filters only) | Source antigen records |
| `iedb_search_tcr_sequences` | (filters only) | TCR sequence records |
| `iedb_search_bcr_sequences` | (filters only) | BCR sequence records |

**Detail tools** (drill down by `structure_id` or `epitope_id`): `iedb_get_epitope_antigens`, `iedb_get_epitope_mhc`, `iedb_get_epitope_tcell_assays`, `iedb_get_epitope_references`.

### Immunoglobulin Genes (IMGT)

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `IMGT_search_genes` | `gene_name` (str, e.g. "IGHV1-2") | Gene type catalog, search/reference URLs |
| `IMGT_get_gene_info` | `gene_name` (str) | Detailed gene information |
| `IMGT_get_sequence` | `gene_name` (str) | Nucleotide/amino acid sequences |

### Immune Protein Interactions

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `intact_get_interaction_network` | `identifier` (str, gene symbol like "IL6"), `limit` (int) | Interaction partners with descriptions |
| `intact_search_interactions` | `query` (str), `limit` (int) | Search interactions by keyword |
| `intact_get_interactor` | `interactor_id` (str, UniProt ID) | Details for a specific interactor |
| `BioGRID_get_interactions` | `gene_names` (list, e.g. `["CD274"]`), `organism` (str "9606"), `limit` (int) | PPI data: symbols, experimental system, throughput |
| `BioGRID_get_chemical_interactions` | `gene_names` (list), `chemical_names` (list), `organism` (int), `limit` (int) | Drug-gene interaction data |

### Cytokine/Receptor Signaling (OpenTargets + GWAS)

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `OpenTargets_get_target_interactions_by_ensemblID` | `ensemblId` (str), `size` (int) | Protein-protein interactions |
| `OpenTargets_get_target_gene_ontology_by_ensemblID` | `ensemblId` (str) | GO annotations for immune function |
| `OpenTargets_get_associated_diseases_by_drug_chemblId` | `chemblId` (str) | Diseases targeted by an immunotherapy drug |
| `OpenTargets_get_target_safety_profile_by_ensemblID` | `ensemblId` (str) | Safety liabilities for immune targets |
| `gwas_search_associations` | `query` (str, e.g. "rheumatoid arthritis") | GWAS hits: p-values, effect sizes, risk alleles |
| `gwas_get_variants_for_trait` | `efo_trait` (str) | Variants associated with an immune trait |
| `gwas_get_snps_for_gene` | `mapped_gene` (str, e.g. "PDCD1") | GWAS SNPs mapped to an immune gene |

> **Resolve gene symbols to Ensembl IDs** with `OpenTargets_get_target_id_description_by_name` before calling ensemblId-based tools.

### Clinical / Safety (FAERS + Clinical Trials)

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `FAERS_calculate_disproportionality` | `drug_name` (str), `adverse_event` (str) | PRR, ROR, IC with signal detection |
| `FAERS_filter_serious_events` | `drug_name` (str), `seriousness_type` (str) | Serious AE reports by category |
| `FAERS_stratify_by_demographics` | `drug_name` (str), `adverse_event` (str, optional), `stratify_by` (str: sex/age/country) | Demographic breakdown |
| `FAERS_compare_drugs` | `drug1` (str), `drug2` (str), `adverse_event` (str) | Side-by-side safety comparison |
| `search_clinical_trials` | `condition` (str), `intervention` (str), `query_term` (str), `pageSize` (int) | Trial records: NCT IDs, status, phases |

### Autoimmune Disease Genetics (Orphanet)

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `Orphanet_search_diseases` | `query` (str, e.g. "lupus") | Disease list with ORPHAcodes |
| `Orphanet_get_genes` | `orpha_code` (int) | Associated genes for a rare immune disease |
| `Orphanet_get_phenotypes` | `orpha_code` (int) | HPO phenotype terms |
| `Orphanet_get_epidemiology` | `orpha_code` (int) | Prevalence and incidence data |
| `Orphanet_get_gene_diseases` | `gene_symbol` (str) | Diseases associated with an immune gene |
| `Orphanet_get_natural_history` | `orpha_code` (int) | Age of onset, inheritance pattern |

### Immune Pathway Analysis (KEGG + Reactome)

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `kegg_search_pathway` | `keyword` (str, e.g. "cytokine") | Matching KEGG pathway IDs and names |
| `KEGG_get_disease` | `disease_id` (str, e.g. "H00080") | Disease entry with gene associations |
| `KEGG_get_disease_genes` | `disease_id` (str) | Gene list for a KEGG disease |
| `KEGG_get_pathway_genes` | `pathway_id` (str, e.g. "hsa04060") | All genes in a KEGG pathway |
| `Reactome_get_pathway` | `stId` (str, e.g. "R-HSA-168256") | Pathway details (R-HSA-168256 = Immune System) |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (str, space-separated gene/protein IDs) | Enriched pathways with p-values |
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` (str) | Pathways containing a protein |

> **Reactome param**: `stId` is required (NOT `pathway_id`). Use "R-HSA-" prefix for human pathways.
> **ReactomeAnalysis**: `identifiers` is a space-separated STRING, not an array.

### Tumor Immune Microenvironment

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `TIMER2_immune_estimation` | `operation` (str), `cancer` (str, e.g. "BRCA"), `gene` (str) | Immune cell infiltration estimates (B, CD4+, CD8+, neutrophil, macrophage, DC) |

---

## Workflow 1: Antibody Target Research

**Goal**: Characterize a therapeutic antibody target (e.g., PD-1, HER2, CD20).

**Steps**:

1. **Identify therapeutic antibodies** targeting the antigen
   - `TheraSAbDab_search_by_target(target="PD-1")` -- approved/clinical antibodies
   - `TheraSAbDab_search_therapeutics(query="pembrolizumab")` -- specific antibody lookup

2. **Get structural data** for antibody-antigen complexes
   - `SAbDab_get_structure(pdb_id="5DK3")` -- PDB structure details
   - `SAbDab_get_summary(pdb_id="5DK3")` -- summary chain/CDR info

3. **Explore known epitopes** on the target
   - `iedb_search_epitopes(sequence_contains="SFVLNWYRMSPSNQTDKLAAFPEDR", limit=10)` -- peptide epitopes
   - `iedb_search_tcell_assays(sequence_contains="SFVLNWYRMSPSNQTDKLAAFPEDR", limit=10)` -- T-cell reactivity

4. **Map interaction partners** of the target
   - `intact_get_interaction_network(identifier="Q9NZQ7", limit=20)` -- PPI network (use UniProt accession, not gene symbol)
   - `BioGRID_get_interactions(gene_names=["PDCD1"], organism="9606", limit=20)` -- additional PPIs

5. **Assess clinical safety** of drugs targeting it
   - `FAERS_calculate_disproportionality(drug_name="pembrolizumab", adverse_event="colitis")`
   - `search_clinical_trials(condition="melanoma", intervention="pembrolizumab", pageSize=5)`

---

## Workflow 2: Autoimmune Disease Genetics

**Goal**: Characterize genetic basis of an autoimmune disease (e.g., SLE, RA, MS).

**Steps**:

1. **Find disease entry and genes**
   - `Orphanet_search_diseases(query="systemic lupus erythematosus")` -- get ORPHAcode (536)
   - `Orphanet_get_genes(orpha_code=536)` -- associated genes
   - `Orphanet_get_phenotypes(orpha_code=536)` -- HPO phenotypes
   - `Orphanet_get_natural_history(orpha_code=536)` -- onset, inheritance

2. **GWAS evidence for the disease**
   - `gwas_search_associations(query="systemic lupus erythematosus")` -- top GWAS hits
   - `gwas_get_snps_for_gene(gene_symbol="STAT4")` -- SNPs in a candidate gene

3. **KEGG disease and pathway context**
   - `KEGG_get_disease(disease_id="H00080")` -- SLE in KEGG (category: Immune system disease)
   - `kegg_search_pathway(keyword="lupus")` -- related pathways
   - `KEGG_get_pathway_genes(pathway_id="hsa05322")` -- genes in SLE pathway

4. **Immune pathway enrichment** of disease genes
   - `ReactomeAnalysis_pathway_enrichment(identifiers="STAT4 IRF5 ITGAM TNFSF4 BLK")` -- pathway enrichment
   - `Reactome_get_pathway(stId="R-HSA-168256")` -- Immune System root pathway

5. **Clinical trials** for the disease
   - `search_clinical_trials(condition="systemic lupus erythematosus", pageSize=10)`

---

## Workflow 3: Immunotherapy Drug Safety Comparison

**Goal**: Compare safety profiles of immunotherapy drugs (e.g., pembrolizumab vs nivolumab).

**Steps**:

1. **Head-to-head adverse event comparison**
   - `FAERS_compare_drugs(drug1="pembrolizumab", drug2="nivolumab", adverse_event="pneumonitis")`
   - `FAERS_compare_drugs(drug1="pembrolizumab", drug2="nivolumab", adverse_event="colitis")`

2. **Serious event profiling**
   - `FAERS_filter_serious_events(drug_name="pembrolizumab", seriousness_type="death")`
   - `FAERS_filter_serious_events(drug_name="nivolumab", seriousness_type="death")`

3. **Demographic stratification**
   - `FAERS_stratify_by_demographics(drug_name="pembrolizumab", stratify_by="age")`
   - `FAERS_stratify_by_demographics(drug_name="nivolumab", stratify_by="age")`

4. **Target safety profile** via OpenTargets
   - Resolve target: `OpenTargets_get_target_id_description_by_name(targetName="PDCD1")` -- get Ensembl ID
   - `OpenTargets_get_target_safety_profile_by_ensemblID(ensemblId="ENSG00000188389")`

5. **Active clinical trials** for both drugs
   - `search_clinical_trials(intervention="pembrolizumab", pageSize=5)`
   - `search_clinical_trials(intervention="nivolumab", pageSize=5)`

---

## Parameter Gotchas

| Issue | Wrong | Correct |
|-------|-------|---------|
| Reactome pathway ID param | `pathway_id="R-HSA-168256"` | `stId="R-HSA-168256"` |
| ReactomeAnalysis identifiers | `identifiers=["STAT4","IRF5"]` | `identifiers="STAT4 IRF5"` (space-separated string) |
| OpenTargets target lookup | `ensemblId="IL6"` | First resolve: `OpenTargets_get_target_id_description_by_name(targetName="IL6")` |
| OpenTargets target lookup param | `query="IL6"` | Correct param is `targetName="IL6"` (not `query`) |
| FAERS drug name | `drug_name="Keytruda"` | `drug_name="pembrolizumab"` (use generic names) |
| IntAct identifier | `identifier="CD274"` | `identifier="Q9NZQ7"` (UniProt accession required; gene symbols return 0 results) |
| BioGRID organism | `organism="human"` | `organism="9606"` (string NCBI taxon ID) |
| BioGRID interactions param | `gene_name="CD274"` | `gene_names=["CD274"]` (list, not string) |
| TheraSAbDab target search | `TheraSAbDab_search_by_target(target="PD-1")` returns 0 | Use `TheraSAbDab_search_therapeutics(query="pembrolizumab")` by drug name; search_by_target requires exact ENCODE antigen registry string |
| gwas_get_snps_for_gene param | `gene_symbol="PDCD1"` | `mapped_gene="PDCD1"` (correct param name) |
| SAbDab search | Expecting JSON from `SAbDab_search_structures` | Returns URL only; use `SAbDab_get_structure` with PDB ID |
| IEDB sequence search | `organism_name="SARS-CoV-2"` (old API) | `sequence_contains="YLQPRTFLL"` or `filters` dict |
| KEGG disease ID | `disease_id="lupus"` | `disease_id="H00080"` (use KEGG ID format) |
| GWAS broken tool | `gwas_get_associations_for_trait(...)` | Use `gwas_search_associations(query=...)` instead |
| TIMER2 operation | Missing `operation` param | Only `"immune_estimation"` is valid; `cancer` must be TCGA code (e.g. "luad_tcga"), `gene` is symbol |

---

## Interpretation Framework

| Evidence Grade | Criteria | Confidence |
|----------------|----------|------------|
| **A -- Strong** | GWAS p < 5e-8 + IEDB epitope data + FAERS safety signal (PRR > 2) | High -- multiple orthogonal sources |
| **B -- Moderate** | GWAS or Orphanet genetics + pathway enrichment, but limited functional data | Medium -- directional evidence |
| **C -- Preliminary** | Single-database hit only (e.g., PPI network or pathway membership alone) | Low -- requires experimental follow-up |

**Interpreting immunology results:**
- Cytokine interaction hits from IntAct/BioGRID should be weighted by experimental method: co-IP and two-hybrid provide direct evidence, while co-expression or text-mining associations are hypothesis-generating only.
- FAERS disproportionality signals (PRR, ROR) indicate reporting bias, not causation -- a PRR > 2 with IC025 > 0 warrants clinical review but does not confirm a drug-adverse event relationship.
- Immune cell subset estimates from TIMER2 are deconvolution-based approximations; validate with orthogonal methods (flow cytometry, IHC) before drawing mechanistic conclusions about infiltration changes.

**Synthesis questions to address in the report:**
1. Does the genetic evidence (GWAS + Orphanet) converge on the same pathway as the protein interaction data (IntAct/BioGRID)?
2. For therapeutic antibody targets: do IEDB epitope data and SAbDab structural data support the proposed binding mechanism?
3. Are the safety signals from FAERS consistent across demographic strata (age, sex), or driven by a specific subpopulation?

---

## Key Immune Pathway IDs

**Reactome** (use with `stId` param): R-HSA-168256 (Immune System root), R-HSA-1280218 (Adaptive), R-HSA-168249 (Innate), R-HSA-1280215 (Cytokine Signaling), R-HSA-913531 (Interferon), R-HSA-449147 (Interleukin), R-HSA-202403 (TCR), R-HSA-983705 (BCR), R-HSA-166658 (Complement).

**KEGG** (use with `pathway_id` param): hsa04060 (Cytokine-receptor), hsa04660 (TCR), hsa04662 (BCR), hsa04650 (NK cell), hsa04620 (TLR), hsa04630 (JAK-STAT), hsa05322 (SLE disease), hsa05323 (RA disease).
