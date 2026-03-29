---
name: tooluniverse-proteomics-data-retrieval
description: >
  Find and retrieve proteomics datasets from public repositories including MassIVE and ProteomeXchange
  (which aggregates PRIDE, PeptideAtlas, jPOST, and iProX). Search by species, keyword, or accession.
  Get detailed dataset metadata including instruments, publications, species, modifications, and file counts.
  Use when asked to find proteomics datasets, search for mass spectrometry data, look up ProteomeXchange
  or MassIVE accessions, or discover publicly available proteomics experiments for a given organism or topic.
---

# Proteomics Data Retrieval

Find and retrieve metadata for publicly available proteomics datasets from MassIVE and ProteomeXchange
repositories. Supports searching by species, keyword, or accession, and returns detailed dataset metadata
including instruments, publications, species, and post-translational modifications.

## When to Use This Skill

**Triggers**:
- "Find proteomics datasets for [organism/disease/protein]"
- "Search MassIVE for [keyword]"
- "Get details for PXD000001" or "Look up MSV000079514"
- "What public mass spectrometry datasets exist for [topic]?"
- "Find MS datasets with [PTM type] data"
- "List recent human proteomics datasets"

**Use Cases**:
1. **Dataset Discovery**: Search repositories for proteomics experiments related to a research topic
2. **Accession Lookup**: Get full metadata for a known dataset accession (PXD or MSV)
3. **Species-Filtered Search**: Find all datasets for a specific organism
4. **Cross-Repository Search**: Query both MassIVE and ProteomeXchange for comprehensive coverage
5. **Experimental Context**: Find published datasets to validate or complement in-house results

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## KEY PRINCIPLES

1. **ProteomeXchange is the aggregator** -- it indexes datasets from PRIDE, MassIVE, PeptideAtlas, jPOST, and iProX
2. **MassIVE has richer metadata** -- includes summaries, keywords, modifications, and contacts
3. **Search both repositories** -- ProteomeXchange for breadth, MassIVE for detail
4. **Species uses NCBI taxonomy IDs** -- human = 9606, mouse = 10090, rat = 10116
5. **Accession formats**: PXD (ProteomeXchange), MSV (MassIVE) -- both accepted by MassIVE_get_dataset
6. **LOOK UP DON'T GUESS** -- Never assume which datasets exist, their accessions, or their instrument types. Always search and retrieve metadata to confirm.

## Domain Reasoning: Dataset Quality Assessment

Dataset quality depends on instrument, sample preparation, and quantification method. TMT/iTRAQ (isobaric labeling) datasets have ratio compression and co-isolation interference biases that differ from label-free quantification (LFQ). DIA datasets require different analysis pipelines than DDA. Check the original publication for methods before reusing data in a meta-analysis or cross-study comparison. Instrument resolution (Orbitrap > ion trap) and acquisition mode (DIA > DDA for completeness) directly affect how many proteins are quantified and at what confidence.

---

## Core Repositories Integrated

| Repository | Coverage | Strengths |
|-----------|----------|-----------|
| **MassIVE** | 10,000+ datasets | Rich metadata (summaries, keywords, modifications, contacts), species filtering by taxonomy ID |
| **ProteomeXchange** | Aggregates PRIDE, MassIVE, PeptideAtlas, jPOST, iProX | Broadest coverage, standardized PXD accessions |

---

## Workflow Overview

```
Query (keyword / species / accession)
|
+-- PHASE 0: Input Resolution
|   Determine search type: keyword, species, or accession lookup
|
+-- PHASE 1: Repository Search
|   Search MassIVE and/or ProteomeXchange based on query type
|
+-- PHASE 2: Dataset Detail Retrieval
|   Get full metadata for promising hits
|
+-- PHASE 3: Result Synthesis
    Compile datasets with metadata, publications, and relevance assessment
```

---

## Phase 0: Input Resolution

**Objective**: Determine the query type and prepare appropriate search parameters.

### Decision Logic

- **Accession provided** (e.g., `PXD000001`, `MSV000079514`):
  - PXD accession: call `ProteomeXchange_get_dataset` and optionally `MassIVE_get_dataset`
  - MSV accession: call `MassIVE_get_dataset`
  - Skip Phase 1, go directly to Phase 2
- **Species name provided** (e.g., "human", "mouse"):
  - Map to NCBI taxonomy ID: human=9606, mouse=10090, rat=10116, yeast=559292, zebrafish=7955, fly=7227, worm=6239, arabidopsis=3702
  - Use `MassIVE_search_datasets` with `species` filter
- **Keyword provided** (e.g., "phosphoproteomics", "breast cancer"):
  - Use `ProteomeXchange_search_datasets` with `query` parameter
  - MassIVE does not support keyword search -- use ProteomeXchange for keyword queries

---

## Phase 1: Repository Search

**Objective**: Find relevant datasets across repositories.

### Tools

**MassIVE_search_datasets**:
- `page_size`: Number of results to return (integer, max 100, default 10)
- `species`: NCBI taxonomy ID string to filter by species (e.g., `"9606"` for human)
- Returns: Array of dataset objects with `accessions` (array), `title`, `summary`, `species`, `instruments`, `keywords`
- **Note**: No keyword/text search parameter -- filtering is by species only

**ProteomeXchange_search_datasets**:
- `query`: Optional search filter -- keyword or dataset accession (e.g., `"phosphoproteomics"`, `"PXD"`)
- `limit`: Max results (1-50, default 10)
- Returns: `{data: [{accession, title, species}], metadata: {source, total_returned, query}}`

### Workflow

1. **For species-specific search**:
   - Call `MassIVE_search_datasets(page_size=20, species="9606")` for species-filtered results
   - Call `ProteomeXchange_search_datasets(limit=20)` for broader listing

2. **For keyword search**:
   - Call `ProteomeXchange_search_datasets(query="keyword", limit=20)`
   - Review titles for relevance

3. **For comprehensive discovery**:
   - Call both tools in parallel
   - Merge results, deduplicate by accession (PXD accessions may appear in both)

### Response Format Notes

- **MassIVE_search_datasets**: Returns a direct array (no `{data: ...}` wrapper)
- **ProteomeXchange_search_datasets**: Returns `{data: [...], metadata: {...}}`

---

## Phase 2: Dataset Detail Retrieval

**Objective**: Get full metadata for datasets of interest.

### Tools

**MassIVE_get_dataset**:
- `accession`: Dataset accession -- accepts both MSV and PXD formats (e.g., `"MSV000079514"`, `"PXD003971"`)
- Returns: Object with `accessions`, `title`, `summary`, `species`, `instruments`, `keywords`, `contacts`, `publications`, `modifications`

**ProteomeXchange_get_dataset**:
- `px_id`: ProteomeXchange identifier in PXD format (e.g., `"PXD000001"`)
- Returns: `{data: {px_id, title, species, identifiers, instruments, publications, file_count}, metadata: {...}}`

### Workflow

1. For each promising dataset from Phase 1, call the appropriate detail tool
2. Extract key metadata: title, species, instruments, publications (PubMed/DOI), modifications
3. For PXD accessions: prefer `ProteomeXchange_get_dataset` for file count; use `MassIVE_get_dataset` for richer summary/keywords

### Key Fields to Extract

- **title**: Dataset name/description
- **species**: Organism(s) studied
- **instruments**: Mass spectrometer(s) used (e.g., Orbitrap, Q Exactive, TripleTOF)
- **publications**: PubMed IDs and DOIs for associated papers
- **modifications**: PTMs studied (from MassIVE only)
- **file_count**: Number of raw files (from ProteomeXchange only)
- **keywords**: Topic tags (from MassIVE only)

---

## Phase 3: Result Synthesis

**Objective**: Compile and present dataset results in a structured format.

### Report Format

```
# Proteomics Dataset Search Results
**Query**: [original query]
**Date**: YYYY-MM-DD
**Repositories searched**: MassIVE, ProteomeXchange

## Summary
Found N datasets matching [criteria].

## Datasets

### 1. [Title]
- **Accession**: PXD/MSV number
- **Species**: [organism]
- **Instruments**: [MS platforms]
- **Publications**: [PubMed IDs / DOIs]
- **Modifications**: [PTMs if available]
- **Files**: [count if available]
- **Summary**: [brief description]

### 2. [Title]
...

## Data Gaps
[Note any limitations in search coverage]
```

---

## Tool Parameter Reference

| Tool | Parameter | Notes |
|------|-----------|-------|
| `MassIVE_search_datasets` | `page_size` | Integer, max 100. Default 10 |
| `MassIVE_search_datasets` | `species` | NCBI taxonomy ID as **string** (e.g., `"9606"` not `9606`) |
| `MassIVE_get_dataset` | `accession` | Accepts both MSV and PXD formats |
| `ProteomeXchange_search_datasets` | `query` | Optional keyword or accession filter |
| `ProteomeXchange_search_datasets` | `limit` | Integer, 1-50 |
| `ProteomeXchange_get_dataset` | `px_id` | PXD format only (e.g., `"PXD000001"`) |

**Response Format Notes**:
- **MassIVE_search_datasets**: Returns direct array of dataset objects (no wrapper)
- **MassIVE_get_dataset**: Returns direct object (no wrapper)
- **ProteomeXchange_search_datasets**: Returns `{data: [...], metadata: {...}}`
- **ProteomeXchange_get_dataset**: Returns `{data: {...}, metadata: {...}}`

---

## Fallback Strategies

| Situation | Fallback |
|-----------|----------|
| MassIVE search returns empty | Use ProteomeXchange search (broader coverage) |
| ProteomeXchange search returns empty | Try broader/simpler query terms |
| MassIVE_get_dataset fails for PXD accession | Use ProteomeXchange_get_dataset instead |
| Species taxonomy ID unknown | Search ProteomeXchange by keyword (organism name) |
| No keyword search results | Try individual terms instead of multi-word queries |

---

## Common Species Taxonomy IDs

| Species | Taxonomy ID |
|---------|-------------|
| Human | 9606 |
| Mouse | 10090 |
| Rat | 10116 |
| Zebrafish | 7955 |
| Fruit fly | 7227 |
| C. elegans | 6239 |
| S. cerevisiae | 559292 |
| A. thaliana | 3702 |
| E. coli | 562 |

---

## Interpretation Framework

| Quality Indicator | Good | Acceptable | Caution |
|-------------------|------|------------|---------|
| **Instrument** | Orbitrap Exploris/Eclipse, timsTOF | Q Exactive, TripleTOF 6600 | Older LTQ, ion trap only |
| **Publication** | Peer-reviewed with PubMed ID | Preprint or DOI only | No associated publication |
| **Metadata completeness** | Species + instrument + PTMs + summary | Species + instrument only | Title only, no annotations |

**Interpreting dataset search results:**
- Datasets with both MassIVE and ProteomeXchange accessions generally have richer metadata; MassIVE provides summaries and keywords while ProteomeXchange provides file counts -- cross-reference both for a complete picture.
- Instrument type determines data quality ceiling: high-resolution instruments (Orbitrap, timsTOF) produce higher mass accuracy and more reliable quantification than older ion trap platforms.
- A dataset lacking a peer-reviewed publication may still be valuable, but its experimental design and processing pipeline cannot be independently verified -- weight such datasets lower in meta-analyses.

**Synthesis questions to address in the report:**
1. Do multiple independent datasets for the same organism/condition show consistent protein identifications, or do discrepancies suggest batch effects?
2. Is the instrument platform appropriate for the analysis type (e.g., DIA requires high-resolution; TMT requires MS3 or calibrated MS2)?
3. Are the reported PTM types and species consistent with the user's research question, or is additional filtering needed?

---

## Limitations

- **MassIVE**: No keyword/text search -- only species-based filtering via `species` parameter
- **ProteomeXchange**: Limited metadata in search results (no summaries or keywords); get details via `Dataverse_get_dataset`
- **No full-text search**: Cannot search within dataset descriptions or abstracts across repositories
- **No download**: These tools retrieve metadata only, not raw data files
- **Rate limits**: Both APIs may throttle under heavy load; keep `page_size`/`limit` reasonable
- **Coverage**: ProteomeXchange is the most comprehensive but may lag behind individual repositories for very recent submissions

---

## Integration with Other Skills

| Skill | Relationship |
|-------|-------------|
| `tooluniverse-proteomics-analysis` | Use retrieved datasets as input for MS data analysis |
| `tooluniverse-protein-modification-analysis` | Find PTM-specific datasets to complement iPTMnet annotations |
| `tooluniverse-multi-omics-integration` | Discover proteomics datasets for cross-omics integration |

---

## References

- MassIVE: https://massive.ucsd.edu
- ProteomeXchange: http://www.proteomexchange.org
- PRIDE: https://www.ebi.ac.uk/pride
- ProXI API: https://github.com/PRIDE-Archive/proxi-schemas
