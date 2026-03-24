# ToolUniverse: Progressive Reveal Protocol

## Compact Mode Tools

ToolUniverse exposes 5 proxy tools in compact mode. All 1,200+ tools are accessed through these:

| Tool | Purpose |
|------|---------|
| `grep_tools` | Keyword search for tools (fast, exact match) |
| `find_tools` | Natural language / embedding search |
| `list_tools` | Browse tools by category |
| `get_tool_info` | Get exact parameter schema for a tool |
| `execute_tool` | Run a tool with arguments |

## Mandatory Workflow: Discover → Inspect → Execute → Iterate

1. **Discover**: Use `grep_tools` or `find_tools` to find relevant tools
2. **Inspect**: Call `get_tool_info` for EACH tool before execution — NEVER guess parameter names
3. **Execute**: Call `execute_tool` with exact schema from step 2
4. **Iterate**: Chain to related tools or cross-database search as needed

**Rule**: NEVER skip step 2. Parameter names vary across tools (e.g., `query` vs `search_keywords`, `limit` vs `max_results`). Always verify with `get_tool_info`.

## Literature Search Reference (Verified Schemas)

| Tool | Key Args | Notes |
|------|----------|-------|
| `PubMed_search_articles` | `query`, `max_results` | NCBI_API_KEY for 10 req/s |
| `ArXiv_search_papers` | `query`, `limit`, `sort_by` | "relevance" or "submittedDate" |
| `Crossref_search_works` | `query`, `limit`, `filter` | filter: "type:journal-article" |
| `SemanticScholar_search_papers` | `query`, `limit` | Optional API key |
| `openalex_literature_search` | `search_keywords`, `max_results`, `year_from`, `open_access` | **search_keywords NOT query** |
| `EuropePMC_search_articles` | `query`, `limit` | Returns data_quality |
| `BioRxiv_get_preprint` | `doi` | Fetch by DOI (no keyword search) |
| `BioRxiv_list_recent_preprints` | `interval`, `server`, `format` | Date-range browsing |
| `MedRxiv_get_preprint` | `doi` | Fetch by DOI (no keyword search) |
| `DOAJ_search_articles` | `query`, `max_results`, `type` | Open access |
| `CORE_search_papers` | `query`, `limit`, `year_from`, `year_to`, `language` | Largest OA |
| `PMC_search_papers` | `query`, `limit`, `date_from`, `date_to`, `article_type` | Full-text |
| `Zenodo_search_records` | `query`, `max_results`, `community` | Datasets |

## Field → Tool Selection

| Domain | Tools |
|--------|-------|
| Literature | PubMed, ArXiv, OpenAlex, Crossref, EuropePMC, CORE, DOAJ |
| Preprints | BioRxiv, MedRxiv |
| Proteins | UniProt, STRING, PDB, AlphaFold |
| Drugs | PubChem, ChEMBL, DrugBank, OpenTargets |
| Safety | FAERS, DailyMed |
| Clinical | ClinicalTrials, ClinVar |
| Genomics | GWAS Catalog, Ensembl, NCBI Gene |
| Pathways | KEGG, Reactome, WikiPathways |
| Ontology | Gene Ontology, HPO, Disease Ontology |
| Datasets | Zenodo, GEO, ArrayExpress |

## Common Non-Literature Tools

| Tool | Key Args | Notes |
|------|----------|-------|
| `UniProt_get_entry_by_accession` | `accession` | e.g., "P12345" |
| `FAERS_count_reactions_by_drug_event` | `medicinalproduct` | FDA adverse events |
| `OpenTargets_get_target_gene_ontology_by_ensemblID` | `ensemblId` | e.g., "ENSG00000141510" |
| `PubChem_get_CID_by_compound_name` | `name` | e.g., "aspirin" |
| `ClinicalTrials_search_studies` | `query`, `max_results` | clinicaltrials.gov |
| `ChEMBL_get_molecule` | `chembl_id` | e.g., "CHEMBL25" |

## Multi-Database Search Template

For comprehensive searches, query 3-5 databases:

1. **PubMed** (peer-reviewed) + **BioRxiv/MedRxiv** (preprints)
2. **OpenAlex** (metadata + citations) + **Crossref** (DOIs)
3. **Semantic Scholar** (AI-powered relevance)
4. Domain-specific: UniProt (proteins), FAERS (safety), etc.

## Hooks Behavior

- **SummarizationHook**: Auto-summarizes outputs >5,000 chars (focus: key findings)
- **FileSaveHook**: Saves outputs >50,000 chars to `/tmp/tooluniverse_outputs/`
- No user interaction needed — hooks fire automatically

## Gotchas

- **OpenAlex**: Uses `search_keywords` not `query`, `max_results` not `limit`
- **Unpaywall**: Requires `email` parameter
- **Rate limits**: NCBI 3 req/s (no key) → 10 req/s (with key)
- **execute_tool arguments**: Must be a flat JSON dict — never nested, never a list
- **Case sensitivity**: Parameter names are case-sensitive — match `get_tool_info` exactly
- **TOOLUNIVERSE_COERCE_TYPES=true**: Auto-converts "42" → 42, reducing type errors
- **TOOLUNIVERSE_STRICT_VALIDATION=false**: Ignores extra params instead of erroring
