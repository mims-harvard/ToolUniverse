# Clinical Variant Interpreter - Tool Reference

## Core Annotation Tools

### MyVariant.info - Aggregated Annotations

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `MyVariant_query_variants` | Query variant annotations | `variant_id`, `fields` |

**Example - Query variant**:
```python
result = tu.tools.MyVariant_query_variants(
    variant_id="chr17:g.7674220C>T",
    fields="clinvar,gnomad,cadd,dbnsfp"
)
# Returns: ClinVar, gnomAD, CADD, dbNSFP predictions
```

**Key Fields**:
| Field | Contains |
|-------|----------|
| `clinvar` | Classification, review status |
| `gnomad` | Allele frequencies |
| `cadd` | CADD scores |
| `dbnsfp` | SIFT, PolyPhen, REVEL, etc. |

---

### ClinVar - Clinical Classifications

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `clinvar_search_variants` | Search by variant | `variant`, `gene` |
| `clinvar_get_variant` | Get by VCV ID | `variation_id` |

**Example - Search ClinVar**:
```python
result = tu.tools.clinvar_search_variants(
    variant="NM_007294.4:c.5266dupC"
)
# Returns: VCV ID, classification, review status, submitters
```

**Classification Interpretation**:
| ClinVar Status | Stars | Meaning |
|----------------|-------|---------|
| Expert panel | ★★★★ | Highest confidence |
| Practice guideline | ★★★★ | Clinical standard |
| Multiple submitters, criteria | ★★★ | Well-supported |
| Single submitter, criteria | ★★ | Limited evidence |
| Single submitter, no criteria | ★ | Minimal support |

---

### VariantValidator - MANE Transcript Lookup & Variant Validation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `VariantValidator_gene2transcripts` | Get MANE Select/Plus Clinical transcripts for a gene | `gene_symbol`, `transcript_set`, `genome_build` |
| `VariantValidator_validate_variant` | Validate and normalize HGVS variant descriptions | `genome_build`, `variant_description`, `select_transcripts` |

**Example - Get MANE transcript**:
```python
result = tu.tools.VariantValidator_gene2transcripts(
    gene_symbol="TP53", transcript_set="mane", genome_build="GRCh38"
)
# Returns: [{current_symbol: "TP53", transcripts: [{reference: "NM_000546.6",
#   annotations: {mane_select: true, mane_plus_clinical: false}}]}]
```

**Example - Validate variant**:
```python
result = tu.tools.VariantValidator_validate_variant(
    genome_build="GRCh38",
    variant_description="NM_007294.4:c.5266dup",
    select_transcripts="NM_007294.4"
)
# Returns: validated HGVS, protein consequence, genomic coordinates, gene IDs
```

**When to use**:
- Phase 1: Always use `gene2transcripts` to identify the MANE Select transcript before annotating variants
- Phase 1: Use `validate_variant` to normalize user-provided HGVS notation and get cross-genome-build coordinates
- Prefer MANE Select transcript for canonical annotation; fall back to MANE Plus Clinical if relevant

---

### gnomAD - Population Frequencies

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `gnomad_search_variants` | Get allele frequencies | `variant`, `dataset` |

**Example - Query gnomAD**:
```python
result = tu.tools.gnomad_search_variants(
    variant="17-7674220-C-T"
)
# Returns: AF, ancestry-specific AFs, AC, AN, homozygotes
```

**ACMG Frequency Thresholds**:
| Frequency | Code | Application |
|-----------|------|-------------|
| >5% | BA1 | Benign (stand-alone) |
| >1% | BS1 | Strong benign |
| Absent | PM2 | Supporting pathogenic |

**Ancestry-Specific Populations**:
| Code | Population |
|------|------------|
| nfe | European (Non-Finnish) |
| fin | Finnish |
| afr | African/African American |
| amr | Latino/Admixed American |
| eas | East Asian |
| sas | South Asian |
| asj | Ashkenazi Jewish |

---

## ClinGen - Gene Validity & Dosage Sensitivity (NEW)

Authoritative curation of gene-disease relationships from ClinGen.

### Gene Validity

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_gene_validity` | Search validity by gene | `gene` |
| `ClinGen_get_gene_validity` | Get all validity curations | `gene` (optional filter) |

**Example - Check gene-disease validity**:
```python
result = tu.tools.ClinGen_search_gene_validity(gene="BRCA1")
# Returns: Classification (Definitive/Strong/Moderate/Limited), disease, inheritance
```

**Validity Classification Interpretation**:
| Classification | ACMG Impact | Usage |
|----------------|-------------|-------|
| **Definitive** | Supports PS4, PP4 | Strong gene-disease evidence |
| **Strong** | Supports PP4 | Good evidence for classification |
| **Moderate** | Supports PP4 (weak) | Use with caution |
| **Limited** | Do not apply PP4 | Insufficient evidence |
| **Disputed/Refuted** | Contra-evidence | Gene likely NOT causative |

### Dosage Sensitivity

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_dosage_sensitivity` | HI/TS scores by gene | `gene` |
| `ClinGen_get_dosage_sensitivity` | All dosage curations | `gene`, `include_regions` |

**Example - Check haploinsufficiency**:
```python
result = tu.tools.ClinGen_search_dosage_sensitivity(gene="MECP2")
# Returns: Haploinsufficiency Score (0-3), Triplosensitivity Score (0-3)
```

**Dosage Score Interpretation** (for CNVs):
| Score | Meaning | Usage |
|-------|---------|-------|
| **3** | Sufficient evidence | HI/TS established - PVS1 for LOF CNVs |
| **2** | Emerging evidence | Some support |
| **1** | Little evidence | Minimal support |
| **0/40** | No evidence / Dosage unlikely | Unknown or unlikely dosage effect |

### Clinical Actionability

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_search_actionability` | Actionability by gene (both contexts) | `gene` |
| `ClinGen_get_actionability_adult` | Adult actionability | `gene` (optional) |
| `ClinGen_get_actionability_pediatric` | Pediatric actionability | `gene` (optional) |

**Why ClinGen is Critical**:
- Required for **PP4** (phenotype specificity)
- Establishes gene-disease validity before classification
- Dosage scores critical for **PVS1** in CNV interpretation
- Actionability informs return of incidental findings

---

## SpliceAI - Splice Variant Prediction (NEW)

Deep learning model for predicting splice-altering effects.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `SpliceAI_predict_splice` | Full splice prediction | `variant`, `genome`, `distance`, `mask` |
| `SpliceAI_get_max_delta` | Quick max score | `variant`, `genome` |
| `SpliceAI_predict_pangolin` | Pangolin model (alternative) | `variant`, `genome` |

**Example - Predict splice effect**:
```python
# Full prediction
result = tu.tools.SpliceAI_predict_splice(
    variant="chr17-41276045-A-G",
    genome="38"
)
# Returns: DS_AG, DS_AL, DS_DG, DS_DL scores, max_delta_score, interpretation

# Quick triage
quick = tu.tools.SpliceAI_get_max_delta(
    variant="chr17-41276045-A-G"
)
# Returns: max_delta_score, interpretation
```

**Variant Format**: `chr{chrom}-{pos}-{ref}-{alt}` or `{chrom}:{pos}:{ref}:{alt}`

**Delta Score Types**:
| Score | Meaning |
|-------|---------|
| DS_AG | Acceptor Gain (creates new acceptor) |
| DS_AL | Acceptor Loss (disrupts existing) |
| DS_DG | Donor Gain (creates new donor) |
| DS_DL | Donor Loss (disrupts existing) |

**Score Interpretation for ACMG**:
| Max Delta Score | Interpretation | ACMG Support |
|-----------------|----------------|--------------|
| ≥0.8 | High splice impact | PP3 (strong) |
| 0.5-0.8 | Moderate impact | PP3 (supporting) |
| 0.2-0.5 | Low impact | PP3 (weak) |
| <0.2 | Likely no impact | BP7 (if synonymous) |

**When to Use**:
- Intronic variants within ±50bp of splice sites
- Synonymous/missense variants (may still affect splicing)
- Deep intronic variants creating cryptic splice sites
- Validation when functional studies suggest splice defect

---

## Pathogenicity Prediction Tools (NEW)

### CADD - Combined Annotation Dependent Depletion (NEW API)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CADD_get_variant_score` | Get PHRED score for variant | `chrom`, `pos`, `ref`, `alt`, `version` |
| `CADD_get_position_scores` | All substitutions at position | `chrom`, `pos` |
| `CADD_get_range_scores` | Scores in genomic range (max 100bp) | `chrom`, `start`, `end` |

**Example - Score a variant**:
```python
result = tu.tools.CADD_get_variant_score(
    chrom="17",
    pos=7674220,
    ref="G",
    alt="A",
    version="GRCh38-v1.7"  # Options: GRCh38-v1.7, GRCh37-v1.7
)
# Returns: phred_score, raw_score, interpretation
```

**CADD PHRED Score Interpretation**:
| Score | Meaning | ACMG Support |
|-------|---------|--------------|
| ≥30 | Top 0.1% deleterious | PP3 (strong) |
| ≥20 | Top 1% deleterious | PP3 (supporting) |
| 15-20 | Uncertain | Neutral |
| <15 | Likely benign | BP4 (supporting) |

---

### AlphaMissense - DeepMind Pathogenicity Prediction (NEW)

State-of-the-art deep learning model for missense pathogenicity prediction.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `AlphaMissense_get_variant_score` | Score specific variant | `uniprot_id`, `variant` |
| `AlphaMissense_get_residue_scores` | All substitutions at position | `uniprot_id`, `position` |

**Example - Get pathogenicity score**:
```python
result = tu.tools.AlphaMissense_get_variant_score(
    uniprot_id="P00533",  # EGFR
    variant="L858R"  # or "p.L858R"
)
# Returns: pathogenicity_score, classification
```

**AlphaMissense Thresholds** (from Cheng et al., Science 2023):
| Score | Classification | ACMG Support |
|-------|----------------|--------------|
| >0.564 | Pathogenic | PP3 (strong) |
| 0.34-0.564 | Ambiguous | Neutral |
| <0.34 | Benign | BP4 (strong) |

**Why Use AlphaMissense**:
- ~90% accuracy on ClinVar pathogenic variants
- Covers all ~71 million possible human missense variants
- Trained on evolutionary data, not clinical annotations

---

### EVE - Evolutionary Variant Effect (NEW)

Unsupervised deep learning model using evolutionary data (Harvard/Oxford).

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EVE_get_variant_score` | Get EVE score via VEP | `chrom`, `pos`, `ref`, `alt` OR `variant` (HGVS) |
| `EVE_get_gene_info` | Check if gene has EVE coverage | `gene_symbol` |

**Example - Score variant**:
```python
# Via genomic coordinates
result = tu.tools.EVE_get_variant_score(
    chrom="17",
    pos=7674220,
    ref="C",
    alt="T"
)

# Or via HGVS
result = tu.tools.EVE_get_variant_score(
    variant="ENST00000269305.4:c.100G>A"
)
# Returns: eve_score, classification, gene, polyphen/sift from VEP
```

**EVE Score Interpretation**:
| Score | Classification | ACMG Support |
|-------|----------------|--------------|
| >0.5 | Likely pathogenic | PP3 |
| ≤0.5 | Likely benign | BP4 |

**Note**: EVE covers ~3,000 disease-related genes. Use `EVE_get_gene_info` to check coverage.

---

### Integrating Prediction Tools

**Best Practice for VUS Classification**:

```python
def get_multi_predictor_evidence(tu, variant_info):
    """
    Combine multiple predictors for robust PP3/BP4 assignment.
    """
    evidence = []
    
    # 1. CADD (all variants)
    cadd = tu.tools.CADD_get_variant_score(
        chrom=variant_info['chrom'],
        pos=variant_info['pos'],
        ref=variant_info['ref'],
        alt=variant_info['alt']
    )
    if cadd.get('status') == 'success':
        score = cadd['data']['phred_score']
        evidence.append({
            'tool': 'CADD',
            'score': score,
            'damaging': score >= 20
        })
    
    # 2. AlphaMissense (missense only)
    if variant_info.get('uniprot_id') and variant_info.get('aa_change'):
        am = tu.tools.AlphaMissense_get_variant_score(
            uniprot_id=variant_info['uniprot_id'],
            variant=variant_info['aa_change']
        )
        if am.get('status') == 'success' and am.get('data'):
            evidence.append({
                'tool': 'AlphaMissense',
                'score': am['data'].get('pathogenicity_score'),
                'classification': am['data'].get('classification'),
                'damaging': am['data'].get('classification') == 'pathogenic'
            })
    
    # 3. EVE (via VEP)
    eve = tu.tools.EVE_get_variant_score(
        chrom=variant_info['chrom'],
        pos=variant_info['pos'],
        ref=variant_info['ref'],
        alt=variant_info['alt']
    )
    if eve.get('status') == 'success':
        eve_scores = eve['data'].get('eve_scores', [])
        if eve_scores:
            evidence.append({
                'tool': 'EVE',
                'score': eve_scores[0].get('eve_score'),
                'damaging': eve_scores[0].get('eve_score', 0) > 0.5
            })
    
    # Consensus
    damaging = sum(1 for e in evidence if e.get('damaging'))
    benign = sum(1 for e in evidence if not e.get('damaging'))
    
    return {
        'predictions': evidence,
        'damaging_count': damaging,
        'benign_count': benign,
        'acmg_pp3': damaging >= 2 and benign == 0,
        'acmg_bp4': benign >= 2 and damaging == 0
    }
```

---

## Somatic & Disease Association Tools (NEW)

### COSMIC - Somatic Cancer Mutations

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `COSMIC_search_mutations` | Search mutations | `operation="search"`, `terms`, `max_results` |
| `COSMIC_get_mutations_by_gene` | Gene mutations | `operation="get_by_gene"`, `gene`, `genome_build` |

**Example - Check if variant is somatic hotspot**:
```python
# Search for specific mutation
result = tu.tools.COSMIC_search_mutations(
    operation="search",
    terms="BRAF V600E",
    max_results=20
)
# Returns: mutation_id, cancer types, frequency

# Get all mutations for gene (hotspot analysis)
gene_muts = tu.tools.COSMIC_get_mutations_by_gene(
    operation="get_by_gene",
    gene="BRAF",
    max_results=200
)
# Returns: All mutations with cancer type distribution
```

**COSMIC Evidence for ACMG**:
| Finding | ACMG Code | Application |
|---------|-----------|-------------|
| Recurrent somatic hotspot | PS3 | Functional evidence |
| Frequent in COSMIC (>100) | PM1 | Hotspot/functional domain |
| Rare in COSMIC | - | Consider other evidence |

### OMIM - Mendelian Disease Context

**⚠️ Requires**: `OMIM_API_KEY` environment variable

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OMIM_search` | Search genes/diseases | `operation="search"`, `query`, `limit` |
| `OMIM_get_entry` | Detailed entry | `operation="get_entry"`, `mim_number` |
| `OMIM_get_clinical_synopsis` | Clinical features | `operation="get_clinical_synopsis"`, `mim_number` |
| `OMIM_get_gene_map` | Gene-disease map | `operation="get_gene_map"`, `mim_number` |

**Example - Get gene-disease context**:
```python
# Search for gene in OMIM
search = tu.tools.OMIM_search(
    operation="search",
    query="BRCA1",
    limit=5
)

# Get detailed entry with clinical info
entry = tu.tools.OMIM_get_entry(
    operation="get_entry",
    mim_number="113705"  # BRCA1
)

# Get clinical synopsis for phenotype matching
synopsis = tu.tools.OMIM_get_clinical_synopsis(
    operation="get_clinical_synopsis",
    mim_number="114480"  # Breast-ovarian cancer
)
```

**OMIM Entry Types**:
| Prefix | Type | Example |
|--------|------|---------|
| * | Gene | *113705 (BRCA1) |
| # | Phenotype with known gene | #114480 (BRCA1 cancer) |
| % | Phenotype, unknown molecular basis | Mapped locus only |
| + | Gene and phenotype combined | Historical entries |

### DisGeNET - Gene-Disease Associations

**⚠️ Requires**: `DISGENET_API_KEY` environment variable

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DisGeNET_search_gene` | Diseases for gene | `operation="search_gene"`, `gene`, `limit` |
| `DisGeNET_search_disease` | Genes for disease | `operation="search_disease"`, `disease` |
| `DisGeNET_get_gda` | Curated associations | `operation="get_gda"`, `gene`, `source`, `min_score` |
| `DisGeNET_get_vda` | Variant-disease | `operation="get_vda"`, `variant` or `gene` |

**Example - Get gene-disease evidence**:
```python
# Gene-disease associations
gda = tu.tools.DisGeNET_search_gene(
    operation="search_gene",
    gene="BRCA1",
    limit=20
)
# Returns: Associated diseases with scores

# High-confidence curated associations
curated = tu.tools.DisGeNET_get_gda(
    operation="get_gda",
    gene="BRCA1",
    source="CURATED",
    min_score=0.5
)

# Variant-disease associations
vda = tu.tools.DisGeNET_get_vda(
    operation="get_vda",
    gene="BRCA1",
    limit=30
)
```

**DisGeNET Score for ACMG**:
| Score | Strength | ACMG Code |
|-------|----------|-----------|
| >0.7 | Strong gene-disease | PP4 (phenotype specific) |
| 0.4-0.7 | Moderate evidence | Supporting |
| <0.4 | Weak/Literature only | Insufficient |

---

## Regulatory Context Tools (NEW)

### ChIPAtlas - Transcription Factor Binding

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChIPAtlas_enrichment_analysis` | TF binding enrichment | `gene`, `cell_type` |
| `ChIPAtlas_get_peak_data` | ChIP-seq peaks | `gene`, `experiment_type` |
| `ChIPAtlas_search_datasets` | Find experiments | `antigen`, `cell_type` |

**Example - Check TF binding at variant**:
```python
# Get TF binding near gene
tf_binding = tu.tools.ChIPAtlas_enrichment_analysis(
    gene="BRCA1",
    cell_type="all"
)
# Returns: TFs with binding peaks near gene

# Get specific peaks
peaks = tu.tools.ChIPAtlas_get_peak_data(
    gene="BRCA1",
    experiment_type="TF"
)
```

**Use for**: Non-coding variants that may disrupt TF binding sites

### ENCODE - Regulatory Elements

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ENCODE_search_experiments` | Find regulatory data | `assay_title`, `biosample` |
| `ENCODE_get_experiment` | Experiment details | `accession` |
| `ENCODE_get_biosample` | Sample annotations | `accession` |

**Example - Get regulatory annotations**:
```python
# Search for regulatory data near variant
experiments = tu.tools.ENCODE_search_experiments(
    assay_title="ATAC-seq",
    biosample="heart"
)
# Returns: Open chromatin experiments
```

**Key ENCODE Assays**:
| Assay | Purpose | Relevance |
|-------|---------|-----------|
| ATAC-seq | Open chromatin | Accessible regions |
| H3K27ac | Active enhancers | Regulatory activity |
| H3K4me3 | Active promoters | Promoter regions |
| CTCF | Insulator binding | Chromatin structure |

---

## Expression Context Tools (NEW)

### CELLxGENE - Single-Cell Expression

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `CELLxGENE_get_expression_data` | Cell-type expression | `gene`, `tissue` |
| `CELLxGENE_get_cell_metadata` | Cell annotations | `gene` |

**Example - Validate tissue expression**:
```python
# Get expression in disease-relevant tissue
expression = tu.tools.CELLxGENE_get_expression_data(
    gene="FBN1",
    tissue="heart"
)
# Returns: Expression per cell type (cardiomyocytes, fibroblasts, etc.)
```

**Why use it**: Confirms gene is expressed in phenotype-relevant cells

---

## Literature Tools (ENHANCED)

### BioRxiv/MedRxiv - Preprints

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search preprints (bioRxiv/medRxiv) | `query`, `source='PPR'`, `pageSize` |
| `BioRxiv_get_preprint` | Get preprint by DOI | `doi` |

**Example - Search preprints** (bioRxiv/medRxiv don't have search APIs, use EuropePMC):
```python
# Search for recent findings
preprints = tu.tools.EuropePMC_search_articles(
    query="BRCA1 variant functional",
    source="PPR",  # PPR = Preprints only
    pageSize=10
)
```

**⚠️ Important**: Always flag preprints as NOT peer-reviewed

### OpenAlex - Citation Analysis

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `openalex_search_works` | Search with citations | `query`, `limit` |

**Example - Get citation counts**:
```python
# Get citation metrics for key paper
work = tu.tools.openalex_search_works(
    query="BRCA1 functional study pathogenic",
    limit=5
)
# Returns: Papers with cited_by_count, is_oa, etc.
```

### Semantic Scholar - AI-Ranked Search

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `SemanticScholar_search_papers` | AI-ranked search | `query`, `limit` |

**Example**:
```python
papers = tu.tools.SemanticScholar_search_papers(
    query="BRCA1 c.5266dupC pathogenic",
    limit=15
)
```

---

### Ensembl - Variant Effect Predictor

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EnsemblVar_get_variant_consequences` | VEP annotations | `variant_id` |
| `Ensembl_get_gene_info` | Gene details | `gene_id` |

**Example - Get VEP data**:
```python
result = tu.tools.EnsemblVar_get_variant_consequences(
    variant_id="rs28934576"
)
# Returns: Consequence, transcript, SIFT, PolyPhen
```

---

## Disease Association Tools

### OMIM - Gene-Disease Relationships

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OMIM_search` | Search by gene/disease | `query` |
| `OMIM_get_entry` | Get MIM entry | `mim_number` |

**Example - Get OMIM associations**:
```python
result = tu.tools.OMIM_search(query="BRCA1")
# Returns: MIM#, gene-phenotype relationships, inheritance
```

---

### ClinGen - Gene Validity

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ClinGen_gene_validity` | Get curation status | `gene` |
| `ClinGen_dosage` | Dosage sensitivity | `gene` |

**Gene Validity Levels**:
| Level | Meaning |
|-------|---------|
| Definitive | Strong evidence, replicated |
| Strong | Considerable evidence |
| Moderate | Some evidence |
| Limited | Minimal evidence |
| Disputed | Conflicting evidence |
| Refuted | Evidence against |

---

## Structural Analysis Tools

### PDB - Experimental Structures

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PDBe_get_uniprot_mappings` | Find structures | `uniprot_id` |
| `RCSBData_get_entry` | Download PDB | `pdb_id` |

**Example - Get structure**:
```python
# Find PDB structures for TP53
hits = tu.tools.PDBe_get_uniprot_mappings(uniprot_id="P04637")
if hits:
    structure = tu.tools.PDB_get_structure(pdb_id=hits[0]['pdb_id'])
```

### AlphaFold - Predicted Structures

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `alphafold_get_prediction` | Get AF DB prediction | `accession` |
| `NvidiaNIM_alphafold2` | Predict de novo | `sequence`, `algorithm` |

**Example - Get AlphaFold structure**:
```python
# From AlphaFold DB
structure = tu.tools.alphafold_get_prediction(accession="P04637")

# Or predict de novo
structure = tu.tools.NvidiaNIM_alphafold2(
    sequence=protein_sequence,
    algorithm="mmseqs2"
)
```

**pLDDT Interpretation**:
| Score | Confidence | Use for Variant |
|-------|------------|-----------------|
| >90 | Very high | Reliable position assessment |
| 70-90 | High | Reliable |
| 50-70 | Moderate | Use with caution |
| <50 | Low | Likely disordered |

---

### Domain/Function Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `InterPro_get_protein_domains` | Domain annotations | `accession` |
| `UniProt_get_function_by_accession` | Functional sites | `accession` |

**Example - Get domains**:
```python
domains = tu.tools.InterPro_get_protein_domains(accession="P04637")
# Returns: Domain boundaries, types, functions
```

---

## Literature Tools

### PubMed - Literature Search

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search articles | `query`, `max_results` |
| `PubMed_get_abstract` | Get abstract | `pmid` |

**Example - Search for functional studies**:
```python
# Gene + variant search
result = tu.tools.PubMed_search_articles(
    query="BRCA1 AND c.5266dupC",
    max_results=10
)

# Functional studies
result = tu.tools.PubMed_search_articles(
    query="BRCA1 AND functional study",
    max_results=20
)
```

**Search Strategies**:
| Strategy | Query Pattern |
|----------|---------------|
| Specific variant | `"{GENE} AND ({HGVS} OR {legacy})"` |
| Functional | `"{GENE} AND (functional study OR mutagenesis)"` |
| Clinical | `"{GENE} AND case report AND {phenotype}"` |
| Review | `"{GENE} AND review[pt]"` |

---

## Workflow Code Examples

### Example 1: Complete Variant Annotation

```python
def annotate_variant(tu, variant_hgvs, gene):
    """Complete variant annotation workflow."""
    
    # Phase 1: Get aggregated annotations
    annotations = tu.tools.MyVariant_query_variants(
        variant_id=variant_hgvs,
        fields="clinvar,gnomad,cadd,dbnsfp"
    )
    
    # Phase 2: ClinVar detail
    clinvar = tu.tools.clinvar_search_variants(variant=variant_hgvs)
    
    # Phase 3: Population frequency
    gnomad = tu.tools.gnomad_search_variants(variant=variant_hgvs)
    
    # Phase 4: Gene context
    omim = tu.tools.OMIM_search(query=gene)
    
    # Phase 5: Literature
    literature = tu.tools.PubMed_search_articles(
        query=f"{gene} AND {variant_hgvs}",
        max_results=20
    )
    
    return {
        'annotations': annotations,
        'clinvar': clinvar,
        'gnomad': gnomad,
        'omim': omim,
        'literature': literature
    }
```

### Example 2: Structural Analysis for VUS

```python
def structural_analysis_for_vus(tu, gene, uniprot_id, residue_position):
    """Structural analysis for VUS missense variants."""
    
    # Try PDB first
    pdb_structures = tu.tools.PDBe_get_uniprot_mappings(uniprot_id=uniprot_id)
    
    if pdb_structures:
        # Use best resolution experimental structure
        best_pdb = sorted(pdb_structures, key=lambda x: x.get('resolution', 10))[0]
        structure = tu.tools.PDB_get_structure(pdb_id=best_pdb['pdb_id'])
        structure_source = f"PDB {best_pdb['pdb_id']}"
    else:
        # Fallback to AlphaFold
        structure = tu.tools.alphafold_get_prediction(accession=uniprot_id)
        structure_source = "AlphaFold DB"
    
    # Get domain information
    domains = tu.tools.InterPro_get_protein_domains(accession=uniprot_id)
    
    # Get functional sites
    functions = tu.tools.UniProt_get_function_by_accession(accession=uniprot_id)
    
    # Analyze residue context
    analysis = {
        'structure_source': structure_source,
        'domains': identify_domain(domains, residue_position),
        'functional_sites': find_nearby_sites(functions, residue_position),
        'pm1_applicable': assess_pm1(domains, functions, residue_position)
    }
    
    return analysis
```

### Example 3: ACMG Classification

```python
def calculate_acmg_classification(evidence_codes):
    """Calculate ACMG classification from evidence codes."""
    
    # Count evidence
    pathogenic = {
        'very_strong': [],
        'strong': [],
        'moderate': [],
        'supporting': []
    }
    benign = {
        'stand_alone': [],
        'strong': [],
        'supporting': []
    }
    
    for code, strength in evidence_codes:
        if code.startswith(('PVS', 'PS', 'PM', 'PP')):
            # Pathogenic evidence
            if strength == 'very_strong':
                pathogenic['very_strong'].append(code)
            elif strength == 'strong':
                pathogenic['strong'].append(code)
            elif strength == 'moderate':
                pathogenic['moderate'].append(code)
            else:
                pathogenic['supporting'].append(code)
        else:
            # Benign evidence
            if code == 'BA1':
                benign['stand_alone'].append(code)
            elif strength == 'strong':
                benign['strong'].append(code)
            else:
                benign['supporting'].append(code)
    
    # Apply ACMG rules
    if benign['stand_alone']:
        return 'Benign'
    
    if len(benign['strong']) >= 2:
        return 'Benign'
    
    vs = len(pathogenic['very_strong'])
    s = len(pathogenic['strong'])
    m = len(pathogenic['moderate'])
    p = len(pathogenic['supporting'])
    
    if (vs >= 1 and (s >= 1 or m >= 1 or m >= 2 or p >= 2)) or \
       (s >= 2) or \
       (s >= 1 and m >= 3):
        return 'Pathogenic'
    
    if (vs >= 1 and m >= 1) or \
       (s >= 1 and m >= 1 or m >= 2) or \
       (s >= 1 and p >= 2):
        return 'Likely Pathogenic'
    
    if len(benign['strong']) >= 1 and len(benign['supporting']) >= 1:
        return 'Likely Benign'
    
    return 'VUS'
```

---

## Fallback Chains

### Variant Annotations
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `MyVariant_query_variants` | `clinvar_search_variants` + `gnomad_search_variants` | Direct database queries |

### Structure
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PDBe_get_uniprot_mappings` | `alphafold_get_prediction` | `NvidiaNIM_alphafold2` |

### Gene Information
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `OMIM_search` | `NCBIGene_search` | `Ensembl_get_gene_info` |

### Literature
| Primary | Fallback 1 |
|---------|------------|
| `PubMed_search_articles` | `EuropePMC_search_articles` |

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `MyVariant_query_variants` | `id="rs123"` | `variant_id="rs123"` |
| `clinvar_search_variants` | `gene="BRCA1:c.123"` | `variant="NM_007294.4:c.123A>G"` |
| `gnomad_search_variants` | `variant="c.123A>G"` | `variant="17-41245466-A-G"` |
| `alphafold_get_prediction` | `uniprot="P04637"` | `accession="P04637"` |

---

## ACMG Code Quick Reference

### Pathogenic Codes
| Code | Strength | Trigger |
|------|----------|---------|
| PVS1 | Very Strong | Null in LOF gene |
| PS1 | Strong | Same AA as pathogenic |
| PS2 | Strong | De novo (confirmed) |
| PS3 | Strong | Functional studies |
| PS4 | Strong | Prevalence in affected |
| PM1 | Moderate | Functional domain |
| PM2 | Moderate | Absent from controls |
| PM3 | Moderate | Trans with pathogenic |
| PM4 | Moderate | Protein length change |
| PM5 | Moderate | Novel at known position |
| PM6 | Moderate | De novo (unconfirmed) |
| PP1 | Supporting | Segregation |
| PP2 | Supporting | Low missense rate gene |
| PP3 | Supporting | Computational predictions |
| PP4 | Supporting | Phenotype specific |
| PP5 | Supporting | Reputable source |

### Benign Codes
| Code | Strength | Trigger |
|------|----------|---------|
| BA1 | Stand-alone | MAF >5% |
| BS1 | Strong | High frequency |
| BS2 | Strong | Homozygotes healthy |
| BS3 | Strong | No functional effect |
| BS4 | Strong | No segregation |
| BP1 | Supporting | Missense in LOF gene |
| BP2 | Supporting | Observed trans |
| BP3 | Supporting | In-frame, no function |
| BP4 | Supporting | Benign predictions |
| BP5 | Supporting | Alternate explanation |
| BP6 | Supporting | Reputable source |
| BP7 | Supporting | Synonymous |

---

## Quality Thresholds

### Computational Predictions (Updated)
| Predictor | Damaging | Uncertain | Benign |
|-----------|----------|-----------|--------|
| **AlphaMissense** | >0.564 | 0.34-0.564 | <0.34 |
| **CADD PHRED** | ≥20 | 15-20 | <15 |
| **EVE** | >0.5 | - | ≤0.5 |
| SIFT | <0.05 | 0.05-0.15 | >0.15 |
| PolyPhen-2 | >0.85 | 0.15-0.85 | <0.15 |
| REVEL | >0.75 | 0.5-0.75 | <0.5 |

**Recommended Order of Use**:
1. AlphaMissense (highest accuracy for missense, ~90%)
2. CADD (works for all variant types)
3. EVE (unsupervised, complements AlphaMissense)
4. SIFT/PolyPhen (legacy, for comparison)

### Concordance for PP3/BP4
| Predictors Agreeing | ACMG Application |
|---------------------|------------------|
| All damaging (≥3) | PP3 (supporting pathogenic) |
| All benign (≥3) | BP4 (supporting benign) |
| Mixed | Neither |

---

## Rate Limits

| Tool | Limit |
|------|-------|
| NVIDIA NIM tools | 40 RPM |
| PubMed | 3 requests/second |
| Ensembl | 15 requests/second |

Handle with appropriate delays between calls.
