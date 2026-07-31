# VSD Hardening and Validation

## Purpose

This change is a focused follow-up to ToolUniverse PR #413. It preserves the
Verified Source Directory workflow while closing the security and state-integrity
gaps found during adversarial review. It also adds a reproducible public-health
case study whose checked artifacts were generated through the real register,
query, and remove tools.

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
| Caching | Catalog mutations and reads inherited cache support. | Register, list, query, and remove are non-cacheable. Discovery remains cacheable because it is packaged and offline. |
| MCP metadata | Register and remove inherited read-only, non-destructive annotations. | Register and remove explicitly advertise `readOnlyHint=false` and `destructiveHint=true`. |
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
contract tests load the actual tool configurations and verify effective caching
and MCP annotations.

Run the focused proof suite from the repository root:

```bash
python -m pytest -o addopts= \
  tests/unit/test_vsd_tools.py \
  tests/unit/test_vsd_transport_security.py \
  tests/unit/test_vsd_catalog_concurrency.py \
  tests/unit/test_vsd_tool_contracts.py \
  tests/unit/test_vsd_public_health_case_study.py -q
```

The final local run passed all 56 focused tests. An additional 60 adjacent tests
covering generated wrappers, package imports, tool configuration validation, and
base-tool capabilities also passed. On Windows, the package-import lane must set
`PYTHONPATH=src` and `PYTHONUTF8=1` so its clean subprocess imports this checkout
and reads the repository's existing Unicode wrapper descriptions as UTF-8.

Ruff passed for every changed Python file, Python byte-compilation completed, all
checked JSON files parsed, and `git diff --check` reported no whitespace errors.

## Live Case Study

[`examples/vsd/public_health_case_study.py`](../../examples/vsd/public_health_case_study.py)
uses the hardened tools to retrieve three bounded public inputs:

1. WHO hypertension indicator metadata.
2. Five aggregate CDC PLACES coronary-heart-disease estimates.
3. One identified public openFDA aspirin label.

Run it with:

```bash
python examples/vsd/public_health_case_study.py
```

The machine-readable artifact is
[`examples/vsd/artifacts/snapshot.json`](../../examples/vsd/artifacts/snapshot.json),
and the rendered evidence report is
[`examples/vsd/artifacts/snapshot.md`](../../examples/vsd/artifacts/snapshot.md).
They retain endpoint, query, status, media type, response size, timestamp, and a
SHA-256 digest of each raw response while omitting the large raw records.

The recorded case-study run completed six hardened HTTPS calls across WHO, CDC,
and openFDA. A separate packaged-source smoke test returned strict JSON from all
four seeded providers (WHO, CDC, openFDA, and Ensembl), with zero redirects and
an exact match between each connected peer and its prevalidated pinned address;
the run exercised both IPv4 and IPv6 destinations.

The sources are independent and cannot support record-level joins, causal claims,
treatment-effect claims, or clinical advice. Live APIs can change, so later runs
may legitimately produce different timestamps, hashes, estimates, or label data.

## Remaining Boundaries

- `TOOLUNIVERSE_VSD_ALLOWED_HOSTS` is an administrator trust boundary. Adding a
  host permits unauthenticated bounded GET requests to that exact host; it does
  not certify the host's scientific quality.
- Pinning one vetted address favors destination integrity over automatic
  multi-address failover. A caller can retry after a transient address failure.
- VSD intentionally does not accept credentials. Authenticated sources require a
  dedicated environment-backed tool with source-specific policy.

## Integration Recommendation

This branch is intentionally stacked on PR #413. The preferred integration is for
the #413 author to merge this follow-up into their existing branch, preserving the
original authorship and discussion while adding the proven fixes and case-study
evidence. If that is inconvenient, this branch can be retargeted to `main` as the
combined replacement after #413's commits and this validation are reviewed
together.
