---
name: tooluniverse-metagenomics-analysis
description: Analyze microbiome and metagenomics data using MGnify, GTDB, ENA, and literature tools. Search studies by biome/keyword, retrieve taxonomic profiles and functional annotations, classify genomes with GTDB taxonomy, and find related publications. Use for human gut microbiome, soil/ocean metagenomics, and environmental microbiology research.
---

# Metagenomics & Microbiome Analysis

Integrated pipeline for exploring microbiome studies, classifying taxa, assessing genome quality, linking microbial composition to clinical phenotypes, and interpreting findings through pathway analysis and literature context.

**Guiding principles**:
1. **Study context first** -- understand biome, sequencing method, and metadata before diving into taxa
2. **Taxonomic consistency** -- GTDB taxonomy as reference standard; reconcile NCBI where needed
3. **Genome quality matters** -- CheckM completeness/contamination thresholds determine trustworthy MAGs
4. **Interpretation over enumeration** -- explain what taxa mean for the biological question
5. **English-first queries** -- use English terms in tool calls

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Core Databases

| Database | Best For |
|----------|---------|
| **MGnify** | Processed metagenomics studies, taxonomic/functional results |
| **GTDB** | Standardized bacterial/archaeal taxonomy, species-level resolution |
| **GMrepo** | Gut species-to-human-health phenotype associations |
| **ENA** | Raw sequencing datasets and study metadata |
| **KEGG** | Pathway mapping for microbial functional annotations |
| **PubMed/EuropePMC** | Published microbiome-disease studies |
| **CTD** | Chemical-microbiome-disease relationships |

---

## Workflow

```
Phase 0: Parse query → organism, biome, phenotype, or accession
Phase 1: Study Discovery → MGnify_search_studies, ENAPortal_search_studies
Phase 2: Taxonomic Classification → GTDB_search_genomes, GTDB_get_species, GTDB_search_taxon
Phase 3: Genome Quality → MGnify_search_genomes, MGnify_get_genome (CheckM metrics)
Phase 4: Functional Annotation → MGnify GO terms + KEGG pathway mapping
Phase 5: Clinical Associations → GMrepo species-phenotype links
Phase 6: Literature → PubMed/EuropePMC + CTD gene-disease
Phase 7: Interpretation & Report Synthesis
```

---

## Key Phase Notes

**Phase 1**: ENA requires structured queries (e.g., `study_title="*IBD*"`), not free text. If ENA fails, fall back to MGnify.

**Phase 2**: GTDB uses its own naming (e.g., `s__Bacteroides_A fragilis` vs NCBI `Bacteroides fragilis`). Always note discrepancies. Use `GTDB_search_taxon(operation="search_taxon", query=name)`.

**Phase 3 - Quality tiers** (MIMAG):
- **High**: >= 90% complete, <= 5% contamination, rRNA + >= 18 tRNAs
- **Medium**: >= 50% complete, <= 10% contamination
- **Low**: below medium -- flag but don't exclude

**Phase 4 - Functional interpretation**: Don't just list GO terms. Connect to biology:

| Functional Category | Key KEGG Pathways | Significance |
|---|---|---|
| SCFA production | map00650, map00640 | Gut barrier, anti-inflammatory |
| LPS biosynthesis | map00540 | Pro-inflammatory, endotoxemia |
| Bile acid metabolism | map00120 | Fat absorption, FXR signaling |
| Tryptophan metabolism | map00380 | Serotonin, AhR, immune |
| Vitamin biosynthesis | map00730/740/760 | Host nutritional contribution |

Use `kegg_search_pathway(keyword=...)` (NOT `query`). Pathway IDs need organism prefix (`hsa`, `ko`, `eco`), NOT bare `map`.

**Phase 5**: GMrepo uses MeSH terms: "Crohn Disease" not "IBD", "Colitis, Ulcerative" not "UC", "Colorectal Neoplasms" not "colorectal cancer". Try NCBI taxon IDs if species name fails.

**Phase 6 - Evidence grading**:
- **Strong**: Meta-analysis or >5 studies, consistent direction
- **Moderate**: 2-5 studies consistent, or 1 large cohort
- **Preliminary**: Single study or conflicting
- **Mechanistic only**: In vitro/animal, no human epidemiology

**Phase 7 - Report**: Executive summary, study landscape, GTDB taxonomy, functional interpretation (not GO term lists), clinical relevance with evidence grades, mechanistic model, genome catalog with quality tiers, data gaps.

---

## Edge Cases & Fallbacks

- **Taxon not in GTDB**: Try partial search or fall back to MGnify (NCBI taxonomy)
- **No GMrepo data**: Normal for non-gut organisms; use literature
- **GMrepo 0 results**: Use formal MeSH terms or NCBI taxon IDs
- **No KEGG match**: Check MetaCyc or literature

## Limitations

- **GMrepo**: Gut-only
- **GTDB**: Bacteria/Archaea only
- **ENA**: Raw data only, strict query syntax
- **No sequence analysis**: Queries databases, not raw FASTQ/FASTA
