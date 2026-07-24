# Full-Text Verification Strategy

Use when abstracts lack critical details (exact values, cell lines, concentrations, protocols, benchmark numbers, hyperparameters, dataset sizes).

---

## Table of Contents

1. [Tier 1: Auto-Snippet (Europe PMC)](#tier-1-auto-snippet-europe-pmc---fastest)
2. [Tier 2: Manual Two-Step](#tier-2-manual-two-step---targeted)
3. [Tier 3: Manual Download](#tier-3-manual-download---fallback)
4. [Decision Matrix](#decision-matrix)
5. [Best Practices](#best-practices)

---

## Tier 1: Auto-Snippet (Europe PMC) - FASTEST

**Use for**: Exploratory queries with 3-5 specific terms.

```
EuropePMC_search_articles(
    query="bacterial antibiotic resistance evolution",
    limit=10,
    extract_terms_from_fulltext=["ciprofloxacin", "meropenem", "A. baumannii", "MIC"]
)
→ Returns articles with fulltext_snippets[].term and fulltext_snippets[].snippet
```

- Single tool call (search + snippets)
- Bounded latency (max 3 OA articles, ~3-5 seconds)
- Terms processed in batches of 5 internally
- Only works for OA articles with fullTextXML (~30-40% coverage)

---

## Tier 2: Manual Two-Step - TARGETED

**Use for**: Specific high-value papers identified from search.

### Europe PMC Full-Text (broadest OA coverage)

```
EuropePMC_get_fulltext_snippets(
    article_id="PMC1234567",
    terms=["ADAR1", "MDA5", "interferon"],
    window_chars=300
)
→ Returns snippets from specific PMC article

EuropePMC_get_fulltext(article_id="PMC1234567")
→ Returns full-text XML
```

### Semantic Scholar PDF

```
SemanticScholar_get_pdf_snippets(
    open_access_pdf_url="<url from search results>",
    terms=["SHAP", "gradient attribution"],
    window_chars=300
)
→ First search with SemanticScholar_search_papers, then use open_access_pdf_url from results
```

### ArXiv (100% OA)

```
ArXiv_get_pdf_snippets(
    arxiv_id="2301.12345",
    terms=["attention mechanism", "self-attention", "layer normalization"],
    max_snippets_per_term=5
)
→ Works for any arXiv paper (100% coverage)
```

---

## Tier 3: Manual Download - FALLBACK

**Use for**: Paywalled content via institutional access (last resort).

```
get_webpage_text_from_url(url="https://doi.org/10.1016/...")
→ Returns full page text (quality varies by publisher)
```

- Requires institutional access
- No snippet extraction (full HTML)
- Quality varies by publisher

---

## Decision Matrix

| Scenario | Tier | Rationale |
|----------|------|-----------|
| Quick verification ("Which antibiotic?") | 1 (Auto-snippet) | Fast, single call |
| CS/ML paper on arXiv | 2 (ArXiv) | 100% coverage, use ArXiv_get_pdf_snippets |
| Preprint deep-dive (arXiv, bioRxiv) | 2 (Manual ArXiv) | 100% coverage |
| High-value paper analysis | 2 (Manual S2) | Precise control |
| Systematic review (50+ papers) | 1 + 2 | Auto for OA, manual for key papers |
| Paywalled critical paper | 3 (Manual download) | Only option |

---

## Best Practices

1. **Limit search terms to 3-5 specific keywords**:
   - Bio: `["ciprofloxacin 5 ug/mL", "HEK293 cells", "RNA-seq"]`
   - CS/ML: `["BLEU score", "F1 macro", "learning rate 3e-5"]`
   - Bad: `["drug", "method", "significant"]`

2. **Check OA status before extraction**: Use `isOpenAccess` field from EuropePMC or `open_access_pdf_url` from SemanticScholar.

3. **Adjust window size for context**:
   - Methods: 400-500 chars
   - Quick verification: 150-200 chars
   - Default: 220 chars

4. **Handle failures gracefully**: fall back to abstract or skip.

5. **Document full-text sources in report**:
   ```markdown
   ## Methods Verification

   **Key detail** (verified from full text):
   - Study A: Value X [PMC12345, Methods section]
   - Study B: Value Y [arXiv:2301.12345, Experimental Design]

   *Full-text verification performed on 8/15 OA papers (53% coverage)*
   ```
