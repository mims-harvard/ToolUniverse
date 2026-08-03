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

The scheduled scanner has two approved OpenAPI directory adapters:

- APIs.guru, a general API directory;
- SmartAPI, a biomedical API registry.

A separate provider-independent path scans a sealed manifest of reviewed
official biomedical service contracts. It uses the same inert inspection and
promotion boundaries without adding provider-specific scanner code. See
`VSD_FEDERATED_BIOMEDICAL_SOURCES.md` for the source admission contract, live
results, and reproducibility instructions.

SmartAPI is read in pages of 100 records so each response remains below the
existing 10 MB transport ceiling. Swagger 2 records remain inventoried as
unsupported rather than being silently converted. A catalog adapter is not a
trust elevation: every directory record and operation remains unreviewed. The
generic official-host crawler in `tooluniverse-vsd-sources` continues to find
all seven supported contract formats on explicitly selected hosts.

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

Every attempted record, including a failed contract, is retained in scanner
state. This prevents an unchanged invalid record from starving later records.
If a process writes an immutable cycle and stops before replacing `latest.json`,
the next run recovers a single unambiguous child from the hash-linked history.
A fork, broken link, catalog mismatch, or modified cycle fails closed. A final
partial batch stops when all compatible records have been attempted instead of
repeating earlier records to fill the batch.

## Scheduled use

Run one bounded cycle:

```console
tooluniverse-vsd-scan --state-directory ~/.tooluniverse/vsd/scanner/apis-guru \
  run --catalog apis-guru --max-contracts 100 --draftable-tool-target 500
tooluniverse-vsd-scan --state-directory ~/.tooluniverse/vsd/scanner/smartapi \
  run --catalog smartapi --max-contracts 100 --draftable-tool-target 500
```

Read the latest sealed summary without contacting a provider:

```console
tooluniverse-vsd-scan --state-directory ~/.tooluniverse/vsd/scanner/apis-guru status
tooluniverse-vsd-scan --state-directory ~/.tooluniverse/vsd/scanner/smartapi status
```

The `run` command is suitable for cron, a systemd timer, Windows Task
Scheduler, or another administrator-owned scheduler. Cross-process locking
prevents overlapping cycles. Contract snapshots are content-addressed, so an
unchanged document is stored once. Use a separate state directory for each
catalog; the scanner rejects a catalog identity change within an existing
history.

## Live scale evaluation

The exhaustive checked evaluation ran both live catalogs to completion against
the real ToolUniverse registry. It processed every compatible directory record
through 25 bounded, hash-linked cycles:

| Measure | Result |
| --- | ---: |
| Catalogs | 2 |
| Directory records | 2,799 |
| Compatible OpenAPI 3 records processed | 1,748 |
| Existing ToolUniverse tools audited | 2,744 |
| Existing ToolUniverse source hosts audited | 259 |
| Unique contracts inspected | 1,626 |
| Unique operation candidates inventoried | 37,570 |
| Unique draft-ready config hashes | 3,097 |
| Provider hosts represented | 203 |
| Coarse scientific-vocabulary matches | 309 |
| Blocked operations | 36,362 |
| Isolated contract failures | 131 |

The full report is
`examples/vsd/artifacts/continuous_catalog_expansion_study.md`; the
tamper-evident ledger is
`examples/vsd/artifacts/continuous_catalog_expansion_study.json`, SHA-256
`10ce696555b9de42a2bdf1fa1c86ac746a8c631b8c0e4e9b2dff3d3c513e7bd8`.

The recorded evidence includes 127 redundant attempts from the older
partial-final-batch behavior. Contract, operation, and configuration hashes
deduplicate those repetitions, and the corrected selector is covered by a
focused regression test. The production scanner retains contract snapshots;
only the exhaustive evaluation runner prunes them after each sealed cycle to
bound study storage while keeping source, candidate, config, and cycle hashes.

The 3,097 results are not published tools. They are distinct read operations
accepted by static inspection and configuration generation. Each still requires
representative provider execution, explicit approval, publication, loading, and
lifecycle maintenance.

## Exhaustive candidate review

`candidate_portfolio_review_study.py` applies one versioned, provider-independent
policy to all 3,097 draft-ready configurations. It refreshes all 290 contracts
that produced those configurations, reinspects their current operations, and
matches each saved candidate hash before assigning a final disposition. The
review completed with all 290 contracts available and all 3,097 candidate hashes
unchanged.

| Final disposition | Candidates |
| --- | ---: |
| Eligible for demand-driven verification | 1,325 |
| Research-facing scientific candidates within that set | 139 |
| Lower-value service utility candidates within that set | 81 |
| Held or superseded | 1,772 |

The original count of 309 used intentionally broad substring vocabulary during
the scale scan. Exact tokenization and contract-aware review reduced that signal
to 235 scientific-context matches, of which 139 had a current, usable response
contract and no higher-priority policy hold. This correction excludes incidental
matches such as words containing `gene` and does not change the historical scan
ledger.

The live phase selected seven no-input scientific operations using the same
generic ranking policy and at most two operations per host. Five passed three
hash-bound calls each and remained unapproved and unpublished; two remote calls
timed out and remained rejected or deferred. Parameterized operations are not
called without a concrete workflow and representative inputs. The cancer
qualification below provides that stronger demand-driven test.

Run the review against completed scanner history:

```console
PYTHONPATH=src uv run python examples/vsd/candidate_portfolio_review_study.py \
  --state-root ./.vsd-continuous-expansion
PYTHONPATH=src uv run python examples/vsd/candidate_portfolio_review_study.py \
  --validate-only
```

The readable report is
`examples/vsd/artifacts/candidate_portfolio_review_study.md`; the complete
machine-readable decision ledger is
`examples/vsd/artifacts/candidate_portfolio_review_study.json`, SHA-256
`3f1a99d861d851ab43983251987f5664b4ed1262605de6d71ef8aced2d0f29a4`.

## Scientific workflow relationship

The scanner supplies breadth; the cancer qualification study measures how that
breadth becomes governed capability. A data-driven manifest selected eight
exact missing operations from the scanner inventory. Four operations passed
five live cases each, were explicitly approved and published, loaded into a
fresh ToolUniverse instance, and completed 20 post-publication calls across
breast, lung, colorectal, melanoma, and prostate workflows. Four other
statically draft-ready operations were rejected because their live responses
violated the published response schemas; approval and publication remained
blocked.

The accepted tools retrieved terminology matches, gene-symbol relationships,
regulatory linked-record counts, and bounded computational drug hypotheses.
Those outputs retain separate interpretations and are not combined into a
clinical score. Review
`examples/vsd/artifacts/scanner_cancer_qualification_study.md` and its
machine-verifiable JSON counterpart, SHA-256
`cb5a36ae24abb4ccc6b7d98d7ab4aae0026e26b43aff709568e8c0a014e78a7e`.
