---
name: literature-sweep
description: Run a graded mini-review on a topic across multiple literature sources (PubMed, EuropePMC, bioRxiv, Semantic Scholar). Dedupes hits, scores relevance to the topic, returns a ranked table with citation, year, key claim, and relevance. Use when the user wants more than a raw search dump — they want a curated short-list ready to read.
argument-hint: "[topic, e.g. 'KRAS G12C inhibitor resistance mechanisms', 'CRISPR base editing in Friedreich ataxia']"
---

Run a literature sweep on this topic: $ARGUMENTS

A raw `PubMed_search` dump is overwhelming and often noisy (many hits don't
actually address the topic). Curate down to a small, high-quality reading
list with structured metadata.

## Process

### 1. Plan the query strategy

Decompose the topic into 1-3 search formulations. Different sources accept
different syntax, so you'll often run the same idea multiple ways.

For "KRAS G12C inhibitor resistance mechanisms":
- Strict: `(KRAS[ti] OR sotorasib OR adagrasib) AND resistance`
- Broad: `KRAS G12C resistance mechanism`
- Mechanism-focused: `KRAS G12C bypass OR rebound`

State the formulations in one line before searching.

### 2. Search 2-3 independent literature sources

PubMed (NIH), EuropePMC, Semantic Scholar, bioRxiv each maintain their own
indices. Run the topic across at least 2 of them so a paper missed by one
gets picked up by another.

```bash
# PubMed (peer-reviewed, mostly biomedical)
tu run PubMed_search_articles '{"query":"KRAS G12C resistance mechanism","max_results":20}'

# EuropePMC (broader incl. preprints, agricultural, pharm)
tu run EuropePMC_search_articles '{"query":"KRAS G12C resistance mechanism","limit":20}'

# Semantic Scholar (citation graph, sometimes catches non-MeSH-indexed)
tu run semantic_scholar_search '{"query":"KRAS G12C inhibitor resistance","limit":20}'
```

If a search returns <5 hits, broaden the query. If >50, narrow it.

### 3. Dedupe across sources

Same paper appears in multiple sources with different IDs. Dedupe by:
- DOI (most reliable)
- PubMed ID (PMID)
- Title fuzzy match (case-insensitive, drop punctuation, prefix-match >85%)

Keep one canonical record per paper, listing the sources that found it
(useful as a relevance signal — papers in multiple indices are usually
more central).

### 4. Score relevance per paper

For each deduped paper, score against the topic on three axes:

- **Topical match (0-3)**: how directly does the title/abstract address the
  topic? 3 = explicit match, 2 = adjacent, 1 = tangential, 0 = irrelevant
- **Recency (0-2)**: 2 = published in last 2 years, 1 = last 5 years, 0 = older
- **Source weight (0-2)**: 2 = peer-reviewed in indexed source, 1 = preprint,
  0 = uncategorized

Total: 0-7. Discard everything below 4.

If you can't read the abstract (some sources return only metadata), use the
title alone — be conservative.

### 5. Output: ranked table + reading order

```
## Literature sweep: <topic>
## Sources: PubMed (n=20), EuropePMC (n=20), Semantic Scholar (n=15)
## Deduped: 38 unique papers; 14 above relevance threshold

| # | Paper | Year | Source(s) | Score | Key claim |
|---|---|---|---|---|---|
| 1 | Awad et al, *Nature Med* | 2024 | PubMed, EPMC | 7 | Acquired KRAS G12C resistance via secondary KRAS mutations + RTK rewiring |
| 2 | Tanaka et al, *Cancer Discov* | 2025 | PubMed, S2 | 7 | YAP/TAZ mediates adaptive resistance to sotorasib |
| 3 | Xue et al, *Nature* | 2024 | PubMed | 6 | Polyclonal resistance landscape from circulating tumor DNA |
| ... |

## Recommended reading order
1. Awad 2024 — establishes the resistance taxonomy (read first)
2. Tanaka 2025 — best mechanistic detail on adaptive (non-genetic) resistance
3. Xue 2024 — clinical heterogeneity context
4-5: skim only

## Caveats
- 4 papers were >5 years old (excluded as below recency threshold) — re-run
  with `--include-older` if historical context is wanted
- Semantic Scholar returned 8 papers with no abstract; scored on title only
- 2 preprints in the list (marked with †); may not be peer-reviewed yet
```

### 6. Note what's missing

End with:
- Years you searched (default: last 5)
- Languages (default: English; note if non-English papers were excluded)
- Whether reviews were included or only primary research
- Specific known papers the user might expect that DIDN'T appear (helpful
  for the user to verify the sweep was thorough)

## When this is overkill

- The user just wants the title of a specific paper they remember partially
  → use a direct PubMed search
- The user wants the FULL TEXT of a specific known paper → use a fetch tool,
  not a sweep
- The topic is too narrow for multi-source (e.g., one specific gene-drug pair
  with <5 known publications) → a single PubMed search is fine

## Stop conditions

- 2 sources both return 0 hits → topic is mis-specified or too narrow.
  Don't fabricate; report empty and suggest broader formulations.
- Dedup runs into citation cycles (same paper claimed by 5+ different
  source-IDs) → trust DOI first, then PMID, ignore the rest.
- 50+ deduped papers above threshold → narrow the topic OR present only
  top-15 with a "more available" note.
