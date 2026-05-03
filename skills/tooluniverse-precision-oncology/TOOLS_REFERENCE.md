# Precision Oncology - Tool Reference

## Variant Interpretation Tools

### CIViC (Clinical Interpretation of Variants in Cancer)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `civic_search_variants` | Search variants by gene | `query` (gene symbol) |
| `civic_get_variant` | Get variant details | `id` (numeric variant ID) |
| `civic_get_evidence_item` | Get evidence details | `id` (evidence item ID) |
| `civic_search_genes` | Search genes | `query` (gene name) |
| `civic_search_evidence_items` | Search evidence | `drug`, `disease`, `evidence_type` |

**Example - Get EGFR L858R evidence**:
```python
# 1. Search for variant
variants = tu.tools.civic_search_variants(query="EGFR L858R")
# 2. Get evidence items
for v in variants:
    evidence = tu.tools.civic_get_variant(id=v['id'])
```

### ClinVar

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinVar_search_variants` | Search variants | `query`, `gene` |
| `clinvar_get_variant_details` | Get variant details | `variant_id` |

### COSMIC - Somatic Cancer Mutations (NEW)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `COSMIC_search_mutations` | Search mutations | `operation="search"`, `terms`, `max_results`, `genome_build` |
| `COSMIC_get_mutations_by_gene` | All mutations for gene | `operation="get_by_gene"`, `gene`, `max_results`, `genome_build` |

**Example - Get BRAF mutations**:
```python
# Search for specific mutation
result = tu.tools.COSMIC_search_mutations(
    operation="search",
    terms="BRAF V600E",
    max_results=20
)
# Returns: mutation_id, GeneName, MutationCDS, MutationAA, PrimarySite, PrimaryHistology

# Get all mutations for gene (for hotspot analysis)
mutations = tu.tools.COSMIC_get_mutations_by_gene(
    operation="get_by_gene",
    gene="EGFR",
    max_results=200,
    genome_build=38
)
# Returns: All EGFR mutations with cancer type distribution
```

**Why use COSMIC**:
- **Gold standard** for somatic cancer mutations
- Cancer type distribution (which tumors have this mutation)
- Mutation frequency (recurrent vs. rare)
- FATHMM pathogenicity prediction

**Genome Build Note**: Use `genome_build=38` for GRCh38 or `genome_build=37` for GRCh37.

---

### GDC/TCGA - Patient Tumor Data (NEW)

Access real patient tumor data from The Cancer Genome Atlas.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `GDC_get_mutation_frequency` | Pan-cancer mutation stats | `gene_symbol` |
| `GDC_get_ssm_by_gene` | Somatic mutations by gene | `gene_symbol`, `project_id` (optional), `size` |
| `GDC_get_gene_expression` | RNA-seq file metadata | `project_id`, `size` |
| `GDC_get_cnv_data` | Copy number variation | `project_id`, `gene_symbol` (optional), `size` |
| `GDC_list_projects` | List TCGA/TARGET projects | `program` (e.g., "TCGA"), `size` |
| `GDC_search_cases` | Search patient cases | `project_id`, `size` |

**Example - Get EGFR mutations in lung cancer**:
```python
# Get mutation frequency for gene
freq = tu.tools.GDC_get_mutation_frequency(
    gene_symbol="EGFR"
)
# Returns: SSM case count, CNV gain/loss counts

# Get specific mutations in lung adenocarcinoma
mutations = tu.tools.GDC_get_ssm_by_gene(
    gene_symbol="EGFR",
    project_id="TCGA-LUAD",
    size=50
)
# Returns: mutation coordinates, amino acid changes, sample counts
```

**TCGA Project IDs**:
| Cancer Type | Project ID |
|-------------|------------|
| Lung Adenocarcinoma | TCGA-LUAD |
| Lung Squamous | TCGA-LUSC |
| Breast | TCGA-BRCA |
| Colorectal | TCGA-COAD |
| Melanoma | TCGA-SKCM |
| Glioblastoma | TCGA-GBM |
| Pancreatic | TCGA-PAAD |
| Ovarian | TCGA-OV |

**Why use GDC/TCGA**:
- **Real patient tumor data** - Not cell lines, actual human tumors
- **Pan-cancer analysis** - Same gene across 33 cancer types
- **Multi-omics** - Mutations + expression + CNV
- **Clinical annotations** - Stage, survival data available

---

### OncoKB - Therapeutic Actionability (NEW)

FDA-recognized biomarker annotations and treatment recommendations.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OncoKB_annotate_variant` | Variant actionability | `gene`, `variant`, `tumor_type` (OncoTree code) |
| `OncoKB_get_gene_info` | Gene classification | `gene` |
| `OncoKB_get_cancer_genes` | All cancer genes | - |
| `OncoKB_get_levels` | Level definitions | - |
| `OncoKB_annotate_copy_number` | CNV actionability | `gene`, `copy_number_type`, `tumor_type` |

**Example - Get variant actionability**:
```python
# Annotate BRAF V600E in melanoma
result = tu.tools.OncoKB_annotate_variant(
    operation="annotate_variant",
    gene="BRAF",
    variant="V600E",
    tumor_type="MEL"  # Melanoma
)
# Returns: oncogenic, mutationEffect, highestSensitiveLevel, treatments

# Check if gene is oncogene/TSG
gene_info = tu.tools.OncoKB_get_gene_info(
    operation="get_gene_info",
    gene="BRAF"
)
# Returns: oncogene=True, tsg=False
```

**OncoKB Evidence Levels**:
| Level | Description | Clinical Use |
|-------|-------------|--------------|
| **1** | FDA-recognized biomarker | Standard care |
| **2** | Standard care (non-FDA) | Guideline recommended |
| **3A** | Compelling clinical evidence | Consider in clinical decision |
| **3B** | Standard care in different tumor | Off-label consideration |
| **4** | Biological evidence | Research context |
| **R1** | Standard care resistance | Explains treatment failure |
| **R2** | Compelling resistance evidence | Resistance interpretation |

**OncoTree Tumor Type Codes** (common):
| Cancer | Code |
|--------|------|
| Melanoma | MEL |
| Non-Small Cell Lung Cancer | NSCLC |
| Lung Adenocarcinoma | LUAD |
| Breast Cancer | BRCA |
| Colorectal Cancer | COADREAD |
| Pancreatic | PAAD |

---

### cBioPortal - Cross-Study Analysis (NEW)

Aggregate genomic data across cancer studies.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `cBioPortal_get_cancer_studies` | List available studies | `limit` |
| `cBioPortal_get_mutations` | Mutations for genes | `study_id`, `gene_list` |
| `cBioPortal_get_molecular_profiles` | Study molecular profiles | `study_id` |
| `cBioPortal_get_sample_clinical_data` | Clinical data | `study_id`, `sample_ids` |
| `cBioPortal_get_patient_clinical_data` | Patient clinical data | `study_id`, `patient_ids` |

**Example - Query mutations across studies**:
```python
# Get studies
studies = tu.tools.cBioPortal_get_cancer_studies(limit=50)

# Get EGFR mutations in TCGA-LUAD
mutations = tu.tools.cBioPortal_get_mutations(
    study_id="luad_tcga",
    gene_list="EGFR,KRAS,ALK"
)
# Returns: proteinChange, mutationType, sampleId, validationStatus

# Get molecular profiles for study
profiles = tu.tools.cBioPortal_get_molecular_profiles(
    study_id="brca_tcga"
)
# Returns: mutation profiles, CNA profiles, expression profiles
```

**Common cBioPortal Study IDs**:
| Study | ID |
|-------|-----|
| TCGA Breast Cancer | brca_tcga |
| TCGA Lung Adenocarcinoma | luad_tcga |
| TCGA Colorectal | coadread_tcga |
| TCGA Melanoma | skcm_tcga |
| GENIE (AACR) | genie_public |

---

### Human Protein Atlas - Expression Validation (NEW)

Protein expression data in tissues and cell lines.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `HPA_search_genes_by_query` | Search for gene | `search_query` |
| `HPA_generic_search` | Custom search | `search_query`, `columns` |
| `HPA_get_comparative_expression_by_gene_and_cellline` | Expression comparison | `gene_name`, `cell_line` |

**Example - Check target expression**:
```python
# Search for gene
gene = tu.tools.HPA_search_genes_by_query(search_query="EGFR")
# Returns: Gene name, Ensembl ID, synonyms

# Compare expression in cancer cell line vs normal
expression = tu.tools.HPA_get_comparative_expression_by_gene_and_cellline(
    gene_name="EGFR",
    cell_line="a549"  # Lung cancer cell line
)
# Returns: expression level differences vs healthy tissue
```

**Supported Cancer Cell Lines**:
| Cell Line | Cancer Type |
|-----------|-------------|
| A549 | Lung adenocarcinoma |
| MCF7 | Breast cancer |
| HepG2 | Hepatocellular carcinoma |
| HeLa | Cervical cancer |
| PC3 | Prostate cancer |
| Jurkat | T-cell leukemia |

**Why HPA matters for precision oncology**:
- **Target validation** - Confirm target expressed in tumor
- **Differential expression** - Compare tumor vs normal
- **Tissue specificity** - Predict on-target/off-tumor effects
- **Cell line selection** - Choose appropriate models

---

### DepMap - Target Validation (NEW)

Cancer cell line dependency data from CRISPR knockout screens.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DepMap_get_gene_dependencies` | CRISPR gene essentiality | `gene_symbol` |
| `DepMap_get_cell_lines` | List cell lines with metadata | `tissue`, `cancer_type`, `page_size` |
| `DepMap_search_cell_lines` | Search by name | `query` |
| `DepMap_get_cell_line` | Detailed cell line info | `model_id` OR `model_name` |
| `DepMap_get_drug_response` | Drug sensitivity data | `drug_name` |

**Example - Assess target essentiality**:
```python
# Is KRAS essential in cancer cells?
deps = tu.tools.DepMap_get_gene_dependencies(
    gene_symbol="KRAS"
)
# Returns: gene info, note about effect scores

# Get lung cancer cell lines
cells = tu.tools.DepMap_get_cell_lines(
    tissue="Lung",
    cancer_type="Non-Small Cell Lung Cancer",
    page_size=20
)
# Returns: cell line names, cancer types, MSI status
```

**Effect Score Interpretation**:
| Score Range | Interpretation |
|-------------|----------------|
| < -1.0 | Strongly essential |
| -0.5 to -1.0 | Essential |
| -0.5 to 0 | Weakly essential |
| > 0 | Not essential |

**Why use DepMap for Precision Oncology**:
- **Target validation** - Proves gene is essential for cancer survival
- **Cancer selectivity** - Is it essential only in cancer?
- **Combination targets** - Identify synthetic lethal partners
- **Drug sensitivity** - Which cell lines respond to drugs?

---

## Drug/Treatment Tools

### OpenTargets

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblId` | Drugs for target | `ensemblId` (camelCase!) |
| `OpenTargets_get_disease_associated_targets` | Targets for disease | `efoId` |
| `OpenTargets_get_target_tractability` | Druggability | `ensemblId` |

**Parameter Note**: Always use `ensemblId` (camelCase), NOT `ensemblID`.

### ChEMBL

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChEMBL_search_drugs` | Search drugs | `query`, `max_phase` |
| `ChEMBL_get_drug_mechanisms_of_action_by_chemblId` | Drug MOA | `chemblId` |
| `ChEMBL_get_target_activities` | Bioactivity data | `target_chembl_id` |

### DailyMed

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DailyMed_search_spls` | Search FDA labels | `drug_name` |
| `DailyMed_search_spls` | Get label details | `setid` |

---

## Clinical Trial Tools

### ClinicalTrials.gov

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_clinical_trials` | Search trials | `condition`, `intervention`, `status`, `pageSize` |
| `get_clinical_trial_by_nct_id` | Get trial details | `nct_id` |
| `get_clinical_trial_eligibility_criteria` | Eligibility | `nct_ids` (list) |

**Common Status Values**: "Recruiting", "Active, not recruiting", "Completed"

---

## Gene/Protein Tools

### MyGene.info

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `MyGene_query_genes` | Search genes | `q`, `species` |
| `MyGene_get_gene_by_id` | Get gene info | `geneid` |

### UniProt

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `UniProt_search` | Search proteins | `query`, `organism` |
| `UniProt_get_protein_by_accession` | Get protein | `accession` |
| `UniProt_get_protein_sequence` | Get sequence | `accession` |

---

## Structure Analysis Tools (NvidiaNIM)

### Protein Structure

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_alphafold2` | Predict structure | `sequence` |
| `NvidiaNIM_esmfold` | Fast structure prediction | `sequence` |

### Molecular Docking

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_diffdock` | Protein-ligand docking | `protein`, `ligand`, `num_poses`, `is_staged` |

---

## Literature Tools

### PubMed

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search articles | `query`, `limit` |
| `PubMed_get_article_details` | Get article | `pmid` |

### EuropePMC

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search articles | `query`, `page_size` |
| `EuropePMC_get_citations` | Get citations | `source`, `ext_id` |

---

## Expression & Network Tools (NEW)

### CELLxGENE - Tumor Single-Cell Expression

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CELLxGENE_get_expression_data` | Cell-type expression | `gene`, `tissue` |
| `CELLxGENE_get_cell_metadata` | Cell annotations | `gene` |

**Example - Tumor expression**:
```python
# Get expression in lung cancer
expression = tu.tools.CELLxGENE_get_expression_data(
    gene="EGFR",
    tissue="lung"
)
# Returns: Expression per cell type (tumor, CAF, immune, etc.)
```

### IntAct - Protein Interactions

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `intact_search_interactions` | Find interactions | `query`, `species` |
| `intact_get_interaction_network` | Network view | `gene`, `depth` |

**Example - Resistance network**:
```python
# Get EGFR interaction partners
network = tu.tools.intact_get_interaction_network(
    gene="EGFR",
    depth=1  # Direct interactors
)
# Returns: MET, ERBB2, ERBB3, etc.
```

### KEGG - Cancer Pathways

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `kegg_search_pathway` | Search pathways | `query` |
| `kegg_get_gene_info` | Gene pathway membership | `gene_id` |

**Example - Get pathway context**:
```python
pathways = tu.tools.kegg_get_gene_info(gene_id="hsa:1956")  # EGFR
# Returns: EGFR signaling, NSCLC pathway, etc.
```

---

## Literature Tools (NEW)

### PubMed - Published Literature

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search papers | `query`, `limit` |
| `PubMed_get_article_details` | Get abstract | `pmid` |

### BioRxiv/MedRxiv - Preprints

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search preprints (bioRxiv/medRxiv) | `query`, `source='PPR'`, `pageSize` |
| `BioRxiv_get_preprint` | Get preprint by DOI | `doi` |
| `MedRxiv_get_preprint` | Get preprint by DOI | `doi`, `server='medrxiv'` |

**⚠️ Important**: Flag preprints as NOT peer-reviewed in reports.

**Example - Search preprints**:
```python
# bioRxiv/medRxiv don't have search APIs, use EuropePMC
preprints = tu.tools.EuropePMC_search_articles(
    query="EGFR inhibitor resistance",
    source="PPR",  # PPR = Preprints only
    pageSize=20
)

### OpenAlex - Citation Analysis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `openalex_search_works` | Search with citations | `query`, `limit` |
| `openalex_get_author` | Author metrics | `author_id` |

---

## Workflow Examples

### Example 1: EGFR-Mutant Lung Cancer

```python
# 1. Resolve EGFR IDs
gene_ids = resolve_gene(tu, "EGFR")

# 2. Get CIViC evidence for L858R
civic_ev = get_civic_evidence(tu, "EGFR", "L858R")

# 3. Get approved drugs
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblId(
    ensemblId=gene_ids['ensembl']
)

# 4. Find clinical trials
trials = tu.tools.search_clinical_trials(
    condition="Non-Small Cell Lung Cancer",
    intervention="EGFR",
    status="Recruiting"
)
```

### Example 2: Resistance Analysis

```python
# 1. Get known resistance mechanisms for osimertinib
resistance = tu.tools.civic_search_evidence_items(
    drug="osimertinib",
    evidence_type="Predictive",
    clinical_significance="Resistance"
)

# 2. Literature on C797S
papers = tu.tools.PubMed_search_articles(
    query='"osimertinib" AND "C797S" AND resistance',
    limit=20
)

# 3. Structural analysis if needed
# Get protein structure for binding analysis
```

---

## Prognosis & Survival Tools

### CancerPrognosis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CancerPrognosis_get_survival_data` | OS/DFS survival curves for TCGA cancers | `cancer` (TCGA code, e.g. `"BRCA"`), `limit` |
| `CancerPrognosis_get_gene_expression` | mRNA expression by cancer type | `cancer`, `gene` |
| `CancerPrognosis_search_studies` | Find non-TCGA studies in cBioPortal | `keyword` |

**Supported TCGA codes** (33 total): ACC, BLCA, BRCA, CESC, CHOL, COAD, DLBC, ESCA, GBM, HNSC, KICH, KIRC, KIRP, LAML, LGG, LIHC, LUAD, LUSC, MESO, OV, PAAD, PCPG, PRAD, READ, SARC, SKCM, STAD, TGCT, THCA, THYM, UCEC, UCS, UVM

**Non-TCGA cancer type routing** — these cancers are NOT in TCGA; use `CancerPrognosis_search_studies`:

| Cancer | Keyword for search_studies | Notes |
|--------|---------------------------|-------|
| CLL / Chronic lymphocytic leukemia | `"CLL"` or `"leukemia"` | Most CLL studies are WES-only (no survival/expression data) |
| SLL | `"CLL"` | Treated as CLL in cBioPortal |
| Multiple myeloma (MM) | `"myeloma"` | |
| Follicular lymphoma (FL) | `"follicular"` | |
| Mantle cell lymphoma (MCL) | `"mantle"` | |
| Osteosarcoma | `"osteosarcoma"` | |
| Ewing sarcoma | `"sarcoma"` | |
| Neuroblastoma | `"neuroblastoma"` | |
| Medulloblastoma | `"medulloblastoma"` | |
| Pancreatic ductal adenocarcinoma | `"pancreatic"` | TCGA code is PAAD |
| AML / Acute myeloid leukemia | `"leukemia"` | TCGA code is LAML |
| Glioblastoma | `"glioblastoma"` | TCGA code is GBM |

**Workflow for non-TCGA cancers:**
```
1. CancerPrognosis_search_studies(keyword="<disease>")
   → identify study_id (e.g. "msk_impact_2017")
2. CancerPrognosis_get_survival_data(cancer="<study_id>")
   → check if OS_MONTHS / DFS_MONTHS fields present
3. If no survival data: study is mutation-only (WES) — note limitation in report
```

---

## Fallback Chain Details

### Variant Interpretation
```
CIViC → COSMIC_get_mutations_by_gene → ClinVar → OncoKB (manual) → PubMed
```

### Somatic Mutation Analysis (NEW)
```
COSMIC_get_mutations_by_gene (somatic) → CIViC (clinical) → ClinVar (germline) → PubMed
```

### Prognosis / Survival
```
CancerPrognosis_get_survival_data (TCGA) → CancerPrognosis_search_studies → CancerPrognosis_get_gene_expression
```

### Drug Information
```
OpenTargets → ChEMBL → DailyMed → DrugBank
```

### Clinical Trials
```
ClinicalTrials.gov (primary) → WHO ICTRP → EudraCT
```

### Structure Prediction
```
AlphaFold DB (precomputed) → NvidiaNIM_alphafold2 → NvidiaNIM_esmfold
```
