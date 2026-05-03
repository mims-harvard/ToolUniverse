# How to Search bioRxiv and medRxiv Preprints

## Important: bioRxiv API Does Not Support Text Search

The official bioRxiv API only supports **direct DOI/date-based retrieval**, not keyword/text search. This is a fundamental limitation of their public API.

## Tool Changes (Breaking Change)

**Old tool (removed):** `BioRxiv_search_preprints`
-  Attempted to search by keywords
-  Caused timeouts due to downloading entire date ranges
-  API misuse - tried to use details API for search purposes

**New tool:** `BioRxiv_get_preprint`
-  Fast direct retrieval by DOI (< 1 second)
-  Correct API usage
-  Returns comprehensive metadata

## Recommended Search Strategies

### Option 1: Use Europe PMC (Recommended)

Europe PMC indexes bioRxiv/medRxiv preprints and provides fast, relevance-ranked search.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# Search for bioRxiv preprints using Europe PMC
result = tu.run({"name": "EuropePMC_search_articles", "arguments": {
   "query": "CRISPR gene editing",
   "source": "PPR",  # Preprints only
   "pageSize": 20
}})

# Get full metadata from bioRxiv once you have the DOI
if result and result.get('status') == 'success':
   for article in result['data']['resultList']['result']:
       doi = article.get('doi')
       if doi and doi.startswith('10.1101/'):
           preprint = tu.run({"name": "BioRxiv_get_preprint", "arguments": {"doi": doi}})
           # Now you have complete bioRxiv metadata
```

**Why Europe PMC?**
-  Full-text search with relevance ranking
-  Supports advanced queries (Boolean, field-specific)
-  Returns abstracts and DOIs
-  Fast response times
-  Filters: date ranges, journals, authors

### Option 2: Use Web Search

For exploratory searches or when you need the latest preprints:

```python
result = tu.run({"name": "web_search", "arguments": {
   "query": "site:biorxiv.org CRISPR gene editing"
}})

# Extract DOIs from results and fetch full metadata
for item in (result or {}).get('data', []):
   # Parse DOI from URL or text
   # Then use BioRxiv_get_preprint
```

### Option 3: Use Semantic Scholar

Semantic Scholar also indexes bioRxiv:

```python
result = tu.run({"name": "SemanticScholar_search_papers", "arguments": {
   "query": "CRISPR gene editing",
   "venue": "bioRxiv"
}})
```

### Option 4: Local Data Dumps (Advanced)

For researchers who need to perform complex searches over the entire bioRxiv corpus:

1. Download the full bioRxiv snapshot from AWS S3 (updated monthly)
2. Use tools like `paperscraper` for local indexing and search
3. Query locally, then use `BioRxiv_get_preprint` for up-to-date metadata

**Note:** This approach requires ~50GB storage and local infrastructure but enables:
- Unlimited searches without API rate limits
- Complex queries not supported by external services
- Reproducible research (fixed snapshot)

## Using BioRxiv_get_preprint

Once you have a DOI, retrieve full metadata:

```python
# Full DOI format
result = tu.run({"name": "BioRxiv_get_preprint", "arguments": {
   "doi": "10.1101/2023.12.01.569554"
}})

# Shortened DOI format (automatically expanded)
result = tu.run({"name": "BioRxiv_get_preprint", "arguments": {
   "doi": "2023.12.01.569554"
}})

# For medRxiv preprints
result = tu.run({"name": "BioRxiv_get_preprint", "arguments": {
   "doi": "10.1101/2021.04.29.21256344",
   "server": "medrxiv"
}})

if result and result.get('status') == 'success':
   data = result['data']
   print(f"Title: {data['title']}")
   print(f"Authors: {', '.join(data['authors'])}")
   print(f"Abstract: {data['abstract']}")
   print(f"PDF: {data['pdf_url']}")
   print(f"Published: {data['published']}")  # Journal DOI if published
```

## Migration Guide

If you were using `BioRxiv_search_preprints`:

### Before (deprecated):
```python
# ❌ This tool no longer exists
result = tu.run({"name": "BioRxiv_search_preprints", "arguments": {
   "query": "CRISPR",
   "max_results": 10
}})
```

### After (recommended workflow):
```python
# Step 1: Search using Europe PMC
search_result = tu.run({"name": "EuropePMC_search_articles", "arguments": {
   "query": "CRISPR",
   "source": "PPR",
   "pageSize": 10
}})

# Step 2: Get full bioRxiv metadata for each result
if search_result and search_result.get('status') == 'success':
   for article in search_result['data']['resultList']['result']:
       doi = article.get('doi')
       if doi and doi.startswith('10.1101/'):
           preprint = tu.run({"name": "BioRxiv_get_preprint", "arguments": {"doi": doi}})
           # Use preprint['data'] with complete metadata
```

## Why This Change?

1. **API Reality**: bioRxiv's public API does not support text search. The old tool attempted to work around this by downloading entire date ranges and filtering client-side, which:
  - Caused 60+ second timeouts
  - Downloaded hundreds of MB unnecessarily
  - Failed for broad queries
  - Violated API design principles

2. **Better Alternatives Exist**: Services like Europe PMC provide proper search infrastructure with:
  - Sub-second response times
  - Relevance ranking
  - Advanced query syntax
  - Abstract snippets
  - Better metadata enrichment

3. **Correct Tool Design**: Each tool should do one thing well:
  - `BioRxiv_get_preprint`: Fast DOI-based retrieval (< 1s)
  - `EuropePMC_search_articles`: Fast text search across preprints
  - `web_search`: Exploratory discovery

## Complete Example: Research Workflow

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# 1. Discover relevant preprints
search = tu.run({"name": "EuropePMC_search_articles", "arguments": {
   "query": "Acinetobacter antibiotic resistance",
   "source": "PPR",
   "fromDate": "2023-01-01",
   "toDate": "2024-12-31",
   "pageSize": 20
}})

# 2. Get complete metadata for the most relevant ones
preprints = []
if search and search.get('status') == 'success':
   for article in search['data']['resultList']['result'][:5]:
       doi = article.get('doi')
       if doi and doi.startswith('10.1101/'):
           detailed = tu.run({"name": "BioRxiv_get_preprint", "arguments": {"doi": doi}})
           if detailed and detailed.get('status') == 'success':
           preprints.append(detailed['data'])

# 3. Access full text if needed
for preprint in preprints:
   print(f"Title: {preprint['title']}")
   print(f"PDF: {preprint['pdf_url']}")
   print(f"XML: {preprint['xml_url']}")
   print(f"Published: {preprint['published'] or 'Not yet'}")
   print("---")
```

## API Reference

### BioRxiv_get_preprint

**Parameters:**
- `doi` (string, required): bioRxiv/medRxiv DOI
 - Full format: `"10.1101/2023.12.01.569554"`
 - Short format: `"2023.12.01.569554"`
- `server` (string, optional): `"biorxiv"` or `"medrxiv"` (default: `"biorxiv"`)

**Returns:**
```json
{
 "status": "success",
 "data": {
   "doi": "10.1101/2023.12.01.569554",
   "title": "Paper title",
   "authors": ["Author1", "Author2"],
   "author_corresponding": "Corresponding Author",
   "author_corresponding_institution": "University Name",
   "abstract": "Full abstract text...",
   "date": "2023-12-01",
   "version": "1",
   "type": "new results",
   "license": "cc_by",
   "category": "microbiology",
   "published": "10.1128/journal.00123-24",
   "url": "https://www.biorxiv.org/content/10.1101/2023.12.01.569554",
   "pdf_url": "https://www.biorxiv.org/content/10.1101/2023.12.01.569554.full.pdf",
   "xml_url": "https://www.biorxiv.org/content/...",
   "server": "biorxiv"
 }
}
```

**Response time:** < 1 second

## Community Resources

- **bioRxiv AWS Snapshots**: https://api.biorxiv.org/
- **paperscraper**: Python library for local bioRxiv search (requires AWS download)
- **Europe PMC API**: https://europepmc.org/RestfulWebService
- **bioRxiv RSS feeds**: Available by subject category
- **bioRxiv Collection pages**: Curated topic collections

## Support

For issues or questions:
1. Check if you're using the correct search strategy (Europe PMC for search, BioRxiv for retrieval)
2. Verify DOI format if using `BioRxiv_get_preprint`
3. Open an issue on GitHub with reproducible examples
