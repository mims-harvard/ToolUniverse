# Rare Disease Diagnosis - Tool Reference

## Phase 1: Phenotype Standardization

### HPO Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `HPO_search_terms` | Search HPO by text | `query` |
| `HPO_get_term_by_id` | Get HPO term details | `hp_id` |
| `HPO_get_term_genes` | Genes associated with HPO term | `hp_id` |
| `HPO_get_term_diseases` | Diseases with HPO term | `hp_id` |

**Example - Convert symptom to HPO**:
```python
# Search for HPO term
results = tu.tools.HPO_search_terms(query="tall stature")
# Returns: [{"id": "HP:0000098", "name": "Tall stature", ...}]
```

---

## Phase 2: Disease Matching

### Orphanet Tools (UPDATED)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `Orphanet_search_diseases` | Search rare diseases | `operation="search_diseases"`, `query` |
| `Orphanet_get_disease` | Get disease details | `operation="get_disease"`, `orpha_code` |
| `Orphanet_get_genes` | Genes for disease | `operation="get_genes"`, `orpha_code` |
| `Orphanet_get_classification` | Disease hierarchy | `operation="get_classification"`, `orpha_code` |
| `Orphanet_search_by_name` | Exact name search | `operation="search_by_name"`, `name`, `exact` |

**Example - Search Orphanet (NEW)**:
```python
# Search for rare diseases
results = tu.tools.Orphanet_search_diseases(
    operation="search_diseases",
    query="Marfan"
)
# Returns: List of matching rare diseases with ORPHA codes

# Get genes for a disease
genes = tu.tools.Orphanet_get_genes(
    operation="get_genes",
    orpha_code="558"
)
# Returns: FBN1 (causative), associated genes
```

**Common Orphanet Disease Codes**:
| Disease | ORPHA Code |
|---------|------------|
| Marfan syndrome | 558 |
| Loeys-Dietz syndrome | 60030 |
| Vascular EDS | 286 |
| Alexander disease | 58 |
| Prader-Willi syndrome | 739 |

### OMIM Tools (UPDATED)

**⚠️ Requires**: `OMIM_API_KEY` environment variable (register at omim.org/api)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OMIM_search` | Search OMIM | `operation="search"`, `query`, `limit` |
| `OMIM_get_entry` | Get MIM entry | `operation="get_entry"`, `mim_number` |
| `OMIM_get_clinical_synopsis` | Clinical features by organ | `operation="get_clinical_synopsis"`, `mim_number` |
| `OMIM_get_gene_map` | Gene-disease mappings | `operation="get_gene_map"`, `mim_number` or `chromosome` |

**Example - Get OMIM details (NEW)**:
```python
# Search OMIM
search = tu.tools.OMIM_search(
    operation="search",
    query="BRCA1",
    limit=5
)
# Returns: List of MIM numbers

# Get detailed entry
entry = tu.tools.OMIM_get_entry(
    operation="get_entry",
    mim_number="154700"  # Marfan syndrome
)
# Returns: Full text, inheritance, molecular genetics

# Get clinical synopsis (structured phenotype)
synopsis = tu.tools.OMIM_get_clinical_synopsis(
    operation="get_clinical_synopsis",
    mim_number="154700"
)
# Returns: Features by organ system (neurologicCentralNervousSystem, cardiovascular, etc.)
```

### DisGeNET Tools (NEW)

**⚠️ Requires**: `DISGENET_API_KEY` environment variable (register free at disgenet.org)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DisGeNET_search_gene` | Diseases for a gene | `operation="search_gene"`, `gene`, `limit` |
| `DisGeNET_search_disease` | Genes for a disease | `operation="search_disease"`, `disease`, `limit` |
| `DisGeNET_get_gda` | Gene-disease associations | `operation="get_gda"`, `gene`/`disease`, `source`, `min_score` |
| `DisGeNET_get_vda` | Variant-disease associations | `operation="get_vda"`, `variant`/`gene`, `limit` |
| `DisGeNET_get_disease_genes` | All genes for disease | `operation="get_disease_genes"`, `disease`, `min_score` |

**Example - DisGeNET gene-disease associations**:
```python
# Get diseases associated with gene
result = tu.tools.DisGeNET_search_gene(
    operation="search_gene",
    gene="FBN1",
    limit=20
)
# Returns: Marfan syndrome (score: 0.95), MASS phenotype, etc.

# Get high-confidence curated associations
gda = tu.tools.DisGeNET_get_gda(
    operation="get_gda",
    gene="FBN1",
    source="CURATED",
    min_score=0.3,
    limit=20
)
# Returns: Gene-disease associations with evidence scores

# Get variant-disease associations for diagnosis
vda = tu.tools.DisGeNET_get_vda(
    operation="get_vda",
    gene="FBN1",
    limit=30
)
# Returns: Variants with disease associations
```

**DisGeNET Score Interpretation**:
| Score | Interpretation | Use |
|-------|----------------|-----|
| >0.7 | Very Strong | High confidence |
| 0.4-0.7 | Strong | Good evidence |
| 0.2-0.4 | Moderate | Consider |
| <0.2 | Weak | Low confidence |

### ClinGen - Gene-Disease Validity (NEW)

Authoritative curation of gene-disease relationships.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_gene_validity` | Gene-disease validity | `gene` |
| `ClinGen_search_dosage_sensitivity` | HI/TS scores | `gene` |
| `ClinGen_search_actionability` | Clinical actionability | `gene` |
| `ClinGen_get_variant_classifications` | Expert variant classifications | `gene`, `variant` |

```python
# Check gene-disease validity classification
validity = tu.tools.ClinGen_search_gene_validity(gene="FBN1")
# Returns: Definitive for Marfan syndrome, Strong for MASS phenotype

# Check dosage sensitivity (for CNV interpretation)
dosage = tu.tools.ClinGen_search_dosage_sensitivity(gene="MECP2")
# Returns: HI Score 3 (haploinsufficient), TS Score 0

# Check clinical actionability
actionability = tu.tools.ClinGen_search_actionability(gene="BRCA1")
# Returns: Adult and pediatric actionability data
```

**ClinGen Validity Classification** (for gene panel prioritization):
| Classification | Include in Panel? | ACMG Impact |
|----------------|-------------------|-------------|
| **Definitive** | Yes - mandatory | Strong PP4 support |
| **Strong** | Yes | Good PP4 support |
| **Moderate** | Yes | Moderate PP4 support |
| **Limited** | Yes, but flag | Weak support |
| **Disputed** | Exclude | Conflicting evidence |
| **Refuted** | EXCLUDE | Gene not causative |

**Dosage Sensitivity Scores** (for CNV interpretation):
| Score | Meaning | ACMG Impact |
|-------|---------|-------------|
| **3** | Sufficient evidence | PVS1 for LOF deletions |
| **2** | Emerging evidence | PM1 |
| **1** | Little evidence | Weak support |
| **0/40** | None/Unlikely | No dosage sensitivity |

### OpenTargets Disease Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OpenTargets_get_disease_info_by_efoId` | Disease details | `efoId` |
| `OpenTargets_get_disease_associated_targets` | Genes for disease | `efoId` |
| `OpenTargets_get_associated_diseases_by_target_ensemblId` | Diseases for gene | `ensemblId` |

---

## Phase 3: Gene Panel

### Gene Information

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `MyGene_query_genes` | Search genes | `q`, `species` |
| `MyGene_get_gene_by_id` | Gene details | `geneid` |
| `ensembl_lookup_gene` | Ensembl gene info | `id`, `species` |

**Parameter Note**: Use `q` not `gene` for MyGene_query_genes.

### Expression Validation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `GTEx_get_median_gene_expression` | Tissue expression | `gencode_id` |
| `HPA_get_gene_expression` | Protein expression | `ensembl_id` |

**Note**: GTEx requires versioned Ensembl ID (e.g., `ENSG00000166147.15`)

### Constraint Scores

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `gnomAD_get_gene_constraints` | pLI, LOEUF scores | `gene_symbol` |
| `ExAC_get_constraint_metrics` | Constraint data | `gene` |

---

## Phase 4: Variant Interpretation

### ClinVar Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinVar_search_variants` | Search variants | `query` |
| `clinvar_get_variant_details` | Get variant details | `id` (not `variant_id`) |
| `ClinVar_get_variant_classifications` | Classification history | `id` |

**Parameter Note**: Use `id` not `variant_id` for ClinVar lookups.

### Population Frequency

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `gnomAD_get_variant_frequencies` | Allele frequencies | `variant_id` |
| `gnomAD_get_variant_annotations` | Variant annotations | `variant_id` |

**Variant ID Format**: `1-55505647-G-A` (chrom-pos-ref-alt)

### Pathogenicity Prediction (ENHANCED)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CADD_get_variant_score` | **CADD deleteriousness (NEW API)** | `chrom`, `pos`, `ref`, `alt`, `version` |
| `AlphaMissense_get_variant_score` | **DeepMind pathogenicity (NEW)** | `uniprot_id`, `variant` |
| `EVE_get_variant_score` | **Evolutionary pathogenicity (NEW)** | `chrom`, `pos`, `ref`, `alt` OR `variant` (HGVS) |
| `SpliceAI_predict_splice` | **Splice impact (NEW)** | `variant`, `genome` |
| `SpliceAI_get_max_delta` | **Quick splice triage (NEW)** | `variant`, `genome` |
| `SpliceAI_predict_pangolin` | Alternative splice model | `variant`, `genome` |

### CADD API (NEW)

Direct access to CADD deleteriousness scores:

```python
# Get CADD score for variant
result = tu.tools.CADD_get_variant_score(
    chrom="15",
    pos=48942946,
    ref="G",
    alt="A",
    version="GRCh38-v1.7"
)
# Returns: phred_score, raw_score, interpretation
# PHRED ≥20 = top 1% deleterious (PP3 support)
```

### AlphaMissense (NEW)

DeepMind's state-of-the-art missense pathogenicity prediction (~90% accuracy):

```python
# Get pathogenicity score for missense variant
result = tu.tools.AlphaMissense_get_variant_score(
    uniprot_id="P35555",  # FBN1
    variant="E1541K"  # or "p.E1541K"
)
# Returns: pathogenicity_score, classification (pathogenic/ambiguous/benign)
# Thresholds: >0.564 pathogenic, <0.34 benign
```

### EVE (NEW)

Evolutionary variant effect prediction (Harvard/Oxford):

```python
# Get EVE score
result = tu.tools.EVE_get_variant_score(
    chrom="15",
    pos=48942946,
    ref="G",
    alt="A"
)
# Returns: eve_score, classification (likely_pathogenic/likely_benign)
# Threshold: >0.5 likely pathogenic
```

### SpliceAI - Splice Variant Prediction (NEW)

Deep learning model for predicting splice-altering effects. ~15% of pathogenic variants affect splicing.

```python
# Full splice prediction
result = tu.tools.SpliceAI_predict_splice(
    variant="chr15-48942946-G-A",
    genome="38"  # or "37"
)
# Returns: DS_AG, DS_AL, DS_DG, DS_DL scores + max_delta_score + interpretation

# Quick triage (max score only)
quick = tu.tools.SpliceAI_get_max_delta(
    variant="chr15-48942946-G-A",
    genome="38"
)
# Returns: max_delta_score, interpretation, pathogenicity_threshold
```

**Variant Format**: `chr{chrom}-{pos}-{ref}-{alt}`

**SpliceAI Delta Score Interpretation**:
| Score Type | Meaning |
|------------|---------|
| DS_AG | Acceptor Gain (creates new) |
| DS_AL | Acceptor Loss (disrupts existing) |
| DS_DG | Donor Gain (creates new) |
| DS_DL | Donor Loss (disrupts existing) |

**Max Score Thresholds for ACMG**:
| Max Delta Score | Interpretation | ACMG |
|-----------------|----------------|------|
| ≥0.8 | High splice impact | PP3 (strong) |
| 0.5-0.8 | Moderate impact | PP3 (supporting) |
| 0.2-0.5 | Low impact | PP3 (weak) |
| <0.2 | Likely no impact | BP7 (if synonymous) |

**When to Use SpliceAI**:
- Intronic variants within ±50bp of splice sites
- Synonymous variants (may still affect splicing)
- Exonic variants near splice junctions
- Variants creating cryptic splice sites

---

**Prediction Tool Thresholds for PP3**:
| Tool | Damaging | Uncertain | Benign |
|------|----------|-----------|--------|
| **AlphaMissense** | >0.564 | 0.34-0.564 | <0.34 |
| **CADD PHRED** | ≥20 | 15-20 | <15 |
| **EVE** | >0.5 | - | ≤0.5 |
| **SpliceAI** | ≥0.5 | 0.2-0.5 | <0.2 |

**Recommended Strategy for VUS**:
1. Run all predictors (AlphaMissense, CADD, EVE for missense; SpliceAI for splice)
2. If ≥2 concordant damaging → Strong PP3 support
3. If ≥2 concordant benign → BP4 support
4. If discordant → Weight AlphaMissense highest for missense, SpliceAI for splice

---

## Phase 3.5: Expression & Regulatory Context (NEW)

### CELLxGENE - Single-Cell Expression

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CELLxGENE_get_expression_data` | Cell-type specific expression | `gene`, `tissue` |
| `CELLxGENE_get_cell_metadata` | Cell type annotations | `gene` |
| `CELLxGENE_download_h5ad` | Download full dataset | `dataset_id` |
| `CELLxGENE_get_embeddings` | UMAP/tSNE coordinates | `dataset_id` |

**Example - Get cell-type expression**:
```python
# Get expression across cell types
expression = tu.tools.CELLxGENE_get_expression_data(
    gene="FBN1",
    tissue="heart"
)
# Returns: Expression values per cell type
```

**Why use it**: Validates that candidate genes are expressed in disease-relevant cell types (e.g., fibroblasts for connective tissue disorders).

### ChIPAtlas - Transcription Factor Binding

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChIPAtlas_enrichment_analysis` | TF binding enrichment | `gene`, `cell_type` |
| `ChIPAtlas_get_peak_data` | ChIP-seq peaks | `gene`, `experiment_type` |
| `ChIPAtlas_search_datasets` | Find experiments | `antigen`, `cell_type` |
| `ChIPAtlas_get_experiments` | Experiment metadata | `experiment_id` |

**Example - Get regulatory context**:
```python
# Find TFs that regulate gene
tf_binding = tu.tools.ChIPAtlas_enrichment_analysis(
    gene="FBN1",
    cell_type="Fibroblast"
)
# Returns: TFs with significant binding near gene
```

**Why use it**: Identifies regulatory mechanisms that may be disrupted; helps interpret regulatory variants.

### ENCODE - Regulatory Elements

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ENCODE_search_experiments` | Find experiments | `assay_title`, `biosample` |
| `ENCODE_get_experiment` | Experiment details | `accession` |
| `ENCODE_get_biosample` | Sample annotations | `accession` |
| `ENCODE_list_files` | Get data files | `experiment_accession` |

**Example - Get regulatory data**:
```python
# Search for regulatory data
experiments = tu.tools.ENCODE_search_experiments(
    assay_title="ATAC-seq",
    biosample="heart"
)
```

---

## Phase 3.6: Pathway Analysis (NEW)

### KEGG - Metabolic & Signaling Pathways

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `kegg_search_pathway` | Search pathways | `query` |
| `kegg_get_pathway_info` | Pathway details | `pathway_id` |
| `kegg_find_genes` | Find gene in KEGG | `query` |
| `kegg_get_gene_info` | Gene pathway membership | `gene_id` |

**Example - Get pathway context**:
```python
# Find gene in KEGG
kegg_gene = tu.tools.kegg_find_genes(query="hsa:FBN1")
# Get pathway membership
gene_info = tu.tools.kegg_get_gene_info(gene_id="hsa:2200")
# Returns: Pathways containing FBN1
```

### Reactome - Biological Processes

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `reactome_search_pathways` | Search pathways | `query` |
| `reactome_get_pathway` | Pathway details | `pathway_id` |
| `reactome_disease_target_score` | Disease-pathway links | `disease`, `target` |

**Example - Get Reactome pathways**:
```python
# Search for pathways
pathways = tu.tools.reactome_search_pathways(query="TGF-beta signaling")
```

### IntAct - Protein-Protein Interactions

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `intact_search_interactions` | Search interactions | `query`, `species` |
| `intact_get_interaction_network` | Network view | `gene`, `depth` |
| `intact_get_complex_details` | Protein complexes | `complex_id` |

**Example - Get protein interactions**:
```python
# Get interaction partners
interactions = tu.tools.intact_search_interactions(
    query="FBN1",
    species="human"
)
# Returns: Direct interaction partners with confidence scores
```

**Why use it**: Identifies protein complexes and pathways; variants may disrupt protein-protein interactions.

---

## Phase 5: Structure Analysis (NVIDIA NIM)

### Structure Prediction

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_alphafold2` | High-accuracy prediction | `sequence`, `algorithm` |
| `NvidiaNIM_esmfold` | Fast prediction | `sequence` |

**Example - AlphaFold2 prediction**:
```python
structure = tu.tools.NvidiaNIM_alphafold2(
    sequence=protein_sequence,
    algorithm="mmseqs2",
    relax_prediction=False
)
# Returns: PDB structure with pLDDT scores
```

### Domain Annotation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `InterPro_get_protein_domains` | Domain architecture | `accession` |
| `UniProt_get_protein_features` | Sequence features | `accession` |
| `Pfam_get_domains` | Pfam domains | `uniprot_id` |

---

## Phase 6: Literature Evidence (NEW)

### PubMed - Published Literature

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search articles | `query`, `limit` |
| `PubMed_get_article` | Get article details | `pmid` |
| `PubMed_get_related` | Related articles | `pmid` |
| `PubMed_get_cited_by` | Citation tracking | `pmid` |

**Example - Search disease literature**:
```python
# Disease-specific search
papers = tu.tools.PubMed_search_articles(
    query='"Marfan syndrome" AND (FBN1 OR genetics)',
    limit=20
)
```

### BioRxiv/MedRxiv - Preprints

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search preprints (bioRxiv/medRxiv) | `query`, `source='PPR'`, `pageSize` |
| `BioRxiv_get_preprint` | Get preprint by DOI | `doi` |
| `ArXiv_search_papers` | Search ArXiv | `query`, `category`, `limit` |

**Example - Search preprints** (bioRxiv/medRxiv don't have search APIs, use EuropePMC):
```python
# Search for recent preprints
preprints = tu.tools.EuropePMC_search_articles(
    query="Marfan syndrome genetics",
    source="PPR",  # PPR = Preprints only
    pageSize=10
)

# Get full metadata if you have a DOI
if doi_from_results.startswith('10.1101/'):
    full = tu.tools.BioRxiv_get_preprint(doi=doi_from_results)
# Returns: Recent preprints (not peer-reviewed)
```

**⚠️ Important**: Preprints are NOT peer-reviewed. Flag this in reports.

### OpenAlex - Citation Analysis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `openalex_search_works` | Search publications | `query`, `limit` |
| `openalex_get_author` | Author metrics | `author_id` |
| `openalex_literature_search` | Advanced search | `query`, `filters` |

**Example - Citation analysis**:
```python
# Get citation data for paper
work = tu.tools.openalex_search_works(
    query="FBN1 Marfan pathogenic",
    limit=10
)
# Returns: Papers with citation counts, open access status
```

### Semantic Scholar - AI-Enhanced Search

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `SemanticScholar_search_papers` | AI-ranked search | `query`, `limit` |

**Example**:
```python
# AI-enhanced literature search
papers = tu.tools.SemanticScholar_search_papers(
    query="rare disease diagnosis machine learning",
    limit=15
)
```

---

## Workflow Code Examples

### Example 1: Full Phenotype-to-Diagnosis

```python
def diagnose_rare_disease(tu, symptoms, patient_id):
    """Complete rare disease diagnostic workflow."""
    
    # Phase 1: Standardize phenotype
    hpo_terms = []
    for symptom in symptoms:
        results = tu.tools.HPO_search_terms(query=symptom)
        if results:
            hpo_terms.append(results[0])
    
    # Phase 2: Match diseases
    candidate_diseases = []
    for hpo in hpo_terms:
        diseases = tu.tools.HPO_get_term_diseases(hp_id=hpo['id'])
        candidate_diseases.extend(diseases)
    
    # Rank by frequency
    disease_counts = Counter(d['orpha_id'] for d in candidate_diseases)
    top_diseases = disease_counts.most_common(10)
    
    # Phase 3: Build gene panel
    genes = set()
    for orpha_id, count in top_diseases:
        disease_genes = tu.tools.Orphanet_get_disease_genes(orpha_code=orpha_id)
        genes.update(disease_genes)
    
    return {
        'hpo_terms': hpo_terms,
        'candidate_diseases': top_diseases,
        'gene_panel': list(genes)
    }
```

### Example 2: Variant Interpretation

```python
def interpret_variant(tu, variant_hgvs, gene_symbol):
    """Interpret a variant using ACMG criteria."""
    
    evidence = {}
    
    # PM2: Population frequency
    freq = tu.tools.gnomAD_get_variant_frequencies(variant_id=variant_hgvs)
    if freq['allele_frequency'] < 0.00001:
        evidence['PM2'] = {'strength': 'Moderate', 'reason': 'Absent from gnomAD'}
    
    # PP3: Computational predictions
    cadd = tu.tools.CADD_get_scores(variant=variant_hgvs)
    if cadd['phred_score'] > 25:
        evidence['PP3'] = {'strength': 'Supporting', 'reason': f'CADD={cadd["phred_score"]}'}
    
    # ClinVar
    clinvar = tu.tools.ClinVar_search_variants(query=variant_hgvs)
    if clinvar:
        evidence['ClinVar'] = clinvar[0]['clinical_significance']
    
    return evidence
```

### Example 3: Structure Analysis for VUS

```python
def analyze_vus_structure(tu, uniprot_id, variant_position):
    """Structural analysis for variant of uncertain significance."""
    
    # Get protein sequence
    protein = tu.tools.UniProt_get_protein_by_accession(accession=uniprot_id)
    sequence = protein['sequence']
    
    # Predict structure
    structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=sequence,
        algorithm="mmseqs2"
    )
    
    # Get domain annotations
    domains = tu.tools.InterPro_get_protein_domains(accession=uniprot_id)
    
    # Check if variant in domain
    variant_domain = None
    for domain in domains:
        if domain['start'] <= variant_position <= domain['end']:
            variant_domain = domain
            break
    
    return {
        'structure': structure,
        'plddt_at_position': get_plddt(structure, variant_position),
        'domain': variant_domain
    }
```

---

## Fallback Chains

### Disease Matching
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `Orphanet_search_diseases` | `OMIM_search` | `DisGeNET_search_disease` |
| `Orphanet_get_genes` | `OMIM_get_gene_map` | `DisGeNET_get_disease_genes` |
| `OMIM_get_clinical_synopsis` | `Orphanet_get_disease` | `OpenTargets` |
| `DisGeNET_search_gene` | `OpenTargets_diseases` | Literature search |

### Expression & Regulatory
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `CELLxGENE_get_expression_data` | `GTEx_get_median_gene_expression` | `HPA_get_gene_expression` |
| `ChIPAtlas_enrichment_analysis` | `ENCODE_search_experiments` | Literature search |

### Pathway Analysis
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `kegg_get_gene_info` | `reactome_search_pathways` | `OpenTargets_pathways` |
| `intact_search_interactions` | `STRING_interactions` | Literature search |

### Variant Annotation
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `clinvar_get_variant_details` | `gnomAD_get_variant` | Literature search |
| `gnomAD_get_variant_frequencies` | `gnomad_get_variant` | 1000 Genomes |

### Pathogenicity Prediction (ENHANCED)
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `AlphaMissense_get_variant_score` | `CADD_get_variant_score` | `EVE_get_variant_score` |
| `CADD_get_variant_score` | myvariant CADD field | PolyPhen-2 |
| `EVE_get_variant_score` | VEP with EVE plugin | REVEL |

### Structure Prediction
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_alphafold2` | `alphafold_get_prediction` | `NvidiaNIM_esmfold` |
| `InterPro_get_protein_domains` | `Pfam_get_domains` | `UniProt_features` |

### Literature
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PubMed_search_articles` | `EuropePMC_search_articles` | `SemanticScholar_search_papers` |
| `EuropePMC_search_articles` (source='PPR') | `web_search` (site:biorxiv.org) | Skip preprints |
| `openalex_search_works` | `Crossref_search_works` | PubMed |

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `MyGene_query_genes` | `gene="FBN1"` | `q="FBN1"` |
| `clinvar_get_variant_details` | `variant_id=123` | `id=123` |
| `OpenTargets_*` | `ensemblID` | `ensemblId` (camelCase) |
| `GTEx_get_median_gene_expression` | `ensembl_id` | `gencode_id` (versioned) |
| `gnomAD_get_variant_frequencies` | `variant="c.123A>G"` | `variant_id="1-123-A-G"` |

---

## NVIDIA NIM Requirements

**API Key**: `NVIDIA_API_KEY` environment variable required

**Check availability**:
```python
import os
nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))
```

**Rate limits**: 40 RPM (1.5 second minimum between calls)

**Async operations**: AlphaFold2 may return 202, requiring polling:
```python
# Initial call may return 202
result = tu.tools.NvidiaNIM_alphafold2(sequence=seq)
if result.get('status') == 'pending':
    # Poll for completion (handled internally by tool)
    pass
```
