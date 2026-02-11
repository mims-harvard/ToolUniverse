# Full-Text Access in ToolUniverse

## Overview: Metadata vs Full Text

Literature search tools (PubMed, Europe PMC, OpenAlex, Semantic Scholar) intentionally return **metadata + abstract only**, not full text. This is by design:

- **Search APIs** are optimized for discovery and relevance ranking
- **Full-text APIs** require additional infrastructure and licensing
- **Abstracts** contain ~90% of key findings for initial screening

However, critical experimental details often reside in the full text:

- **Methods sections**: Specific reagents, concentrations, protocols, cell lines
- **Figure captions**: Numerical results, statistical details
- **Tables**: Complete datasets, parameter values
- **Supplementary materials**: Raw data, extended methods

**When you need full text:**
- ✅ Verifying specific experimental conditions (e.g., "Which antibiotic was used?")
- ✅ Extracting quantitative data not in abstract
- ✅ Disambiguating vague statements in abstract
- ✅ Checking methods for reproducibility
- ❌ Basic findings already clear in abstract

---

## Tool Selection Matrix

| Database | Search Tool | Full-Text Tool | Auto-Snippet Mode | Coverage | Notes |
|----------|-------------|----------------|-------------------|----------|-------|
| **Europe PMC** | `EuropePMC_search_articles` | `EuropePMC_get_fulltext_snippets` | ✅ `extract_terms_from_fulltext` | ~30-40% OA | XML-based, high quality |
| **Semantic Scholar** | `SemanticScholar_search_papers` | `SemanticScholar_get_pdf_snippets` | ❌ Manual 2-step | ~15-20% OA PDFs | Via `open_access_pdf_url` |
| **ArXiv** | `ArXiv_search_papers` | `ArXiv_get_pdf_snippets` | ❌ Manual 2-step | 100% (no paywall) | All preprints freely available |
| **PubMed** | `PubMed_search_articles` | → Europe PMC | Via Europe PMC | PMC subset (~25%) | Use `pmcid` to link to Europe PMC |
| **OpenAlex** | `openalex_literature_search` | `pdf_url` field | ❌ Manual download | Variable (~20-30%) | Use with `get_webpage_text_from_url` |

**Key:**
- ✅ Auto-snippet: Single tool call retrieves search results + full-text snippets
- ❌ Manual 2-step: Search → extract snippets from specific article
- OA: Open Access

---

## Workflow Examples

### Example 1: Quick Search with Auto-Snippets (Europe PMC)

**Use case:** "Find recent papers on bacterial antibiotic resistance evolution and verify which antibiotics were used."

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
results = tu.EuropePMC_search_articles(
    query="bacterial antibiotic resistance evolution",
    limit=10,
    extract_terms_from_fulltext=["ciprofloxacin", "meropenem", "gentamicin", "A. baumannii"]
)

# Process results
for article in results:
    print(f"Title: {article['title']}")
    print(f"Open Access: {article['open_access']}")
    
    # Check if snippets were extracted
    if "fulltext_snippets" in article:
        print(f"Full-text snippets found: {article['fulltext_snippets_count']}")
        for snippet in article["fulltext_snippets"]:
            print(f"  Term: {snippet['term']}")
            print(f"  Context: {snippet['snippet'][:100]}...")
    else:
        print("No full-text available (not OA or XML unavailable)")
```

**Advantages:**
- Single tool call
- Automatic OA detection
- Bounded latency (max 3 OA articles processed)
- No manual URL extraction needed

**Limitations:**
- Only works for open-access articles with fullTextXML
- Limited to first 3 OA articles (performance trade-off)
- Max 5 search terms

---

### Example 2: Two-Step Manual Extraction (Semantic Scholar)

**Use case:** "Search for machine learning papers and extract methodology details from a specific highly-cited paper."

```python
# Step 1: Search for papers
papers = tu.SemanticScholar_search_papers(
    query="machine learning interpretability",
    limit=10,
    include_abstract=True
)

# Step 2: Identify OA papers and extract snippets
for paper in papers:
    if paper.get("open_access_pdf_url"):
        print(f"Processing: {paper['title']}")
        
        snippets = tu.SemanticScholar_get_pdf_snippets(
            open_access_pdf_url=paper["open_access_pdf_url"],
            terms=["SHAP", "LIME", "gradient", "attribution"],
            window_chars=300
        )
        
        if snippets["status"] == "success":
            print(f"Found {snippets['snippets_count']} snippets")
            for s in snippets["snippets"]:
                print(f"  {s['term']}: {s['snippet'][:150]}...")
```

**Advantages:**
- Precise control over which articles to process
- Can extract from any OA paper
- Adjustable window size and term limits

**Limitations:**
- Requires two tool calls per article
- Manual loop needed for bulk processing

---

### Example 3: ArXiv Preprint Analysis

**Use case:** "Find recent computer vision preprints and extract architecture details."

```python
# Step 1: Search ArXiv
papers = tu.ArXiv_search_papers(
    query="vision transformer architecture",
    limit=5,
    sort_by="submittedDate"
)

# Step 2: Extract snippets from recent papers
for paper in papers:
    # Extract arXiv ID from URL (e.g., https://arxiv.org/abs/2301.12345)
    arxiv_id = paper["url"].split("/")[-1]
    
    snippets = tu.ArXiv_get_pdf_snippets(
        arxiv_id=arxiv_id,
        terms=["attention mechanism", "self-attention", "layer normalization"],
        max_snippets_per_term=5
    )
    
    if snippets["status"] == "success":
        print(f"Paper: {paper['title']}")
        print(f"Snippets: {snippets['snippets_count']}")
        for s in snippets["snippets"]:
            print(f"  {s['snippet'][:200]}...")
```

**Advantages:**
- All ArXiv papers are freely available (no OA check needed)
- High-quality LaTeX-based PDFs
- Often includes supplementary materials

---

### Example 4: Cross-Database Search with Fallback

**Use case:** "Comprehensive search across multiple databases with full-text extraction where available."

```python
search_query = "CRISPR gene editing off-target effects"
terms_of_interest = ["off-target", "specificity", "guide RNA", "Cas9"]

# Try Europe PMC first (best OA coverage + XML quality)
epmc_results = tu.EuropePMC_search_articles(
    query=search_query,
    limit=10,
    extract_terms_from_fulltext=terms_of_interest
)

print(f"Europe PMC: {len(epmc_results)} results")
oa_with_snippets = [r for r in epmc_results if "fulltext_snippets" in r]
print(f"  With full-text snippets: {len(oa_with_snippets)}")

# Supplement with Semantic Scholar
ss_results = tu.SemanticScholar_search_papers(
    query=search_query,
    limit=10
)

print(f"Semantic Scholar: {len(ss_results)} results")
oa_pdfs = [r for r in ss_results if r.get("open_access_pdf_url")]
print(f"  With OA PDFs: {len(oa_pdfs)}")

# Process top Semantic Scholar OA papers
for paper in oa_pdfs[:3]:
    snippets = tu.SemanticScholar_get_pdf_snippets(
        open_access_pdf_url=paper["open_access_pdf_url"],
        terms=terms_of_interest
    )
    if snippets["status"] == "success":
        print(f"  Extracted from: {paper['title'][:50]}...")
```

---

## Best Practices

### 1. Optimize Search Terms

**Good terms (specific, unambiguous):**
- ✅ "ciprofloxacin 5 μg/mL"
- ✅ "HEK293 cells"
- ✅ "RNA-seq analysis"

**Poor terms (too broad, ambiguous):**
- ❌ "drug" (matches thousands of words)
- ❌ "method" (too generic)
- ❌ "significant" (found everywhere)

### 2. Check Open Access Status

Always verify `open_access: true` before attempting full-text extraction:

```python
for article in results:
    if article.get("open_access"):
        # Proceed with full-text extraction
        pass
    else:
        print(f"Paywalled: {article['title']}")
        # Consider institutional access or manual download
```

### 3. Use Auto-Snippet Mode for Exploration

When exploring a new topic, use Europe PMC's auto-snippet mode:

```python
results = tu.EuropePMC_search_articles(
    query="new topic keywords",
    limit=20,
    extract_terms_from_fulltext=["key term 1", "key term 2", "key term 3"]
)

# Quickly scan which articles contain your terms
relevant = [r for r in results if r.get("fulltext_snippets")]
print(f"Found {len(relevant)} articles with matching terms in full text")
```

### 4. Adjust Window Size for Context

- **Narrow (150-200 chars)**: Quick verification, specific values
- **Medium (220 chars, default)**: Balanced context
- **Wide (400-500 chars)**: Full sentences, complex methods

```python
# Wide window for methods
snippets = tu.EuropePMC_get_fulltext_snippets(
    fulltext_xml_url=article["fulltext_xml_url"],
    terms=["cell culture protocol"],
    window_chars=500
)
```

### 5. Handle Rate Limits

Semantic Scholar and ArXiv have rate limits:

```python
import time

for paper in papers:
    snippets = tu.ArXiv_get_pdf_snippets(arxiv_id=paper["arxiv_id"], terms=terms)
    # ArXiv requests 3s between calls
    time.sleep(3.1)
```

### 6. Graceful Degradation

Always handle cases where full text is unavailable:

```python
def extract_or_skip(article, terms):
    if not article.get("open_access"):
        return {"status": "skipped", "reason": "not_oa"}
    
    if not article.get("fulltext_xml_url"):
        return {"status": "skipped", "reason": "no_xml"}
    
    try:
        return tu.EuropePMC_get_fulltext_snippets(
            fulltext_xml_url=article["fulltext_xml_url"],
            terms=terms
        )
    except Exception as e:
        return {"status": "error", "reason": str(e)}
```

---

## Troubleshooting

### Issue: "markitdown library not available"

**Solution:** Install markitdown with all dependencies:

```bash
pip install 'markitdown[all]>=0.1.0'
```

### Issue: Europe PMC auto-snippets returns empty

**Possible causes:**
1. Articles are not open access
2. fullTextXML not available (check `fulltext_xml_url` field)
3. Search terms not found in full text

**Debug:**

```python
results = tu.EuropePMC_search_articles(query="...", limit=10)

for r in results:
    print(f"Title: {r['title']}")
    print(f"  OA: {r['open_access']}")
    print(f"  XML URL: {r.get('fulltext_xml_url', 'N/A')}")
    print(f"  Snippets: {'fulltext_snippets' in r}")
```

### Issue: PDF download fails (403/404)

**Possible causes:**
1. Paper is not open access (Semantic Scholar)
2. arXiv ID format incorrect
3. PDF URL expired or changed

**Solution:**

```python
# For Semantic Scholar: verify OA status
if paper.get("open_access") and paper.get("open_access_pdf_url"):
    # Proceed

# For ArXiv: ensure correct ID format
arxiv_id = "2301.12345"  # Not "arXiv:2301.12345v1"
```

### Issue: PDF conversion returns garbled text

**Possible causes:**
1. PDF is image-based (scanned)
2. Complex LaTeX formatting
3. Non-standard fonts

**Solution:** markitdown uses OCR for image-based PDFs, but quality varies. Consider:

```python
snippets = tu.ArXiv_get_pdf_snippets(
    arxiv_id=arxiv_id,
    terms=terms,
    window_chars=400  # Wider window helps with garbled text
)

# Check snippet quality
for s in snippets["snippets"]:
    if len(s["snippet"]) < 50:
        print(f"Warning: Short snippet for '{s['term']}' - possible conversion issue")
```

### Issue: Rate limit errors (429)

**Solution:** Respect rate limits:

```python
import time

def rate_limited_extract(papers, delay=3):
    results = []
    for paper in papers:
        result = tu.ArXiv_get_pdf_snippets(...)
        results.append(result)
        time.sleep(delay)
    return results
```

---

## Performance Considerations

### Latency

| Operation | Typical Latency | Notes |
|-----------|----------------|-------|
| Europe PMC search | 1-2s | Fast API |
| Europe PMC auto-snippets | 3-5s | +1-2s per OA article (max 3) |
| PDF download (Semantic Scholar) | 2-10s | Depends on file size |
| PDF download (ArXiv) | 3-15s | ArXiv PDFs can be large |
| PDF → Markdown conversion | 1-5s | markitdown processing |

**Optimization tips:**
- Use auto-snippet mode for ≤3 articles
- For bulk processing, use manual 2-step with parallelization
- Cache frequently accessed PDFs

### API Quotas

| Service | Rate Limit (no key) | Rate Limit (with key) | Key Required? |
|---------|--------------------|-----------------------|---------------|
| Europe PMC | Unspecified | Unspecified | No |
| Semantic Scholar | 1 req/sec | 100 req/sec | Optional (`SEMANTIC_SCHOLAR_API_KEY`) |
| ArXiv | 3s between requests | N/A | No |
| PubMed | 3 req/sec | 10 req/sec | Optional (`NCBI_API_KEY`) |

---

## Integration with AI Workflows

### Use Case: LLM-Powered Literature Review

```python
# Step 1: Search and extract
results = tu.EuropePMC_search_articles(
    query="cancer immunotherapy checkpoint inhibitors",
    limit=20,
    extract_terms_from_fulltext=["PD-1", "PD-L1", "CTLA-4", "response rate"]
)

# Step 2: Build context for LLM
context = []
for r in results:
    if "fulltext_snippets" in r:
        context.append({
            "title": r["title"],
            "year": r["year"],
            "snippets": r["fulltext_snippets"]
        })

# Step 3: Query LLM
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a biomedical research assistant."},
        {"role": "user", "content": f"Summarize the checkpoint inhibitor response rates from these papers:\n\n{context}"}
    ]
)

print(response.choices[0].message.content)
```

### Use Case: Automated Hypothesis Generation

Extract specific experimental conditions across papers to identify gaps:

```python
# Find papers with specific model organisms
papers = tu.EuropePMC_search_articles(
    query="Alzheimer's disease tau pathology",
    limit=50,
    extract_terms_from_fulltext=["mouse model", "rat model", "C. elegans", "Drosophila"]
)

# Analyze model organism distribution
model_counts = {}
for p in papers:
    if "fulltext_snippets" in p:
        for s in p["fulltext_snippets"]:
            model = s["term"]
            model_counts[model] = model_counts.get(model, 0) + 1

print("Model organism usage:")
for model, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {model}: {count} papers")
```

---

## Summary

**For quick explorative searches:** Use Europe PMC with `extract_terms_from_fulltext`

**For comprehensive reviews:** Combine Europe PMC auto-snippets + manual Semantic Scholar/ArXiv extraction

**For preprints:** ArXiv provides 100% coverage with no paywall

**For paywalled content:** Use institutional access with `get_webpage_text_from_url` or contact authors

**Remember:** Full-text extraction adds latency. Use judiciously and cache results when possible.
