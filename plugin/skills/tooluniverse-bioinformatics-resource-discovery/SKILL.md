---
name: tooluniverse-bioinformatics-resource-discovery
description: "Discover which bioinformatics software tool, biomedical REST API, R/Bioconductor package, CRAN package, or training material exists for a task, before writing analysis code or building a pipeline. Covers ELIXIR bio.tools (30,000+ software tools/databases by keyword, EDAM topic, or EDAM operation), SmartAPI (biomedical API registry, incl. NCATS Translator components), ELIXIR TeSS (bioinformatics training materials/events), Bioconductor (R packages for computational biology), and CRAN (general R packages). Use when someone asks 'is there an existing tool/package for X', 'what software does [analysis]', 'find an API for Y', or 'is there a tutorial on Z'."
disable-model-invocation: true
---

# Bioinformatics Resource Discovery

Answers "what already exists for this task" — software, APIs, R packages, or training material — **before** writing new analysis code, choosing an nf-core pipeline, or wrapping a new REST API by hand.

**LOOK UP, DON'T GUESS**: Never assert that a tool/package/API does or doesn't exist for a task from memory. These 5 registries are live and current — search them.

## When to Use This Skill

- "Is there existing software for [bioinformatics task]?" -> bio.tools
- "What biomedical APIs exist for [domain], and where's the base URL/spec?" -> SmartAPI
- "Is there a tutorial/course on [technique]?" -> ELIXIR TeSS
- "What R package does [analysis] in Bioconductor?" -> Bioconductor
- "What does CRAN package X do / what version / what does it depend on?" -> CRAN

**NOT for**: actually running an nf-core pipeline once you've picked one (-> `tooluniverse-nfcore-pipelines`); resolving IDs between databases (-> `tooluniverse-sequence-retrieval`'s Bioregistry/Identifiers.org/TogoID section); retrieving biological data itself (sequences, structures, expression) rather than software/APIs about it.

## 1. bio.tools — Bioinformatics Software & Database Registry

ELIXIR's registry of 30,000+ bioinformatics tools, web services, and databases.

| Tool | Use for | Key params |
|---|---|---|
| `BioTools_search` | Free-text keyword search across name/description/topics | `q`, `page`, `size` (max 50) |
| `BioTools_get_tool` | Full record for a known tool by its bio.tools ID | `biotoolsID` |
| `BioTools_search_by_topic` | Filter by EDAM scientific topic (e.g. "Genomics", "Proteomics") | `topic`, `page`, `size` |
| `BioTools_search_by_operation` | Filter by EDAM operation — what the tool DOES (e.g. "Sequence alignment", "Variant calling") | `operation`, `page`, `size` |
| `BioTools_search_by_type` | Filter by resource type | `toolType` (e.g. "Database portal"), `q`, `page`, `size` |

Verified live: `BioTools_search {"q": "RNA-seq", "size": 3}` -> 6,079 total matches. `BioTools_get_tool {"biotoolsID": "blast"}` -> the real BLAST record (homepage, EDAM operations, full description). `BioTools_search_by_topic {"topic": "Genomics"}` -> 10,165 matches; `BioTools_search_by_operation {"operation": "Sequence alignment"}` -> 5,890 matches; `BioTools_search_by_type {"toolType": "Database portal"}` -> 2,597 matches — note `toolType` is the required param name, not `tool_type`, and `topic`/`operation` searches return a real, differently-sized result set per filter even when the very top-ranked item coincides across filters (bio.tools' own relevance/recency ranking, not a wrapper bug) — always check `count` and page through more than the first result.

## 2. SmartAPI — Biomedical API Registry

~270 OpenAPI-described biomedical web APIs, many of them NCATS Biomedical Data Translator components (BioThings APIs, knowledge-provider APIs).

| Tool | Use for | Key params |
|---|---|---|
| `SmartAPI_search_apis` | Keyword or field-scoped Lucene search (e.g. `tags.name:translator`) | `query`, `limit` (max 100) |
| `SmartAPI_get_api` | Full spec for one API: base URLs, endpoint list, contact | `api_id` |

Verified live: `SmartAPI_search_apis {"query": "biothings", "limit": 3}` -> real APIs including "Biothings Therapeutic Target Database API" (`base_url: https://biothings.transltr.io/ttd`) and "MyGeneset.info API". Feeding that `api_id` into `SmartAPI_get_api` returns `base_urls` (prod/test/CI variants), `endpoint_count: 5`, and the actual endpoint paths (`/query`, `/metadata`, `/association/{id}`, ...).

**Use this to find an API not yet wrapped as a dedicated ToolUniverse tool** — resolve its base URL and endpoints here, then either call it directly (if simple/one-off) or use `tooluniverse-create-tool`/`devtu-create-tool` to wrap it properly. Also useful for resolving an API mentioned in a paper's methods section to its actual current base URL.

## 3. ELIXIR TeSS — Training Materials & Events

Aggregates bioinformatics/life-science tutorials, courses, webinars, and events from ELIXIR nodes and partners.

| Tool | Use for | Key params |
|---|---|---|
| `ELIXIRTeSS_search_materials` | Find tutorials/courses/webinars | `q`, `scientific_topics` (EDAM), `target_audience`, `difficulty_level`, `licence`, `page_size`, `page` |
| `ELIXIRTeSS_search_events` | Find live/scheduled training events | `q`, plus similar filters |

Verified live: `ELIXIRTeSS_search_materials {"q": "RNA-seq", "page_size": 3}` -> real materials, e.g. "A practical introduction to bioinformatics and RNA-seq using Galaxy". `ELIXIRTeSS_search_events {"q": "bioinformatics"}` -> real upcoming events (e.g. a 2026-09-21 SIB Swiss Institute of Bioinformatics course, "Feature Selection for Bioinformatics with Python"). A query with zero matches (e.g. `q: "CRISPR"` at time of testing) returns a clean empty list, not an error — confirmed by re-running with a broader query and an empty-query call, both of which returned real, different, non-empty result sets, so treat an empty result as "nothing currently listed for that exact term," not a broken call.

## 4. Bioconductor — R Packages for Computational Biology

2,200+ R packages for RNA-seq, single-cell, proteomics, epigenomics, and more, indexed via the R-universe search API.

| Tool | Use for | Key params |
|---|---|---|
| `Bioconductor_search_packages` | Keyword/topic search | `q`, `limit` (max 100) |
| `Bioconductor_get_package` | Full metadata for a known package | `package_name` (exact, case-sensitive) |

Verified live: `Bioconductor_search_packages {"q": "differential expression", "limit": 3}` -> real packages ranked by relevance score (`_score`), e.g. `compcodeR`. `Bioconductor_get_package {"package_name": "DESeq2"}` -> the real current DESeq2 record (`Version: "1.53.3"`, full author list, description) — note the param is `package_name`, not `package` (that name is reserved for the separate CRAN tools below; passing `package` to this tool fails validation).

## 5. CRAN — General R Package Registry

20,000+ general R packages (via the `crandb` mirror) — use for R packages outside Bioconductor's bio-specific scope (stats, viz, data wrangling, and bio-adjacent packages like `survival`).

| Tool | Use for | Key params |
|---|---|---|
| `CRAN_get_package` | Current metadata: version, description, license, dependencies | `package` (exact, case-sensitive) |
| `CRAN_get_package_versions` | Full release history | `package` |

Verified live: `CRAN_get_package {"package": "ggplot2"}` -> real current metadata (`Version: "4.0.3"`, full author list, license). `CRAN_get_package_versions {"package": "ggplot2"}` -> full version history back to `0.5` (2007-01-01) with each version's own metadata snapshot.

## Choosing Among the Five Resources

| Resource | What it holds | Example question |
|---|---|---|
| **bio.tools** (Sec. 1) | Bioinformatics software/services/databases, catalogued by EDAM topic & operation | "What tools do variant calling from BAM files?" |
| **SmartAPI** (Sec. 2) | Live biomedical REST APIs with machine-readable specs | "What's the base URL and endpoints for the BioThings TTD API?" |
| **ELIXIR TeSS** (Sec. 3) | Training materials and events | "Is there a beginner RNA-seq course I can point someone to?" |
| **Bioconductor** (Sec. 4) | R packages specifically for computational biology | "What Bioconductor package does differential expression on RNA-seq counts?" |
| **CRAN** (Sec. 5) | General-purpose R packages (incl. bio-adjacent) | "What does the `survival` package's current version support?" |

A `Bioconductor_search_packages` hit and a `CRAN_get_package` hit can both resolve for a genuinely bio-relevant R package (e.g. `survival` lives on CRAN, not Bioconductor) — try Bioconductor first for a task that sounds computational-biology-specific, and fall back to CRAN if it's a general statistics/viz need or Bioconductor returns nothing relevant.

## Common Pitfalls

- **Parameter name mismatches across similarly-shaped tools**: `Bioconductor_get_package` takes `package_name`; `CRAN_get_package`/`CRAN_get_package_versions` take `package`; `BioTools_search_by_type` takes `toolType` (camelCase), not `tool_type`. Don't assume a shared convention across these 5 resources — check each tool's own schema.
- **A shared top result across different filters on bio.tools is not a bug** — verify by checking the `count` field, which does differ, and by paging further if the very top hit looks generic.
- **An empty ELIXIR TeSS result is a real "nothing listed," not a broken call** — retry with a broader query before concluding the tool is down.
