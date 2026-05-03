# Spatial Omics: Phase Procedures

Detailed procedures for each analysis phase. Referenced from SKILL.md.

---

## Phase 0: Input Processing & Disambiguation (ALWAYS FIRST)

**Objective**: Parse user input, resolve tissue/disease identifiers, establish analysis context.

### Tools Used

- **OpenTargets_get_disease_id_description_by_name**: `diseaseName` (string) -> `{data: {search: {hits: [{id, name, description}]}}}`
- **OpenTargets_get_disease_description_by_efoId**: `efoId` (string) -> `{data: {disease: {id, name, description, dbXRefs}}}`
- **HPA_search_genes_by_query**: `query` (string) -> List of gene entries

### Workflow

1. Parse SVG list from user input (ensure valid gene symbols)
2. Identify tissue type and map to standard ontology term
3. If disease provided, resolve to MONDO/EFO ID using OpenTargets
4. Get disease description and cross-references
5. Determine analysis scope:
   - Cancer? -> Include immune microenvironment, somatic mutations, druggable targets
   - Neurological? -> Include brain region specificity, neuronal markers
   - Metabolic? -> Include metabolic zonation, enzyme distribution
   - Normal tissue? -> Focus on tissue architecture and cell type composition
6. Set up report file with header information

### Decision Logic

- **Cancer tissue**: Enable immune microenvironment phase, CIViC/cBioPortal queries, immuno-oncology analysis
- **Normal tissue**: Skip disease phases, focus on tissue zonation and cell type composition
- **Liver/kidney/brain**: Enable zonation-specific analysis
- **No disease context**: Proceed with tissue biology only
- **Small gene list (<20)**: Warn about limited enrichment power, emphasize gene-level analysis
- **Large gene list (>500)**: Suggest filtering to top SVGs by significance before enrichment

---

## Phase 1: Gene Characterization

**Objective**: Resolve gene identifiers, annotate functions, tissue specificity, and subcellular localization.

### Tools Used

| Tool | Input | Use |
|------|-------|-----|
| `MyGene_query_genes` | `query` (string) | Resolve gene symbol to Ensembl/Entrez ID. Filter by `symbol` field |
| `UniProt_get_function_by_accession` | `accession` (string) | Protein function annotation |
| `UniProt_get_subcellular_location_by_accession` | `accession` (string) | Protein localization |
| `HPA_get_subcellular_location` | `gene_name` (string) | Experimentally validated subcellular location |
| `HPA_get_rna_expression_by_source` | `gene_name`, `source_type`, `source_name` (ALL 3 required) | Tissue expression |
| `HPA_get_comprehensive_gene_details_by_ensembl_id` | ALL 5 params required: `ensembl_id`, `include_isoforms`, `include_images`, `include_antibodies`, `include_expression` | One-stop HPA data |
| `HPA_get_cancer_prognostics_by_gene` | `ensembl_id` (NOT gene_name) | Cancer prognosis |
| `UniProtIDMap_gene_to_uniprot` | `gene_name`, `organism` | Map gene to UniProt accession |

### Workflow

1. For each SVG (batch if >20, sample top genes):
   a. Query MyGene to get Ensembl ID, Entrez ID
   b. Map to UniProt accession
   c. Get subcellular location from HPA
   d. Get tissue expression from HPA
   e. If cancer: check cancer prognostics
2. Compile gene characterization table
3. Identify genes with tissue-specific expression
4. Note genes with nuclear vs membrane vs secreted localization

### Batch Strategy

- **10-50 genes**: Characterize all individually
- **50-200 genes**: Top 50 by priority (known disease genes first), summarize rest
- **200+ genes**: Top 30, use enrichment for full list
- Always run pathway enrichment on the FULL list regardless

---

## Phase 2: Pathway & Functional Enrichment

**Objective**: Identify biological pathways and functions enriched in SVGs and per-domain gene sets.

### Tools Used

| Tool | Input | Notes |
|------|-------|-------|
| `STRING_functional_enrichment` | `protein_ids` (array), `species` (9606) | PRIMARY. Returns GO, KEGG, Reactome in one call |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (SPACE-SEPARATED string, NOT array) | Reactome-specific |
| `Reactome_map_uniprot_to_pathways` | `id` (UniProt accession) | Individual gene pathways |
| `GO_get_annotations_for_gene` | `gene_id` (string) | Individual gene GO terms |
| `kegg_search_pathway` | `query` (string) | Find KEGG pathways |
| `WikiPathways_search` | `query` (string) | Additional pathway context |

### Workflow

1. **Global SVG enrichment**: Run STRING_functional_enrichment on ALL SVGs, filter FDR < 0.05, report top 10-15 per category
2. **Reactome detailed**: Run ReactomeAnalysis_pathway_enrichment, report top FDR < 0.05
3. **Per-domain enrichment** (if domains provided): Run STRING on each domain's gene set, compare across domains
4. **Compile pathway tables**: Merge all results

### Enrichment Interpretation

- **Signaling** (RTK, Wnt, Notch, Hedgehog): Cell-cell communication
- **Metabolic**: Tissue metabolic zonation
- **Immune**: Immune infiltration/exclusion
- **ECM/adhesion**: Tissue structure and remodeling
- **Cell cycle/proliferation**: Growth zones
- **Apoptosis/stress**: Damage zones

---

## Phase 3: Spatial Domain Characterization

**Objective**: Characterize each spatial domain biologically and compare between domains.

Additional tools: `HPA_get_biological_processes_by_gene`, `HPA_get_protein_interactions_by_gene`

### Workflow

1. For each spatial domain:
   a. Get marker gene list
   b. Run STRING_functional_enrichment on domain genes
   c. Identify top pathways, GO terms
   d. Assign likely cell types from markers (see reference-data.md for marker lists)
   e. Generate biological interpretation narrative
2. Compare domains: differential pathways, unique vs shared genes, disease-relevant vs homeostatic regions

### Cell Type Assignment Rules

- Check each gene against known cell type markers
- Use HPA tissue/cell type expression data for validation
- Report confidence: high (3+ markers), medium (2), low (1)

---

## Phase 4: Cell-Cell Interaction Inference

**Objective**: Predict cell-cell communication from spatial gene expression patterns.

### Tools Used

| Tool | Input | Notes |
|------|-------|-------|
| `STRING_get_interaction_partners` | `protein_ids` (array), `species` (9606), `limit`, `confidence_score` (0.7) | PPI network |
| `STRING_get_protein_interactions` | `protein_ids` (array), `species` (9606) | Pairwise interactions |
| `intact_search_interactions` | `query`, `max` | IntAct database |
| `Reactome_get_interactor` | protein/gene ID | Pathway-level interactions |
| `DGIdb_get_drug_gene_interactions` | `genes` (array) | Druggable interaction nodes |

### Workflow

1. Run STRING_get_interaction_partners on all SVGs, filter score > 0.7, identify hub genes
2. Check for known ligand-receptor pairs (see reference-data.md)
3. Build interaction network: intra-domain, inter-domain, signaling axes
4. Map interactions to Reactome signaling pathways

---

## Phase 5: Disease & Therapeutic Context

**Objective**: Connect spatial findings to disease mechanisms and druggable targets.

### Tools Used

| Tool | Input | Notes |
|------|-------|-------|
| `OpenTargets_get_associated_targets_by_disease_efoId` | `efoId`, `size` | Disease-associated genes |
| `OpenTargets_get_target_tractability_by_ensemblID` | `ensemblId` | Druggability |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` (both REQUIRED) | Approved/clinical drugs |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` | Drug mechanism |
| `OpenTargets_target_disease_evidence` | `ensemblId`, `efoId` | Target-disease evidence |
| `clinical_trials_search` | `action='search_studies'`, `condition`, `intervention`, `limit` | Clinical trials |
| `DGIdb_get_gene_druggability` | `genes` (array) | Druggability categories |
| `civic_search_genes` | (no filter) | CIViC cancer evidence |

### Workflow

1. Disease gene overlap: OpenTargets targets intersected with SVGs
2. Druggable targets: DGIdb + OpenTargets tractability + approved drugs
3. Clinical trials: search for trials targeting spatial genes
4. Cancer-specific: CIViC evidence, immune checkpoints

---

## Phase 6: Multi-Modal Integration

**Objective**: Integrate protein, RNA, and metabolite spatial data when available.

### Tools

- `HPA_get_subcellular_location` (protein localization)
- `HPA_get_rna_expression_in_specific_tissues` (`ensembl_id`, `tissue_name`)
- `Reactome_map_uniprot_to_pathways` (metabolic pathways)
- `kegg_get_pathway_info` (KEGG pathway details)

### Workflow

1. **RNA-Protein concordance**: Compare spatial RNA with protein detection, note concordant vs discordant
2. **Subcellular context**: Secreted = paracrine signaling, Membrane = surface markers, Nuclear = TFs
3. **Metabolic integration**: Map genes to metabolic pathways, link detected metabolites to enzymes

---

## Phase 7: Immune Microenvironment (Cancer/Inflammation)

**Activate only if**: cancer/autoimmune/inflammatory context, immune marker SVGs present, or user requests.

### Tools

- `STRING_functional_enrichment` (immune pathway enrichment)
- `OpenTargets_get_target_tractability_by_ensemblID` (checkpoint druggability)
- `iedb_search_epitopes` (`organism_name`, `source_antigen_name`)

### Workflow

1. Identify immune-related SVGs from marker lists (see reference-data.md)
2. Classify immune cell types per spatial domain
3. Check immune checkpoint expression
4. Assess immune infiltration: Hot vs Cold vs Excluded
5. Identify immunotherapy targets
6. Check for tertiary lymphoid structures (B cell + T cell clusters)

---

## Phase 8: Literature & Validation Context

**Objective**: Literature evidence and experimental validation suggestions.

### Tools

- `PubMed_search_articles`: `query`, `max_results` -> `[{pmid, title, authors, journal, pub_date, doi}]`
- `openalex_literature_search`: `query`, `per_page` -> works with titles, DOIs, abstracts

### Search Strategy

1. `"{tissue} spatial transcriptomics"`
2. `"{disease} spatial omics"`
3. `"{top_gene} {tissue} expression"` for key SVGs
4. `"{tissue} zonation gene expression"` (if relevant)
5. `"{technology} {tissue}"`

### Validation Recommendations

| Priority | Method | Use Case |
|----------|--------|----------|
| High | smFISH / RNAscope | Validate spatial pattern at single-molecule level |
| High | IHC on serial sections | Confirm protein expression in spatial domain |
| High | Proximity ligation assay (PLA) | Confirm physical interaction at tissue level |
| Medium | Multiplexed IF (CODEX/IBEX) | Validate multiple markers simultaneously |
| Medium | Spatial metabolomics (MALDI/DESI) | Confirm metabolic pathway activity |
| Low | Co-culture + conditioned media | Functional validation of predicted interaction |
