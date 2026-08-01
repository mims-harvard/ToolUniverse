# VSD Hardening and Validation

## Purpose

This change is a focused follow-up to ToolUniverse PR #413. It preserves the
Verified Source Directory workflow while closing the security, state-integrity,
and product-boundary gaps found during adversarial review. Mutable catalog
operations now live behind an explicit administration CLI. The default
ToolUniverse surface contains only reviewed, read-only, source-specific tools
with constrained inputs, normalized outputs, and concrete provenance.

## Corrected Behavior

| Area | Previous behavior | Corrected behavior |
| --- | --- | --- |
| Network destination | DNS was checked before the request, but the peer was checked only after transmission. | The request connects to one vetted public IP while TLS, SNI, certificate, and HTTP `Host` validation retain the original hostname. The connected peer must equal the pinned IP. |
| Redirects | Up to three redirects were followed after validation. | Every redirect is rejected. This keeps one validation and one connection target per tool call. |
| Response bound | `iter_content` could decompress a small encoded response before applying the 1 MB count. | Requests advertise identity encoding, any non-identity response is rejected before reading, and undecoded bytes are capped at 1 MB. |
| Request duration | The read timeout was an inactivity timeout, so a slow stream could retain a worker indefinitely. | Connection, header, and body processing share one wall-clock deadline; raw socket reads use the remaining duration. |
| JSON contract | Any media type containing `json` and Python's non-standard `NaN`/`Infinity` values were accepted. | Only `application/json` or `+json` media types and standards-compliant JSON numbers are accepted. |
| Catalog writes | A process-local thread lock protected atomic replacement, but concurrent processes could lose updates. | A cross-platform OS file lock covers each complete read-modify-write transaction, and the replacement file is flushed and synchronized before atomic replace. |
| Duplicate IDs | Registration silently overwrote an existing source. | Duplicates fail before probing unless the caller explicitly supplies `replace=true`; the result reports whether replacement occurred. |
| Agent boundary | Mutable catalog tools and a generic arbitrary-JSON proxy were loaded as scientific tools. | Register, list, generic query, and remove are available only through `tooluniverse-vsd-admin`; they are absent from the default registry and generated SDK. |
| Scientific contracts | A successful reachability probe produced an untyped `result: {}` and could be mistaken for scientific verification. | Four packaged integrations map to individual read-only tools with fixed endpoints, constrained parameters, typed return schemas, source-specific validation, and an explicit statement that adapter review is not scientific endorsement. |
| Host information | Registration returned the absolute catalog path. | Tool results and catalog validation errors do not expose host filesystem paths. |

## Regression Evidence

The concurrency test starts two independent Python processes at the same time and
widens the old read/write race. On the original implementation both processes
reported success while the final catalog contained only one source. With the OS
lock, both sources are present on every completed run.

The transport tests verify the selected connection address, preserved TLS
hostname and `Host` header, exact peer match, rejection of gzip/Brotli encodings
before body reads, redirect rejection, total-deadline enforcement, strict media
types, standards-compliant JSON, and credential-like path rejection. ToolUniverse
contract tests load the actual tool configurations, prove the generic and mutable
operations are absent, validate the generated SDK surface, and execute normalized
provider output through `ToolUniverse.run_one_function()`.

Run the focused proof suite from the repository root:

```bash
python -m pytest -o addopts= \
  tests/unit/test_vsd_tools.py \
  tests/unit/test_vsd_transport_security.py \
  tests/unit/test_vsd_catalog_concurrency.py \
  tests/unit/test_vsd_admin_cli.py \
  tests/unit/test_vsd_reviewed_sources.py \
  tests/unit/test_vsd_tool_contracts.py \
  tests/unit/test_vsd_public_health_case_study.py -q
```

The focused lane passed all 68 transport, concurrency, administration,
source-adapter, ToolUniverse-contract, complete-grid, screening, evidence, and
artifact tests. An additional 60 generated-wrapper, package-import, validator,
and base-tool tests passed as adjacent regression lanes. Hosted CI status is
recorded on the pull request.

## Live Case Study

[`examples/vsd/public_health_case_study.py`](../../examples/vsd/public_health_case_study.py)
creates one `ToolUniverse` instance, selectively loads six tools, and makes every
call through `run_one_function()` with caching disabled:

1. Offline discovery of reviewed source-specific VSD tool names.
2. A fixed eight-measure CDC PLACES heart-health profile for Autauga County.
3. WHO hypertension indicator metadata through a fixed adapter.
4. One identified public openFDA aspirin label through a UUID adapter.
5. A bounded PubMed scan for tract-level CHD and risk-factor literature.
6. A bounded ClinicalTrials.gov scan for active or upcoming Alabama-matched CHD records.

Run it with:

```bash
python examples/vsd/public_health_case_study.py
```

The machine-readable artifact is
[`examples/vsd/artifacts/snapshot.json`](../../examples/vsd/artifacts/snapshot.json),
the rendered evidence report is
[`examples/vsd/artifacts/snapshot.md`](../../examples/vsd/artifacts/snapshot.md).
Two analyst-ready tables are also checked:
[`examples/vsd/artifacts/tract_profiles.csv`](../../examples/vsd/artifacts/tract_profiles.csv)
contains one row per tract with all estimates, intervals, and flags, while
[`examples/vsd/artifacts/measure_summary.csv`](../../examples/vsd/artifacts/measure_summary.csv)
contains one row per measure with population semantics and descriptive statistics.

The study refuses to produce a report if the CDC result reaches its limit or if
the expected tract-by-measure grid is incomplete. It applies a reproducible rule
that selects, without ranking, tracts whose CHD point estimate is above the county
tract median and that show at least four of seven direction-aware context signals.
A three-through-seven signal sensitivity table exposes dependence on the selected
threshold. A separate strict heuristic requires the CHD interval and at least
three context intervals to be entirely beyond the relevant medians; this is
reported as a sensitivity check, not a statistical-significance test.

The checked JSON retains the exact ToolUniverse call ledger and bounded source
records. VSD provider results include endpoint, query, status, media type,
response size, timestamp, and a raw-response SHA-256 while omitting raw provider
payloads and label warning text. Supporting PubMed and ClinicalTrials.gov tools
are explicitly identified as outside the VSD transport and provenance contract.

The sources are independent and cannot support record-level joins, neighborhood
health rankings, causal claims, treatment-effect claims, or clinical advice.
Live APIs can change, so later runs may legitimately produce different records,
timestamps, hashes, estimates, or label data.

## Remaining Boundaries

- `TOOLUNIVERSE_VSD_ALLOWED_HOSTS` is an administrator trust boundary. Adding a
  host permits unauthenticated bounded GET requests to that exact host; it does
  not certify the host's scientific quality.
- Pinning one vetted address favors destination integrity over automatic
  multi-address failover. A caller can retry after a transient address failure.
- VSD intentionally does not accept credentials. Authenticated sources require a
  dedicated environment-backed tool with source-specific policy.
- A reviewed adapter means the endpoint, input constraints, normalization, and
  technical provenance contract were reviewed. It does not certify upstream
  methodology, accuracy, stability, or fitness for a scientific claim.

## Integration Recommendation

This draft contains PR #413 plus the hardened transport, administration boundary,
source-specific tools, regression suite, and disease-study evidence. The #413
author can take the follow-up commits into their branch or use this combined draft
after review.
