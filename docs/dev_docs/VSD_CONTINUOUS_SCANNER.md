# Continuous VSD Catalog Scanner

## Purpose

The continuous scanner is an administrator-controlled supply pipeline for VSD.
It inventories an approved API directory on a schedule, detects additions and
changes, rotates through previously uninspected contracts, compares their exact
operation identities with ToolUniverse, and prepares a local queue of inert
operation candidates. It never verifies responses, approves candidates,
publishes tools, loads configurations, or executes provider operations.

The scanner complements demand-driven growth. Workflow planning and the private
demand ledger identify capabilities researchers repeatedly need; the scanner
provides a changing inventory of possible operations. A reviewer can match the
two before spending effort on representative verification and maintenance.

## Accepted contract inputs

The existing source-intelligence and local inspection boundaries accept:

- OpenAPI 3.0 and 3.1
- GraphQL schema introspection documents and SDL
- AsyncAPI
- Postman collections
- WSDL
- protobuf service definitions
- MCP manifests

The scheduled large-directory adapter currently uses the APIs.guru OpenAPI
Directory. This is a catalog adapter, not a trust elevation: every directory
record and operation remains unreviewed. The generic official-host crawler in
`tooluniverse-vsd-sources` continues to find all seven supported contract
formats on explicitly selected hosts.

## Cycle behavior

Each `run` command performs these steps:

1. download the complete approved directory through the bounded VSD transport;
2. normalize and hash every catalog record;
3. compare the record index with the previous sealed cycle;
4. prioritize new, changed, and previously uninspected compatible contracts;
5. save selected contracts as content-addressed local snapshots;
6. inspect operations without network execution;
7. compare supported read operations with reviewed ToolUniverse operation
   identities and known source hosts;
8. invoke the existing config generator and retain only the resulting config
   hash for draft-ready candidates;
9. atomically write immutable cycle history and `latest.json`.

Failed contracts are isolated. Unsupported authentication, writes, request
bodies, missing response schemas, non-public server identities, incompatible
parameters, and other contract blockers remain recorded instead of being
relaxed.

## Scheduled use

Run one bounded cycle:

```console
tooluniverse-vsd-scan --state-directory ~/.tooluniverse/vsd/scanner run \
  --max-contracts 100 --draftable-tool-target 500
```

Read the latest sealed summary without contacting a provider:

```console
tooluniverse-vsd-scan --state-directory ~/.tooluniverse/vsd/scanner status
```

The `run` command is suitable for cron, a systemd timer, Windows Task
Scheduler, or another administrator-owned scheduler. Cross-process locking
prevents overlapping cycles. Contract snapshots are content-addressed, so an
unchanged document is stored once.

## Live scale evaluation

The checked two-cycle evaluation used the complete live APIs.guru directory and
the real ToolUniverse registry:

| Measure | Result |
| --- | ---: |
| Directory records | 2,529 |
| Compatible OpenAPI 3 records | 1,521 |
| Existing ToolUniverse tools audited | 2,744 |
| Existing ToolUniverse source hosts audited | 259 |
| Unique contracts inspected | 127 |
| Unique operation candidates inventoried | 4,925 |
| Unique draft-ready config hashes | 717 |
| Provider hosts represented | 31 |
| Blocked operations | 4,281 |
| Isolated contract failures | 24 |

The full report is
`examples/vsd/artifacts/continuous_catalog_scanner_portfolio.md`; the
tamper-evident ledger is
`examples/vsd/artifacts/continuous_catalog_scanner_portfolio.json`, SHA-256
`4181b8af874d3fb6c86a51546b8125fc93b560672732f935d671ff915a5cd054`.

The 717 results are not published tools. They demonstrate that the catalog records
contained 717 distinct read operations accepted by the existing static
inspection and configuration-generation boundaries. Each still requires
representative provider execution, explicit approval, publication, and loading.

## Scientific workflow relationship

The scanner supplies breadth; the earlier scientific evaluations establish how
individual candidates become useful capabilities. Those studies include live
ClinicalTrials.gov retrieval for ALS, multi-catalog cancer evidence using a
trial registry and a population mortality cube, and live GA4GH service
qualification. In each case, ToolUniverse reused existing tools first and VSD
addressed only a specific missing operation. This avoids equating catalog scale
with scientific value.
