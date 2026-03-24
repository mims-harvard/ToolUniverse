# ToolUniverse Query Reference

Anti-dict-error reference — exact JSON schemas verified against official tutorial.

## execute_tool Call Format

```
execute_tool(tool_name: str, arguments: dict)
# arguments MUST be a flat JSON dict — never nested, never a list
# Keys must match get_tool_info output EXACTLY (case-sensitive)
```

## Common Dict Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `KeyError: 'query'` | Tool uses `search_keywords` not `query` | Always call `get_tool_info` first |
| `TypeError: dict` | Passing string where dict expected | Wrap args: `{"query": "..."}` not `"query"` |
| `ValidationError` | Wrong param name or type | Match schema exactly from `get_tool_info` |
| `Missing required field` | Omitted required param | Check `get_tool_info` for required vs optional |

## Literature Tool Call Formats (Copy-Paste Ready)

```json
// PubMed
{"name": "PubMed_search_articles", "arguments": {"query": "CRISPR cancer", "max_results": 5}}

// ArXiv
{"name": "ArXiv_search_papers", "arguments": {"query": "machine learning", "limit": 5, "sort_by": "relevance"}}

// Crossref
{"name": "Crossref_search_works", "arguments": {"query": "AI", "limit": 5, "filter": "type:journal-article"}}

// OpenAlex — NOTE: search_keywords NOT query, max_results NOT limit
{"name": "openalex_literature_search", "arguments": {"search_keywords": "CRISPR", "max_results": 5, "year_from": 2020, "open_access": true}}

// Europe PMC
{"name": "EuropePMC_search_articles", "arguments": {"query": "machine learning", "limit": 5}}

// Semantic Scholar
{"name": "SemanticScholar_search_papers", "arguments": {"query": "deep learning", "limit": 5}}

// BioRxiv (no keyword search — use DOI or date-range)
{"name": "BioRxiv_get_preprint", "arguments": {"doi": "10.1101/2024.01.01.000000"}}
{"name": "BioRxiv_list_recent_preprints", "arguments": {"interval": "2024-01-01/2024-01-31", "server": "biorxiv", "format": "json"}}

// MedRxiv (no keyword search — use DOI or EuropePMC with SRC:PPR filter)
{"name": "MedRxiv_get_preprint", "arguments": {"doi": "10.1101/2024.01.01.24300000"}}

// DOAJ (Open Access)
{"name": "DOAJ_search_articles", "arguments": {"query": "renewable energy", "max_results": 5, "type": "articles"}}

// CORE
{"name": "CORE_search_papers", "arguments": {"query": "AI", "limit": 5, "year_from": 2020, "year_to": 2026, "language": "en"}}

// PMC (full-text)
{"name": "PMC_search_papers", "arguments": {"query": "cancer", "limit": 5, "date_from": "2020/01/01", "article_type": "research-article"}}

// Zenodo (datasets)
{"name": "Zenodo_search_records", "arguments": {"query": "dataset", "max_results": 5}}

// Unpaywall — requires email
{"name": "Unpaywall_check_oa_status", "arguments": {"doi": "10.1038/nature12373", "email": "user@example.com"}}
```

## Non-Literature Tool Call Formats

```json
// UniProt
{"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P12345"}}

// FAERS drug safety
{"name": "FAERS_count_reactions_by_drug_event", "arguments": {"medicinalproduct": "metformin"}}

// OpenTargets
{"name": "OpenTargets_get_target_gene_ontology_by_ensemblID", "arguments": {"ensemblId": "ENSG00000141510"}}

// PubChem
{"name": "PubChem_get_CID_by_compound_name", "arguments": {"name": "aspirin"}}

// ClinicalTrials
{"name": "ClinicalTrials_search_studies", "arguments": {"query": "diabetes", "max_results": 5}}

// ChEMBL
{"name": "ChEMBL_get_molecule", "arguments": {"chembl_id": "CHEMBL25"}}

// STRING protein interactions
{"name": "STRING_get_interaction_partners", "arguments": {"identifiers": "TP53", "species": 9606}}

// KEGG pathway
{"name": "kegg_get_pathway_info", "arguments": {"pathway_id": "hsa04110"}}

// Gene Ontology
{"name": "GO_search_terms", "arguments": {"query": "apoptosis"}}

// ClinVar
{"name": "clinvar_search_variants", "arguments": {"gene": "BRCA1"}}
```

## Field → Tool Routing

| Question About | Start With |
|----------------|------------|
| Published papers | `PubMed_search_articles` → `Crossref_search_works` |
| Preprints | `EuropePMC_search_articles` (SRC:PPR) → `MedRxiv_get_preprint` → `BioRxiv_list_recent_preprints` |
| Drug safety | `FAERS_count_reactions_by_drug_event` → `DailyMed` |
| Protein info | `UniProt_get_entry_by_accession` → `STRING` |
| Drug/compound | `PubChem_get_CID_by_compound_name` → `ChEMBL_get_molecule` |
| Clinical trials | `ClinicalTrials_search_studies` |
| Gene function | `OpenTargets` → `GO_search_terms` |
| Variants | `clinvar_search_variants` → `GWAS` |
| Open access | `DOAJ_search_articles` → `Unpaywall` → `CORE` |
| Datasets | `Zenodo_search_records` → `GEO` |

## Glossary

- **ChEMBL ID**: e.g., `CHEMBL25` (aspirin) — drug/compound queries
- **UniProt Accession**: e.g., `P05067` (amyloid precursor protein) — 1-6 chars
- **EFO ID**: e.g., `EFO_0000537` (hypertension) — disease classification
- **PubChem CID**: e.g., `2244` (aspirin) — numerical compound ID
- **Ensembl ID**: e.g., `ENSG00000141510` (TP53) — gene identifier
- **Compact Mode**: Only 5 proxy tools exposed; all 1200+ accessible via `execute_tool`
- **SMCP**: Scientific MCP — ToolUniverse's MCP implementation
- **Tool Finder family**: `grep_tools` (keyword), `find_tools` (NL/embedding), `list_tools` (browse)
- **FAERS**: FDA Adverse Event Reporting System

## Environment Variables

| Variable | Value | Why |
|----------|-------|-----|
| `TOOLUNIVERSE_CACHE_ENABLED` | `true` | 10x speedup, offline support |
| `TOOLUNIVERSE_CACHE_PERSIST` | `true` | Results survive restarts |
| `TOOLUNIVERSE_CACHE_MEMORY_SIZE` | `1024` | LRU entries (default 256) |
| `TOOLUNIVERSE_LAZY_LOADING` | `true` | Fast startup, load on demand |
| `TOOLUNIVERSE_COERCE_TYPES` | `true` | Auto-fix string-to-int mismatches |
| `TOOLUNIVERSE_STRICT_VALIDATION` | `false` | Tolerate extra params |
| `TOOLUNIVERSE_STDIO_MODE` | `1` | Required for MCP stdio |
| `TOOLUNIVERSE_LOG_LEVEL` | `INFO` | Change to `DEBUG` for troubleshooting |
