# Verified Source Directory Public-Health Case Study

This example uses the VSD register, query, and remove workflow to build a small
cardiovascular public-health snapshot from three independent public sources:

- WHO Global Health Observatory indicator metadata
- CDC PLACES aggregate census-tract estimates
- one identified public openFDA aspirin label

The point is provenance and safe retrieval, not data integration. The sources
have different populations, semantics, and update schedules. The output must not
be interpreted as evidence that aspirin changes the CDC or WHO measures.

## Run

From the repository root:

```bash
python examples/vsd/public_health_case_study.py
```

The command makes six small HTTPS GET requests: registration probes and bounded
queries for three exact allowlisted hosts. It uses a temporary VSD catalog and
removes every registration. No credentials are accepted or required.

To keep generated files outside the checkout:

```bash
python examples/vsd/public_health_case_study.py \
  --json /tmp/vsd-snapshot.json \
  --markdown /tmp/vsd-snapshot.md
```

## Security Model

The example inherits VSD policy enforcement: HTTPS on port 443, exact-host
allowlisting, DNS resolution pinned to one vetted public address, TLS hostname
verification, redirect rejection, environment-proxy disabling, strict JSON media
types, identity encoding only, a 1 MB body limit, credential-like input rejection,
and a total wall-clock deadline. Queries select at most one WHO row, five CDC
aggregate rows, and one openFDA label.

Raw responses are never written. The JSON artifact retains a SHA-256 digest of
each canonical raw payload, exact endpoint and query parameters, HTTP status,
content type, response size, and redirect count. This is enough to identify the
retrieval without publishing large upstream records. The selected CDC fields are
aggregate estimates; the selected FDA fields describe a public product label.

## Artifacts

- `artifacts/snapshot.json` is the machine-readable record.
- `artifacts/snapshot.md` is the human-readable rendering.

Live APIs change, so a later run may produce a different timestamp, response
hash, estimate, or label metadata. Given the same source payloads and timestamp,
the transformation, ordering, JSON serialization, and Markdown rendering are
deterministic. Offline unit tests use fixed payloads and do not contact the
network.

## Interpretation

The WHO row identifies the selected hypertension-diagnosis-coverage indicator.
The CDC rows are model-based local prevalence estimates with confidence limits.
The FDA row demonstrates that public labeling can be retrieved and reduced to
non-clinical metadata and explicitly matched warning phrases. None of these
observations supports patient-level inference, causal comparison, or treatment
advice. Follow the upstream licenses, terms, and clinical disclaimers.
