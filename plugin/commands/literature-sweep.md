---
name: literature-sweep
description: Run a graded mini-review on a topic across many literature sources, adaptively chosen by domain — a core multi-field set (PubMed, EuropePMC, OpenAlex, Semantic Scholar) plus domain-specific indexes (ArXiv/DBLP for CS, InspireHEP for physics, PubTator/PMC/clinical guidelines for biomedical, Crossref/CORE/DOAJ/Fatcat for broad coverage, OSF/preprints for the latest work). Dedupes hits, scores relevance to the topic, returns a ranked table with citation, year, key claim, and relevance. Use when the user wants more than a raw search dump — they want a curated short-list ready to read.
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

### 2. Search several independent literature sources (adaptive by domain)

ToolUniverse exposes 15+ keyword-searchable literature indexes. Each maintains
its own coverage, so running a topic across several catches papers any single
one misses. **Don't blindly fire all of them** — that's slow and noisy. Pick
the always-on CORE set, then add the domain rows that match the topic.

**ALWAYS run (multi-field core — 4 indexes):**

```bash
# PubMed (NIH; peer-reviewed biomedical, MeSH-indexed)
tu run PubMed_search_articles '{"query":"KRAS G12C resistance mechanism","limit":20}'

# EuropePMC (broader: clinical, agricultural, pharma + preprints via SRC:PPR)
tu run EuropePMC_search_articles '{"query":"KRAS G12C resistance mechanism","limit":20}'

# OpenAlex (250M+ works, every discipline; good cross-field recall)
tu run openalex_search_works '{"search":"KRAS G12C inhibitor resistance","per_page":20}'

# Semantic Scholar (AI-ranked citation graph; catches non-MeSH-indexed work)
tu run SemanticScholar_search_papers '{"query":"KRAS G12C inhibitor resistance","limit":20}'
```

**THEN add domain-specific indexes when the topic matches:**

| Topic signal | Add these sources | Why |
|---|---|---|
| Biomedical / clinical / gene·drug·disease | `PMC_search_papers` (full text), `PubTator3_LiteratureSearch` (entity & relation queries, e.g. `relations:treat\|@CHEMICAL_X\|@DISEASE_Y`) | Full-text body hits + entity-normalized recall |
| Clinical practice / treatment guidelines | `PubMed_Guidelines_Search` | Filters to guideline / practice-guideline pub types |
| CS / ML / AI / algorithms | `ArXiv_search_papers`, `DBLP_search_publications` | arXiv preprints + CS bibliography (often not in PubMed) |
| Physics / HEP / astro | `InspireHEP_search_papers` | 1.6M+ particle/astro physics records |
| Broad / cross-disciplinary / hard-to-find | `Crossref_search_works`, `CORE_search_papers`, `DOAJ_search_articles`, `Fatcat_search_scholar` | DOI registry + open-access aggregators + Internet Archive Scholar |
| Need the very latest (preprints) | `EuropePMC_search_articles` with `SRC:PPR`, `OSF_search_preprints` | bioRxiv/medRxiv/PsyArXiv etc. before peer review |
| Datasets / code / supplementary outputs | `Figshare_search_articles`, `Zenodo_search_records` | Research data and software with citable DOIs |

Run the core 4 plus the matching domain row(s) — typically **5–8 sources total**.
State which sources you chose (and why) in one line before searching.

**Parameter gotchas** (the add-on tools don't all use `query` + `limit` — run
`tu info <Tool>` if a call is rejected):
- `InspireHEP_search_papers`: query param is `q`, count is `size`.
- `Figshare_search_articles`: query param is `search_for` (not `query`).
- OpenAlex has two tools with **different** query params: `openalex_search_works`
  uses `search` (or `query`); `openalex_literature_search` uses `search_keywords`.
  Passing the wrong one silently returns unfiltered (off-topic) results — pick one
  and match its param.
- `DBLP_search_publications`, `PubMed_Guidelines_Search`, `Fatcat_search_scholar`,
  `HAL_search_archive`, `OpenAIRE_search_publications`: a count param is
  **required** (`limit` or `max_results`) — passing only the query is rejected.
  `OpenAIRE` also requires `type` (`"publications"`).
- Preprints: append `SRC:PPR` to the EuropePMC `query` string.
- `CORE_search_papers` is rate-limited (HTTP 429) without `CORE_API_KEY` — treat
  as best-effort; don't rely on it as a sole source.

If a search returns <5 hits, broaden the query. If >50, narrow it. If a source
errors or needs an unconfigured API key, note it and proceed with the rest —
never let one dead source abort the sweep.

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
## Sources queried: PubMed (n=20), EuropePMC (n=20), OpenAlex (n=20), Semantic Scholar (n=15), PMC (n=12), PubTator3 (n=8)
## Deduped: 61 raw hits → 38 unique papers; 14 above relevance threshold

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

- The core sources (PubMed + EuropePMC + OpenAlex) all return 0 hits → topic is
  mis-specified or too narrow. Don't fabricate; report empty and suggest broader
  formulations. (A domain-specific index returning 0 is normal — e.g. ArXiv on a
  pure-clinical topic — and is not a stop condition.)
- Dedup runs into citation cycles (same paper claimed by 5+ different
  source-IDs) → trust DOI first, then PMID, ignore the rest.
- 50+ deduped papers above threshold → narrow the topic OR present only
  top-15 with a "more available" note.
