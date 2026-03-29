---
name: Microbiome Research
description: Analyze microbiome and metagenomics data using MGnify, GTDB, ENA, and literature tools. Search studies by biome/keyword, retrieve taxonomic profiles and functional annotations, classify genomes with GTDB taxonomy, and find related publications. Use for human gut microbiome, soil/ocean metagenomics, and environmental microbiology research.
---

# Microbiome Research with ToolUniverse

Comprehensive microbiome analysis using MGnify (EBI metagenomics), GTDB (genome taxonomy), ENA (sequencing data), OLS (ontology lookup for ENVO biomes), and EuropePMC (literature).

## Core Tools

| Tool | Purpose | Auth |
|------|---------|------|
| **MGnify_search_studies** | Find metagenomics studies by biome/keyword | None |
| **MGnify_search_studies_detail** | Study metadata, abstract, sample counts | None |
| **MGnify_list_analyses** | List taxonomic/functional analysis outputs for a study | None |
| **MGnify_get_taxonomy** | Taxonomic composition from an analysis | None |
| **MGnify_get_go_terms** | GO functional annotations from an analysis | None |
| **MGnify_get_interpro** | InterPro protein domain annotations | None |
| **MGnify_list_biomes** | Browse MGnify biome hierarchy | None |
| **MGnify_search_genomes** | Search metagenome-assembled genomes (MAGs) | None |
| **MGnify_get_genome** | Genome quality metrics (completeness, contamination) | None |
| **GTDB_search_genomes** | Search bacterial/archaeal genomes by taxonomy | None |
| **GTDB_get_species** | Species cluster details from GTDB | None |
| **GTDB_get_taxon_info** | Taxonomic rank info in GTDB hierarchy | None |
| **GTDB_search_taxon** | Search taxa by partial name across all ranks | None |
| **ENAPortal_search_studies** | Find sequencing studies in ENA. Query format: `description="keyword"` | None |
| **ENAPortal_search_samples** | Find samples with environmental metadata | None |
| **ols_search_terms** | Search ENVO ontology for biome/environment terms | None |
| **EuropePMC_search_articles** | Find microbiome publications | None |
| **PubMed_search_articles** | Literature search (different coverage than EuropePMC) | None |

**For drug-microbiome studies**, also use:
- `PubChem_get_CID_by_compound_name` / `PubChem_get_compound_properties_by_CID` — drug identity
- `CTD_get_chemical_gene_interactions` — drug-gene interactions (e.g., metformin affects 1,175+ genes)
- `kegg_search_pathway` / `kegg_get_pathway_info` — microbial metabolic pathways (butanoate, propanoate)
- `ReactomeAnalysis_pathway_enrichment` — host pathway enrichment for drug-affected genes
- `drugbank_vocab_search` — drug mechanism and targets

> **MGnify tip**: Use concise single-keyword searches (e.g., "metformin") — multi-word queries may timeout. The MGnify API can be slow for broad searches.

## Quick Start

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# 1. Search for gut microbiome studies
studies = tu.run_one_function({
    'name': 'MGnify_search_studies',
    'arguments': {'search': 'gut microbiome', 'size': 5}
})

# 2. Get study details
detail = tu.run_one_function({
    'name': 'MGnify_search_studies_detail',
    'arguments': {'study_accession': 'MGYS00006860'}
})

# 3. List analyses for a study
analyses = tu.run_one_function({
    'name': 'MGnify_list_analyses',
    'arguments': {'study_accession': 'MGYS00006860', 'size': 5}
})

# 4. Get taxonomic profile from an analysis
taxonomy = tu.run_one_function({
    'name': 'MGnify_get_taxonomy',
    'arguments': {'analysis_accession': 'MGYA00612683'}
})

# 5. Get functional annotations
go_terms = tu.run_one_function({
    'name': 'MGnify_get_go_terms',
    'arguments': {'analysis_accession': 'MGYA00612683'}
})
```

## Common Workflows

### Workflow 1: Study Discovery by Environment

Find studies for a specific biome using MGnify's biome hierarchy:

```python
# Browse biome hierarchy
biomes = tu.run_one_function({
    'name': 'MGnify_list_biomes',
    'arguments': {'lineage': 'root:Host-associated:Human', 'depth': 3}
})

# Search studies in a specific biome
studies = tu.run_one_function({
    'name': 'MGnify_search_studies',
    'arguments': {'biome': 'root:Host-associated:Human:Digestive system', 'size': 10}
})

# Look up ENVO ontology terms for environment metadata
envo = tu.run_one_function({
    'name': 'ols_search_terms',
    'arguments': {'query': 'human gut', 'ontology': 'envo', 'rows': 5}
})
```

### Workflow 2: Taxonomic Profiling

Get the microbial composition of a metagenomics sample:

```python
# Get analyses for a study
analyses = tu.run_one_function({
    'name': 'MGnify_list_analyses',
    'arguments': {'study_accession': 'MGYS00006860', 'size': 3}
})

# Get taxonomy for a specific analysis
taxonomy = tu.run_one_function({
    'name': 'MGnify_get_taxonomy',
    'arguments': {'analysis_accession': 'MGYA00612683'}
})
# Returns organisms with lineage, abundance counts, and taxonomy rank
```

### Workflow 3: Genome Quality Assessment

Evaluate metagenome-assembled genomes (MAGs):

```python
# Search for genomes from a specific taxon
genomes = tu.run_one_function({
    'name': 'MGnify_search_genomes',
    'arguments': {'search': 'Faecalibacterium prausnitzii', 'size': 5}
})

# Get quality metrics for a genome
genome = tu.run_one_function({
    'name': 'MGnify_get_genome',
    'arguments': {'genome_accession': 'MGYG000000001'}
})
# Returns completeness, contamination, N50, genome length, taxonomy

# Cross-reference with GTDB taxonomy
gtdb = tu.run_one_function({
    'name': 'GTDB_search_genomes',
    'arguments': {'operation': 'search_genomes', 'query': 'Faecalibacterium', 'items_per_page': 5}
})
```

### Workflow 4: Functional Annotation

Discover functional potential of a metagenome:

```python
# GO terms from an analysis
go_terms = tu.run_one_function({
    'name': 'MGnify_get_go_terms',
    'arguments': {'analysis_accession': 'MGYA00612683'}
})

# InterPro domains
interpro = tu.run_one_function({
    'name': 'MGnify_get_interpro',
    'arguments': {'analysis_accession': 'MGYA00612683'}
})
```

### Workflow 5: Literature Integration

Combine metagenomics data with published research:

```python
# Find relevant publications
papers = tu.run_one_function({
    'name': 'EuropePMC_search_articles',
    'arguments': {'query': 'gut microbiome AND Faecalibacterium AND (IBD OR "Crohn")', 'limit': 10}
})

# Find sequencing data in ENA
ena_studies = tu.run_one_function({
    'name': 'ENAPortal_search_studies',
    'arguments': {'query': 'description="gut microbiome 16S"', 'limit': 5}
})
```

## MGnify Biome Hierarchy

Key biome lineages (use `MGnify_list_biomes` to discover others):
- Human gut: `root:Host-associated:Human:Digestive system`
- Human oral/skin: `root:Host-associated:Human:Oral` / `root:Host-associated:Human:Skin`
- Soil: `root:Environmental:Terrestrial:Soil`
- Ocean/Freshwater: `root:Environmental:Aquatic:Marine` / `root:Environmental:Aquatic:Freshwater`
- Wastewater: `root:Engineered:Wastewater`

## Key Identifiers

MGnify: studies=`MGYS*`, analyses=`MGYA*`, genomes=`MGYG*`. ENA studies=`PRJEB*`. GTDB genomes=`GCA_*`. ENVO terms=`ENVO:*` (e.g. ENVO:00002041).

## Reasoning Framework

### Starting Point: Define the Question First

Microbiome analysis starts with: what is the question? LOOK UP DON'T GUESS — always check the study type and sequencing method before interpreting results.

**Decision tree for data type:**
- Community composition (who is there?) → 16S/ITS amplicon → alpha/beta diversity, differential abundance
- Functional potential (what can they do?) → Shotgun metagenomics → MGnify GO terms, InterPro, KEGG pathways
- Active function (what are they doing now?) → Metatranscriptomics → specialized pipelines (not MGnify/GTDB alone)

Before calling any tool, determine which data type the user has via `MGnify_search_studies_detail` — the pipeline type (amplicon vs shotgun) determines which analyses are valid. Do not apply 16S diversity metrics to metagenomic data or vice versa.

### Dysbiosis Assessment Strategy

Dysbiosis (microbial imbalance) is context-dependent — there is no universal "healthy" microbiome. LOOK UP DON'T GUESS — compare to study-matched controls, not general population references.

1. **Check alpha diversity**: Reduced Shannon index relative to controls suggests dysbiosis. Use `MGnify_get_taxonomy` to get community profiles, then assess richness and evenness.
2. **Identify keystone taxa shifts**: Loss of known beneficial taxa (e.g., Faecalibacterium, Roseburia in gut) or bloom of pathobionts (e.g., Enterobacteriaceae). LOOK UP taxa roles with `GTDB_get_species` and literature via `EuropePMC_search_articles`.
3. **Functional consequences**: Does taxonomic shift correlate with loss/gain of metabolic pathways? Check `MGnify_get_go_terms` and `MGnify_get_interpro` for the affected samples.
4. **Confounders**: Antibiotics, diet, age, and geography all affect microbiome composition. A dysbiosis claim requires controlling for these factors or acknowledging them as limitations.

### Taxonomic vs Functional Analysis: When to Use Each

- **Taxonomic analysis alone** is sufficient when the question is "which organisms are present?" or "does community composition differ between groups?" Use `MGnify_get_taxonomy` + `GTDB_search_genomes`.
- **Functional analysis** is needed when the question is "what metabolic capabilities differ?" or "why does a taxonomic shift matter?" Use `MGnify_get_go_terms` + `MGnify_get_interpro` + `kegg_search_pathway`.
- **Both together** when linking organisms to functions (e.g., "which taxa drive butyrate production in healthy vs IBD gut?"). Cross-reference taxonomic profiles with functional annotations from the same MGnify analysis.

### Evidence Grading

| Tier | Description | Example |
|------|-------------|---------|
| **T1** | Replicated finding across multiple cohorts with consistent effect | Reduced Faecalibacterium in IBD (>10 independent studies) |
| **T2** | Single well-powered study (n > 100) with appropriate controls | Metformin-associated Akkermansia enrichment in a controlled trial |
| **T3** | Pilot study or observational association, small sample size | Taxonomic shift in n=15 case-control, no validation cohort |
| **T4** | Computational prediction or single-sample observation | Novel MAG with predicted function, no culture confirmation |

### Interpretation Guidance

**Alpha diversity (within-sample)**: Shannon index measures richness and evenness. Higher Shannon (>3.0 for gut) suggests a stable community. Reduced alpha diversity is associated with dysbiosis (IBD, antibiotics). Always compare to study-matched controls — diversity varies by body site, sequencing depth, and geography.

**Beta diversity (between-sample)**: Bray-Curtis (abundance-based) or UniFrac (phylogenetic). PERMANOVA p < 0.05 with R-squared > 0.05 indicates condition-driven clustering. Low R-squared (<0.02) even with significant p suggests the effect is small relative to inter-individual variation. Choose weighted UniFrac when abundant taxa matter most; unweighted when rare taxa are important.

**Taxonomic composition**: Relative abundance at phylum level (Firmicutes/Bacteroidetes ratio) is a coarse indicator; genus- or species-level resolution is preferred. A taxon present at >1% relative abundance in multiple samples is reliably detected. Taxa at <0.1% may be noise or sequencing artifacts. GTDB taxonomy may reclassify NCBI names (e.g., Firmicutes split into multiple phyla).

**Functional profiling**: GO terms and InterPro domains from MGnify reflect the metabolic potential (not necessarily activity) of the community. Enrichment of specific pathways (e.g., butyrate production, LPS biosynthesis) should be interpreted alongside taxonomic data to identify which organisms contribute the functions.

### Synthesis Questions

A complete microbiome report should answer:
1. How does alpha diversity compare between conditions, and is the difference significant?
2. Does beta diversity analysis show condition-driven clustering (PERMANOVA)?
3. Which taxa are differentially abundant, and are they known commensals or pathobionts?
4. What functional pathways are enriched, and which taxa likely drive them?
5. How do findings compare to published studies for the same biome/condition (literature context)?

## Tips

- MGnify study accessions start with `MGYS`, analyses with `MGYA`, genomes with `MGYG`
- Use `MGnify_list_biomes` first to find the correct biome lineage string
- `MGnify_get_taxonomy` returns phylum-level to species-level composition
- GTDB provides standardized bacterial/archaeal taxonomy (differs from NCBI in some lineages)
- For 16S amplicon studies, taxonomy is the primary output; for shotgun metagenomics, both taxonomy and functional annotations are available
- The `size` parameter in MGnify tools controls results per page (max 100)
