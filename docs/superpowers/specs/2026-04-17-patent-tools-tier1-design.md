# Patent Tools Tier 1 -- Design Spec

| Field  | Value      |
|--------|------------|
| Date   | 2026-04-17 |
| Status | Approved   |

## Problem

ToolUniverse has 6 existing USPTO ODP tools, but all require
`applicationNumberText` as input. Users have patent numbers (e.g.,
US9629826B2), not application numbers (e.g., 14966067). There is no resolver.

FTO-critical data -- assignments, claims, prosecution history, and AI-enriched
citations -- has no tools at all. Patent practitioners cannot perform
freedom-to-operate analysis without leaving ToolUniverse.

## Decision Record

- **PatentsView is dead.** The API migrated to ODP on 2026-03-20. All
  PatentsView endpoints return 404. Do not build against it.
- **No dedicated claims endpoint.** ODP does not expose patent claims as
  structured data. The workaround is to download grant XML via
  `associated-documents` and parse the `<claims>` element.
- **Assignment endpoint is singular.** `/assignment` returns 200.
  `/assignments` returns 403. The Swagger docs are misleading.
- **DSAPI endpoints are high-value FTO data.** Office Action text, citations,
  rejections, and enriched citations (with X/Y/A/E category codes) are
  available via the DSAPI sub-API and are not covered by any existing tool.

## Deliverables

6 tools + 1 base class.

### Tool 1: USPTO_patent_number_to_application

Patent number resolver. Searches ODP with a field-specific query on
`applicationMetaData.patentNumber` to return the corresponding
`applicationNumberText`. Handles grant numbers, application numbers (passthrough
after stripping punctuation), and publication numbers (via
`earliestPublicationNumber`).

### Tool 2: USPTO_get_patent_assignment

JSON-config tool. Hits the `/assignment` endpoint (singular -- `/assignments`
returns 403). Returns assignee chain, conveyance text, execution dates, and
reel/frame numbers.

### Tool 3: USPTO_get_patent_transactions

JSON-config tool. Hits the `/transactions` endpoint. Returns prosecution
history: office actions, responses, allowances, and issue events with dates.

### Tool 4: USPTO_get_patent_claims

Downloads grant XML from the `associated-documents` endpoint
(`grantDocumentMetaData.fileLocationURI`), then parses the `<claims>` element
to extract structured claim text. Returns independent and dependent claims with
claim numbers.

### Tool 5: USPTO_search_enriched_citations

DSAPITool subclass. POSTs Lucene queries to the enriched-citations DSAPI
endpoint. Returns prior art citations with category codes:

- **X** -- Particularly relevant (alone)
- **Y** -- Particularly relevant (in combination)
- **A** -- General technological background
- **E** -- Earlier patent document with later publication date

### Tool 6: USPTO_patent_deep_lookup

Batch pipeline tool. Accepts one or more patent numbers, resolves each to an
application number, then fans out to assignments, transactions, claims, and
enriched citations in parallel. Includes rate limiting (burst=1, 4 req/s
default) and structured multi-patent output for FTO analysis.

### DSAPITool Base Class

Abstract base class for Office Action DSAPI endpoints. Handles:

- POST request construction with Lucene query syntax
- Pagination (offset/limit)
- Response normalization
- Error handling for the DSAPI-specific error format

## Code Standards

- Follow `python-library.md` template from the repo's coding standards
- Section dividers between logical blocks
- Inline comments explaining non-obvious logic
- Beginner-readable: no clever tricks, explicit over implicit

## Build Order

1. JSON config tools (assignment, transactions) -- simplest, validates ODP
   connectivity
2. Patent number resolver -- required by everything downstream
3. Claims extractor -- XML download + parsing
4. DSAPI base class + enriched citations
5. Deep lookup pipeline -- orchestrates all of the above

## Test Patents

| Patent        | Application | Entity     |
|---------------|-------------|------------|
| US9629826B2   | 14966067    | ForwardVue |
| US10844125B2  | 16286857    | Nuvig      |
| US12000000B2  | 18045436    | PacBio     |
