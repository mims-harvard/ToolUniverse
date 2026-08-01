# VSD Reviewed Tool Promotion

This phase turns one **reviewed** discovery candidate into one or more narrow,
read-only ToolUniverse tools. It does not make discovery results executable and
does not let an agent approve or publish a tool.

## Boundary

The pipeline has four explicit administrator actions:

1. `draft-socrata` generates a bounded GET contract from reviewed candidate fields.
2. `verify` executes the draft through a real `ToolUniverse` instance against 3-20 cases.
3. `approve` records a reviewer and decision against the exact draft and evidence hashes.
4. `publish` atomically writes the approved contract. Loading remains a separate, explicit call.

Draft, evidence, approval, and publication artifacts are SHA-256 linked. A changed
artifact fails closed. Generated filters are mandatory, the record limit is fixed,
credentials are forbidden, provider responses must match the reviewed schema, and
published tools cannot replace a tool already loaded in the process.

The hashes detect accidental or out-of-band modification; they are not digital
signatures. Write access to the promotion workspace is therefore an administrative
trust boundary. Loading validates every publication before registering any of them,
so one malformed record cannot leave a partially loaded set.

Socrata arbitrary-precision `Number` and `Money` fields are modeled as bounded
numeric strings because that is their documented JSON wire representation. Object
fields may be returned, but the generator refuses to expose them as direct equality
filters. Field and tool-name limits also match the dynamic runtime and ToolUniverse's
MCP-compatible name ceiling.

Provider reference: https://dev.socrata.com/docs/datatypes/number.html

This is a technical review boundary. It does not establish that a dataset is
scientifically correct, clinically appropriate, current enough for care, or endorsed
by ToolUniverse.

## Administrator CLI

The CLI accepts either a standalone discovery candidate or the checked discovery
case-study snapshot:

```console
tooluniverse-vsd-promote --workspace .tooluniverse/vsd draft-socrata discovery.json \
  --tool-name CancerTrialsBySite \
  --description "Query the reviewed cancer-trial dataset by exact primary site." \
  --filter-fields primary_site \
  --return-fields protocol,primary_site,study_phase,title \
  --max-records 25

tooluniverse-vsd-promote --workspace .tooluniverse/vsd verify DRAFT_ID cases.json
tooluniverse-vsd-promote --workspace .tooluniverse/vsd approve DRAFT_ID \
  --reviewed-by REVIEWER \
  --decision-note "Technical approval after contract review and live verification."
tooluniverse-vsd-promote --workspace .tooluniverse/vsd publish DRAFT_ID
tooluniverse-vsd-promote --workspace .tooluniverse/vsd list
```

Applications opt in to published records explicitly:

```python
from tooluniverse import ToolUniverse
from tooluniverse.vsd_promotion import load_published_tools

tu = ToolUniverse()
loaded_names = load_published_tools(tu, workspace=".tooluniverse/vsd")
```

There is no startup scan, background publication, or agent-facing approval action.

## End-to-End Cancer-Trial Case

The checked case starts with the candidate selected by the preceding Socrata catalog
study: New York State dataset `2ig8-yxf8`, "Current Active Clinical Trials - Roswell
Park Cancer Institute." It deliberately creates **two tools from one source**:

- `VSDGeneratedCancerTrialsBySite`, requiring an exact `primary_site`.
- `VSDGeneratedCancerTrialsByPhase`, requiring an exact `study_phase`.

The site tool verifies Brain and Nervous System, Breast, and Prostate. The phase tool
verifies phases I, II, and III. After publication, a fresh ToolUniverse instance loads
both records and repeats independent Breast and phase III queries.

Run it from the repository root:

```console
PYTHONPATH=src python examples/vsd/tool_promotion_cancer_case_study.py
```

Review the concise report at
`examples/vsd/artifacts/tool_promotion_snapshot.md`, the machine-readable summary at
`examples/vsd/artifacts/tool_promotion_snapshot.json`, and the complete audit chain
under `examples/vsd/artifacts/promotion_workspace/`.

## Verification Commands

```console
PYTHONPATH=src python -m pytest \
  tests/unit/test_vsd_promotion.py \
  tests/unit/test_vsd_promotion_cli.py -q

uvx --from ruff==0.14.5 ruff check \
  src/tooluniverse/vsd_promotion.py \
  src/tooluniverse/vsd_promotion_cli.py \
  tests/unit/test_vsd_promotion.py \
  tests/unit/test_vsd_promotion_cli.py \
  examples/vsd/tool_promotion_cancer_case_study.py
```
