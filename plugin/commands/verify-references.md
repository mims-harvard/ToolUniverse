---
name: verify-references
description: Check whether cited references are real and accurately described — confirms each citation actually exists and that its title/authors/year/journal/DOI match what's claimed, using independent databases (Crossref, DataCite, PubMed, OpenAlex, Semantic Scholar, EuropePMC, plus domain-specific sources like ArXiv/DBLP/InspireHEP/Zenodo and a last-resort web search) instead of trusting the citation at face value. Also flags retracted papers. Accepts a single citation or claim, or a full bibliography (.bib file or pasted reference list), and checks every entry — including dataset/software DOIs, not just journal articles. Use before trusting, publishing, or citing a reference list — especially AI-drafted text, where fabricated ("hallucinated") citations are a known failure mode.
argument-hint: "[a citation/DOI/claim, a .bib file path, or a pasted reference list — e.g. 'Smith et al 2023, Nature, doi:10.1038/xyz' or 'refs.bib' or a full References section]"
---

Verify these references: $ARGUMENTS

A citation that *looks* well-formed (real-sounding authors, a plausible journal,
a DOI-shaped string) can still be wrong in three different ways: the paper
doesn't exist at all (fabricated), the paper exists but the citation
misstates it (wrong year, wrong journal, wrong authors), or the paper exists
and is cited correctly but has since been retracted. Only a database lookup
distinguishes these — don't judge a citation by how plausible it reads.

## Process

### 1. Parse the input into individual entries

Figure out what you're checking before touching any tool:

- **Single citation or claim** ("Smith et al 2023 showed X, doi:10.1038/xyz")
  → one entry.
- **`.bib` file** → read it and parse each `@article{key, title={...},
  author={...}, year={...}, journal={...}, doi={...}}` block into a record.
  Missing fields are fine — just note what wasn't stated.
- **Pasted reference list** (numbered `[12] ...`, or a References section from
  a paper draft) → split on the list's own numbering/formatting. Don't
  re-derive boundaries from prose; use whatever markers the list already uses.

For each entry, extract whatever is present: DOI, title, author(s), year,
journal/venue. A DOI is the strongest anchor — resolve on that first when
available. If two entries share the same DOI, resolve it once and reuse the
record — don't repeat the same lookup.

### 2. Resolve each entry to an authoritative record

**If a DOI is present:**
```bash
tu run Crossref_get_work '{"doi":"10.1038/s41586-025-10014-0"}'
```
Crossref is the *largest* DOI registrar, not the only one — it covers most
journal articles, but datasets, software, and many repository records
(Zenodo, institutional archives) are registered with **DataCite** instead.
A Crossref 404 on its own does not mean the DOI is fake; try DataCite
before concluding that:
```bash
tu run DataCite_get_doi '{"doi":"10.5281/zenodo.1215979"}'
```
Only classify the DOI as fabricated/mistyped once *both* registries fail
(also try stripping trailing punctuation first — a stray period or
parenthesis from the citation's formatting is a common false negative).
Cross-check the returned title/authors/year against one more independent
source (`openalex_get_work_by_doi` or `SemanticScholar_get_paper` with
`{"paper_id":"DOI:<doi>"}`) — registry metadata is occasionally sparse for
older or unusual works.

**If no DOI is given (or the citation is prose-only):**
Search by title/author/year across 2 independent sources — don't stop at one:
```bash
tu run Crossref_search_works '{"query":"<title and lead author>","limit":3}'
tu run PubMed_search_articles '{"query":"<title>","limit":3}'
```
Pick a *third* source that actually fits the field, rather than defaulting
to more biomedical tools for a paper that obviously isn't biomedical (same
sources `/literature-sweep` uses):

| Citation looks like... | Add these sources |
|---|---|
| CS / ML / algorithms | `ArXiv_search_papers`, `DBLP_search_publications` |
| Physics / HEP / astro | `InspireHEP_search_papers` |
| Dataset / software / code | `Zenodo_search_records`, `DataCite_search_dois` |
| Preprint (bio/med) | `BioRxiv_get_preprint` / `MedRxiv_get_preprint` if a DOI is given, else `EuropePMC_search_articles` with `SRC:PPR` |
| Broad / hard to place | `openalex_search_works`, `CORE_search_papers`, `SemanticScholar_search_papers`, `DOAJ_search_articles` |

**Important — these searches are keyword-based, not existence checks.**
`Crossref_search_works` and friends return their *closest keyword matches*
for almost any query, including ones built from a fully fabricated title —
they will not come back empty just because nothing matches. A returned hit
is only evidence the reference is real if **you** judge that its title,
authors, and year actually match the claim. Never treat "the search returned
results" as verification on its own.

**Once a DOI is found this way**, resolve it with `Crossref_get_work` (or
`DataCite_get_doi`) as above, and proceed to retraction check.

**Last resort before declaring NOT FOUND — one general web search.**
Structured databases don't cover everything: books (ISBN, no DOI),
technical reports, older non-digitized papers, and unindexed conference
proceedings can be entirely real and still invisible to every tool above.
If the domain-appropriate database checks all come up empty, do ONE web
search (Claude Code's own WebSearch/WebFetch — not a ToolUniverse tool)
before concluding fabricated. This cuts both ways: it can save a real
citation from a false NOT FOUND, but a webpage alone isn't authoritative
enough to mark something VERIFIED — if a web search is the *only* thing
that turns something up, cap the verdict at AMBIGUOUS rather than VERIFIED,
and say what you found (a citing page, a publisher listing, etc.) so the
user can judge it themselves. Never let a web search override a database's
retraction finding.

### 3. Check retraction status (whenever a DOI resolves via Crossref)

A real, correctly-cited paper can still be a bad thing to cite if it's been
retracted since publication — this is a distinct failure mode from
"citation is wrong" and easy to miss:
```bash
tu run Crossref_check_retraction '{"doi":"10.1016/S0140-6736(97)11096-0"}'
```
Report `is_retracted` / `has_expression_of_concern` / `has_correction`
prominently when true — a paper existing is not the same as it being safe to
cite. Retraction tracking is a journal-article concept, so skip this step
for entries that only resolved via DataCite (datasets/software) — the call
will just error, and that's expected, not a problem to work around.

### 4. Compare claimed fields against the authoritative record

For each field the citation stated, compare against what the database
returned:
- **Title** — fuzzy match (case/punctuation-insensitive; a missing subtitle
  after a colon is not a mismatch, a different topic is)
- **Authors** — first-author surname at minimum; flag if the full list was
  claimed and doesn't match
- **Year** — exact; allow one year of slack for "online first" vs print
  publication dates, and say so when you use that slack
- **Journal/venue** — match by name (abbreviations count, e.g. "PNAS" =
  "Proceedings of the National Academy of Sciences")
- **DOI** — exact string match if both are present

### 5. Classify each entry

- **VERIFIED** — found, all stated fields match
- **MISMATCH** — found, but one or more stated fields are wrong; name exactly
  which field and what the correct value is
- **RETRACTED** — found and matches, but Crossref flags it as retracted /
  under expression of concern
- **NOT FOUND** — no candidate across the domain-appropriate sources (plus
  a last-resort web search, if no DOI was findable) plausibly matches the
  claimed title/authors/year; likely fabricated
- **AMBIGUOUS** — multiple candidates fit equally well and the citation
  doesn't give enough to disambiguate (e.g. common author surname, no DOI,
  generic title) — say so rather than guessing which one

### 6. Report

```
## References checked: N

| # | Citation (as given) | Verdict | Evidence |
|---|---|---|---|
| 1 | Avsec et al 2026, Nature, doi:10.1038/s41586-025-10014-0 | VERIFIED | Crossref: title/authors/year match; not retracted |
| 2 | Wakefield et al 1998, Lancet | RETRACTED | Real paper (Crossref), but retracted 2010-02-06 — do not cite as supporting evidence |
| 3 | Zhang & Patel 2023, Nature Cell Biology, "Quantum entanglement mediated CRISPR..." | NOT FOUND | No candidate across Crossref/PubMed/Semantic Scholar matches this title+author+year combination |
| 4 | Lee 2021, J Immunol, vol 12 | MISMATCH | Paper exists (PMID 12345678) but published in *Cell Reports*, not *J Immunol*; year is correct |

## Summary: X verified, Y mismatched, Z not found, W retracted, V ambiguous
```

Order the table by input order, not by verdict — the user needs to map
results back to their original list.

## Stop conditions

- Cap structured-database effort at ~4 tool calls per entry (a DOI-path
  entry can legitimately need registry + fallback registry + cross-check +
  retraction check). The one-web-search last resort is *in addition* to
  this cap, not part of it — but is still exactly one search, not a hunt.
  If nothing plausible turns up after that, classify NOT FOUND or AMBIGUOUS
  rather than continuing to search — don't burn the budget chasing one
  stubborn reference in a 40-entry bib file.
- A source errors (API key, rate limit, 5xx) → note it, drop to the remaining
  sources for that entry, don't let one dead source stall the whole batch.
- Very large batches (50+ entries): process all of them, but say up front
  how many you're checking and don't silently skip entries — if you truncate,
  say so and name what was skipped.

## When this is overkill

- The user just wants a paper's own metadata (not verifying a citation of
  it) → a direct `Crossref_get_work` / `PubMed_get_article` lookup is enough.
- The user wants to know whether a *claim* is well-supported by the
  literature (not whether a specific citation is accurately described) →
  that's `/cross-validate` or `/literature-sweep`, not this.
