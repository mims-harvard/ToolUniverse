---
name: tooluniverse-expression-data-retrieval
description: Retrieves gene expression and omics datasets from ArrayExpress and BioStudies with gene disambiguation, experiment quality assessment, and structured reports. Creates comprehensive dataset profiles with metadata, sample information, and download links. Use when users need expression data, omics datasets, or mention ArrayExpress (E-MTAB, E-GEOD) or BioStudies (S-BSST) accessions.
---

# Gene Expression & Omics Data Retrieval

Retrieve gene expression experiments and multi-omics datasets with disambiguation and quality assessment.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

**LOOK UP DON'T GUESS**: Never assume which datasets exist or their accessions. Always search to confirm.

## Domain Reasoning

Before retrieving, determine: organism, tissue, experimental design (case-control/time-series/dose-response). These affect which database to search and how to interpret results. RNA-seq provides wider dynamic range; microarray has extensive legacy data. Prioritize experiments with >=3 biological replicates, complete annotations, and both raw+processed data.

## Workflow

```
Phase 0: Clarify (if ambiguous) → Phase 1: Disambiguate → Phase 2: Search & Retrieve → Phase 3: Report
```

---

## Phase 0: Clarification (When Needed)

Ask ONLY if: gene name ambiguous, tissue/condition unclear, organism not specified.
Skip for: specific accessions (E-MTAB-*, E-GEOD-*, S-BSST*), clear disease/tissue+organism, explicit platform requests.

---

## Phase 1: Query Disambiguation

Resolve official gene symbol (HGNC for human, MGI for mouse). Note common aliases for search expansion.

| User Query Type | Search Strategy |
|-----------------|-----------------|
| Specific accession | Direct retrieval |
| Gene + condition | "[gene] [condition]" + species filter |
| Disease only | "[disease]" + species filter |
| Technology-specific | Add platform keywords |

---

## Phase 2: Data Retrieval (Internal)

Search silently. Do NOT narrate the process.

```python
# ArrayExpress search
result = tu.tools.arrayexpress_search_experiments(keywords="[gene/disease]", species="[species]", limit=20)

# Get experiment details, samples, files
details = tu.tools.arrayexpress_get_experiment(accession=accession)
samples = tu.tools.arrayexpress_get_experiment_samples(accession=accession)
files = tu.tools.arrayexpress_get_experiment_files(accession=accession)

# BioStudies for multi-omics
biostudies = tu.tools.biostudies_search(query="[keywords]", limit=10)
study = tu.tools.biostudies_get_study(accession=study_accession)
study_files = tu.tools.biostudies_get_study_files(accession=study_accession)
```

### Fallback Chains

| Primary | Fallback |
|---------|----------|
| ArrayExpress search | BioStudies search |
| arrayexpress_get_experiment | biostudies_get_study |
| arrayexpress_get_experiment_files | Note "Files unavailable" |

---

## Phase 3: Report Dataset Profile

Present as a **Dataset Search Report**. Hide search process. Include:

1. **Search Summary**: query, databases searched, result count
2. **Top Experiments** (per experiment):
   - Accession, organism, type (RNA-seq/microarray), platform, sample count, date
   - Description, experimental design (conditions, replicates, tissue)
   - Sample groups table, data files table
   - Quality assessment (●●●/●●○/●○○)
3. **Multi-Omics Studies** (from BioStudies): accession, type, data types included
4. **Summary Table**: all experiments ranked
5. **Recommendations**: best dataset for user's purpose, integration notes
6. **Data Access**: download links, database URLs

---

## Data Quality Tiers

| Tier | Symbol | Criteria |
|------|--------|----------|
| High | ●●● | >=3 bio replicates, complete metadata, processed data available |
| Medium | ●●○ | 2-3 replicates OR some metadata gaps |
| Low | ●○○ | No replicates, sparse metadata, or access issues |
| Caution | ○○○ | Single sample, no replication, outdated platform |

---

## Reasoning Framework

**Dataset quality**: Prioritize >=3 biological replicates, complete annotations, both raw+processed data. Single-replicate experiments can inform but not be sole evidence.

**Platform comparison**: RNA-seq = wider dynamic range, novel transcripts. Microarray = probe-limited but extensive legacy data. Cross-platform combining requires batch correction.

**Metadata scoring**: Rate 0-5 on: (1) sample annotations, (2) design documented, (3) pipeline described, (4) raw data deposited, (5) publication linked. Score <=2 warrants caution.

**GEO vs ArrayExpress**: GEO has broader coverage (older studies); ArrayExpress enforces stricter metadata. BioStudies captures multi-omics. Search both.

### Synthesis Questions
1. Does the dataset have sufficient replication and metadata for the intended analysis?
2. Are there batch effects or confounding variables?
3. Do multiple datasets show concordant patterns, and can they be integrated?

---

## Error Handling

| Error | Response |
|-------|----------|
| "No experiments found" | Broaden keywords, remove species filter, try synonyms |
| "Accession not found" | Verify format, check if withdrawn |
| "Files not available" | Note: "Data files restricted by submitter" |
| "API timeout" | Retry once, note "(metadata retrieval incomplete)" |

---

## Tool Reference

**ArrayExpress**: `arrayexpress_search_experiments` (search), `arrayexpress_get_experiment` (metadata), `arrayexpress_get_experiment_files` (downloads), `arrayexpress_get_experiment_samples` (annotations)

**BioStudies**: `biostudies_search` (search), `biostudies_get_study` (metadata+sections), `biostudies_get_study_files` (files)

**Additional Sources**:
- `GEO_search_rnaseq_datasets` / `geo_search_datasets` -- GEO (largest RNA-seq repo)
- `OmicsDI_search_datasets` -- cross-repository aggregation (GEO+ArrayExpress+PRIDE+MassIVE)
- `GTEx_get_expression_summary` -- baseline tissue expression (54 normal tissues, param: `gene_symbol`)
- `ENAPortal_search_studies` -- sequencing studies (param: `query` with `description="..."`)
- `CxGDisc_search_datasets` -- single-cell datasets (needs exact disease ontology terms)
- `PubMed_search_articles` -- dataset discovery via publications

---

## Search Parameters

**ArrayExpress**: `keywords` (free text), `species` (scientific name), `array` (platform filter), `limit`
**BioStudies**: `query` (free text), `limit`
