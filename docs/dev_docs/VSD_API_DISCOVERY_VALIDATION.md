# VSD Demand-Driven API Discovery

## Scope

This phase turns a research demand into concrete public-data API candidates.
The agent-facing `VSDDiscoverAPICandidates` tool searches only the fixed,
keyless Socrata catalog endpoint. It does not crawl the web, probe candidate
hosts, execute candidates, generate tools, or approve scientific content.

Each returned candidate is labeled `unreviewed_candidate`, carries
`execution_allowed: false`, and treats provider descriptions and tags as
untrusted catalog metadata. A later administrator-only phase must create and
verify a bounded operation contract before ToolUniverse can execute it.

## Ranking

Candidates must be tabular datasets with a syntactically valid Socrata domain,
dataset identifier, and field schema. The deterministic score combines:

- 55% demand-token coverage across title, description, tags, and fields
- 10% exact-phrase match
- 20% API and field-schema readiness
- 10% the catalog's official-provenance label
- 5% a government-domain signal

The complete score breakdown is returned; no candidate is silently promoted.

## End-to-End Proof

`examples/vsd/api_discovery_case_study.py` asks for an active cancer-trial data
source supporting protocol, primary site, phase, title, opening date, and
principal investigator. It calls the packaged discovery tool through a real
`ToolUniverse.run_one_function()` path, maps the demand to returned fields, and
selects a candidate for human contract review only when at least five of six
capabilities are present alongside the official, government, and API-ready
signals.

The checked artifacts are:

- `examples/vsd/artifacts/api_discovery_snapshot.json`
- `examples/vsd/artifacts/api_discovery_snapshot.md`

The proof demonstrates demand-to-source discovery. It does not claim the
catalog result is scientifically valid, approved, or safe to execute.
