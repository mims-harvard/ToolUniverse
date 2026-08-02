# VSD Multi-Catalog API Discovery

## Scope

`VSDDiscoverAPICandidates` converts a non-sensitive research capability into
reviewable data-endpoint and OpenAPI leads. Omitting `providers` preserves the
original Socrata-only response contract. Supplying `providers` enables the
normalized multi-catalog path:

```python
result = tu.run_one_function(
    {
        "name": "VSDDiscoverAPICandidates",
        "arguments": {
            "query": "ALS longitudinal cohort outcomes specialist access",
            "providers": [
                "socrata",
                "datagov",
                "data_europa",
                "ckan_data_gov_uk",
                "apis_guru",
            ],
            "exclude_registered": True,
            "limit": 20,
        },
    },
    use_cache=False,
)
```

The result is an inventory, not a tool installation. Every candidate is
`unreviewed_candidate`, contains `execution_allowed: false`, and must pass
contract inspection, representative verification, approval, publication, and
explicit loading before an agent can execute it.

## Reviewed Catalog Providers

| Provider ID | Fixed catalog | Candidate form | Request boundary |
| --- | --- | --- | --- |
| `socrata` | Socrata Discovery API | SODA JSON endpoint | 1 MB, no credential |
| `datagov` | US Data.gov Catalog API v4 | JSON, CSV, XML, or SODA endpoint | 1 MB, `TOOLUNIVERSE_DATAGOV_API_KEY` or the public demo key |
| `data_europa` | European Data Portal Hub Search | JSON, CSV, or XML distribution | 10-result page, 1 MB |
| `ckan_data_gov_uk` | data.gov.uk CKAN backend | JSON, CSV, or XML resource | 1 MB, no credential |
| `apis_guru` | APIs.guru OpenAPI Directory | OpenAPI document | complete directory, hard 10 MB ceiling |

The integrations follow the providers' published interfaces: [Data.gov Catalog
API](https://resources.data.gov/catalog-api/), [European Data Portal Hub
Search](https://data.europa.eu/api/hub/search/), [CKAN package
search](https://docs.ckan.org/en/2.11/api/), and the [APIs.guru OpenAPI
Directory](https://apis.guru/api-doc/). The data.gov.uk request uses its final
HTTPS CKAN backend because the public URL redirects across two hosts.

Adding a provider is a code change. It requires a fixed endpoint, exact-host
allowlisting, a bounded request plan, a strict payload normalizer, deterministic
fixtures, failure-isolation tests, and a live integration check. Users cannot
turn an arbitrary search engine or URL into a catalog provider through tool
arguments.

## Normalized Candidate Contract

All providers produce the same bounded record:

- stable candidate ID derived from the endpoint or specification URL
- `data_endpoint` or `openapi_specification` candidate kind
- catalog provider, record identity, publisher, license, and update metadata
- machine-readable format and interface type
- exact catalog provenance records retained during cross-catalog merging
- canonical SHA-256 digest covering the complete normalized candidate
- transparent relevance, readiness, provenance, and completeness score
- untrusted-metadata and non-executable boundary labels

HTML pages, archives, malformed URLs, non-HTTPS resources, credential-bearing
URLs, nonstandard ports, and unsupported media formats are discarded. A query
with more than three meaningful terms must match at least two terms; shorter
queries must match at least one. APIs.guru needs this explicit filter because
its directory endpoint returns the complete index rather than performing
server-side search.

## Ranking And Deduplication

The deterministic score is:

- 50% query-token coverage
- 5% exact-phrase match
- 15% usable endpoint or specification
- 10% explicit OpenAPI contract
- 8% official catalog label
- 5% government-domain signal
- 7% publisher, license, and update-metadata completeness

The response includes the complete score breakdown and matched-term count.
Exact endpoint or specification URLs are merged across catalogs while retaining
every catalog record as provenance. When `exclude_registered` is true, the
ToolUniverse registry is loaded once and exact GET host/path operation matches
are removed with their matching tool names and registry hash. Semantic partial
matches remain visible for review; they are not treated as duplicates.

One catalog failure does not discard successful results from the others. Each
provider reports its own status, counts, bounded error, request metadata, and
payload SHA-256. The operation fails closed only when every requested provider
fails.

## Fixed-Resource Promotion

Machine-readable catalog distributions that have no operation contract can be
promoted only through a narrow reviewed-resource path. The administrator must
provide a valid `VSDReviewedOperationTool` configuration whose endpoint, fixed
query, and response format exactly match the content-addressed candidate. The
request must be an anonymous, input-free GET with no custom headers, body, or
pagination. Endpoint substitution, format substitution, a modified candidate,
or any variable or active request fails before a draft is written.

```console
tooluniverse-vsd-promote --workspace ./private-vsd-promotion \
  draft-catalog-resource discovery.json reviewed-config.json \
  --candidate-id <candidate-id> \
  --review-note "Reviewed exact endpoint, format, schema, and response bounds."
```

The draft records the candidate digest, exact resource identity, catalog
provenance, response format, and a binding digest. It still must pass
representative verification, explicit approval, publication, and loading
before execution. This path intentionally does not synthesize an arbitrary
parameterized API from catalog metadata.

## Live Cancer Portfolio Proof

`examples/vsd/multicatalog_cancer_case_study.py` starts with repeated unmet
demand for exact breast-cancer trial and mortality capabilities. It then runs
five focused cancer searches through Socrata, US Data.gov, the European Data
Portal, data.gov.uk, and APIs.guru to cover trial, mortality, outcome, access,
and molecular evidence roles. Each selected lead remains inert while its real
resource or OpenAPI contract is qualified.

Only two leads cross the lifecycle: the Roswell Park SODA endpoint by exact
primary-site query and Ireland's fixed principal-cause-of-death JSON-stat cube,
which supplies malignant-neoplasm counts through 2024 by age group. Three other
leads prove the rejection boundaries: the live Oklahoma outcome URL redirects
to a signed object-store URL and is blocked before retrieval, its captured
direct response is stale and sparse, a Northern Ireland resource fails its
declared CSV media contract, and five Google Genomics operations fail contract
inspection.
The accepted tools pass six verification executions, cannot publish early, are
absent from a fresh registry until explicitly loaded, execute through the
normal ToolUniverse API, close both exact planning gaps, and suppress their own
endpoints during repeat discovery.

```console
PYTHONPATH=src python examples/vsd/multicatalog_cancer_case_study.py --mode replay
TOOLUNIVERSE_DATAGOV_API_KEY=... PYTHONPATH=src \
  python examples/vsd/multicatalog_cancer_case_study.py --mode live
PYTHONPATH=src python examples/vsd/multicatalog_cancer_case_study.py \
  --mode network_backed
```

The checked network-backed report and audit snapshot are
`examples/vsd/artifacts/multicatalog_cancer_snapshot.md` and
`examples/vsd/artifacts/multicatalog_cancer_snapshot.json`. This mode labels the
captured Data.gov catalog response explicitly while keeping the other four
catalogs and all five selected candidate resources/contracts live. The replay
uses small excerpts captured from the same real responses, and the opt-in
integration test performs the complete live run with a personal Data.gov key.

## Rare-Disease Deduplication Proof

`examples/vsd/multicatalog_discovery_case_study.py` starts with a real planning
gap: a comparative ALS, Duchenne muscular dystrophy, and spinal muscular
atrophy workflow needs longitudinal progression, genotype, clinical-outcome,
and specialist-access measures. Three preflights record the same missing
capability before the agent-facing tool searches all five catalogs.

Ten deterministic catalog records become five relevant candidates after URL,
format, relevance, and exact-identity deduplication. Data.gov and Socrata point
to the same endpoint. An administrator binds that endpoint to a local OpenAPI
contract; early publication fails, three distinct cohort cases pass schema and
exact-value verification, and the approved tool is loaded into a fresh
ToolUniverse instance. Replanning then reports exact coverage, and a repeated
catalog search suppresses the already-registered endpoint with an auditable
reason.

Run the proof from the repository root:

```console
PYTHONPATH=src python examples/vsd/multicatalog_discovery_case_study.py
```

The checked artifacts are:

- `examples/vsd/artifacts/multicatalog_discovery_snapshot.md`
- `examples/vsd/artifacts/multicatalog_discovery_snapshot.json`
- `examples/vsd/artifacts/multicatalog_discovery_demand_proposal.json`

The unit portfolio runs the complete study twice to prove reproducibility and
then modifies the snapshot to prove audit-hash tamper detection.

## Security Boundary

Catalog metadata does not establish scientific validity, provider ownership,
license compatibility, runtime safety, or approval. Catalog API keys are sent
only in reviewed headers and are represented in provenance by the environment
variable name, never the value. Discovery does not crawl candidate hosts,
download candidate specifications, call candidate endpoints, create drafts,
approve tools, publish tools, or report local demand to the core team.
