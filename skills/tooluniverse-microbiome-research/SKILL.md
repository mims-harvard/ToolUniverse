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
| **MGnify_get_study_detail** | Study metadata, abstract, sample counts | None |
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
    'name': 'MGnify_get_study_detail',
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

Key biome lineages for common research areas:

| Research Area | Biome Lineage |
|--------------|---------------|
| Human gut | `root:Host-associated:Human:Digestive system` |
| Human oral | `root:Host-associated:Human:Oral` |
| Human skin | `root:Host-associated:Human:Skin` |
| Soil | `root:Environmental:Terrestrial:Soil` |
| Ocean surface | `root:Environmental:Aquatic:Marine` |
| Freshwater | `root:Environmental:Aquatic:Freshwater` |
| Wastewater | `root:Engineered:Wastewater` |
| Food/fermented | `root:Engineered:Food production` |

## Key Identifiers

| ID Type | Example | Used By |
|---------|---------|---------|
| MGnify study | MGYS00006860 | MGnify_search_studies, MGnify_get_study_detail |
| MGnify analysis | MGYA00612683 | MGnify_get_taxonomy, MGnify_get_go_terms |
| MGnify genome | MGYG000000001 | MGnify_get_genome |
| ENA study | PRJEB41867 | ENAPortal_search_studies |
| GTDB genome | GCA_000016605.1 | GTDB_get_genome |
| ENVO term | ENVO:00002041 | ols_get_term_info (biome) |

## Tips

- MGnify study accessions start with `MGYS`, analyses with `MGYA`, genomes with `MGYG`
- Use `MGnify_list_biomes` first to find the correct biome lineage string
- `MGnify_get_taxonomy` returns phylum-level to species-level composition
- GTDB provides standardized bacterial/archaeal taxonomy (differs from NCBI in some lineages)
- For 16S amplicon studies, taxonomy is the primary output; for shotgun metagenomics, both taxonomy and functional annotations are available
- The `size` parameter in MGnify tools controls results per page (max 100)
