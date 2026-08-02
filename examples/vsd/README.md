# ToolUniverse VSD Validation Case Studies

## Cross-Format Source-To-Runtime Total Proof

`cross_format_total_proof.py` connects the complete VSD stack in one ALS/DANDI
growth loop. It audits the real ToolUniverse registry and the 50-source review
catalog, separates an existing NIH RePORTER host from a DANDI capability gap,
runs the bounded two-host scan twice, snapshots and inspects seven contract
formats, and selects six DANDI operations while leaving the duplicate OpenAPI
source unpromoted.

Each selected operation is bound to its exact provider and format-specific
identity before a draft can exist: GraphQL root field and arguments, Postman
method and explicit template-variable map, WSDL endpoint/SOAPAction/body
operation, protobuf authority/RPC/messages/streaming/descriptor, MCP declared
tool, or AsyncAPI source endpoint/channel/payload schema. The portfolio then
runs three representative cases per format, approves and publishes all six,
loads them into a fresh ToolUniverse instance, and executes one final ALS
request through every format. Eight cross-provider or cross-operation
substitution attempts must fail before draft creation.

The professional report also indexes sixteen concrete studies across PRs
#416-#431, including registry reuse, dynamic REST, discovery, promotion, Docker,
OpenAPI, workflow planning, private demand, credentials, lifecycle drift,
multi-format contracts, reviewed runtime, and source intelligence. Run it from
the repository root:

```console
PYTHONPATH=src python examples/vsd/cross_format_total_proof.py
```

Review `artifacts/cross_format_total_proof.md` and its machine-verifiable JSON
counterpart. The checked proof contains 21 end-to-end assertions, 18 promotion
verification executions, six final executions, and eight fail-closed
substitution cases.

## Trusted-Source Intelligence And Review Handoff

`source_intelligence_case_study.py` asks whether ToolUniverse can identify the
interfaces needed to connect ALS grant evidence with reusable neurophysiology
datasets without duplicating configured sources or silently installing
discovered operations. It first audits the real built-in configuration
inventory, then runs eleven focused cases covering the 50-source review
catalog, exact-host duplicate detection, genuine gap detection, bounded
multi-host crawling, robots and host boundaries, seven contract formats,
content-addressed snapshots, local contract inspection, cron history, private
demand linkage, and explicit core-team handoff.

The 50 sources are not an allowlist for execution. A catalog entry permits only
bounded candidate discovery. Every discovered document remains inert and must
be explicitly snapshotted, inspected, reduced to an exact operation, verified
against representative cases, approved, published, and loaded through the
existing VSD lifecycle. Source scans and unmet-demand records remain local by
default; the core team sees a sanitized subset only when an administrator
selects candidate IDs, supplies review text, gives consent, and separately
confirms issue submission.

Run the deterministic offline portfolio from the repository root:

```console
PYTHONPATH=src python examples/vsd/source_intelligence_case_study.py
```

Review `artifacts/source_intelligence_snapshot.md`, its machine-verifiable JSON
counterpart, the sanitized demand proposal, and the local handoff preview. The
portfolio checks 28 end-to-end properties and renders an issue without
submitting it.

The administrator CLI supports the same lifecycle:

```console
tooluniverse-vsd-sources coverage
tooluniverse-vsd-sources scan --seed https://api.example.org/developer \
  --report-directory ./private-vsd-source-history
tooluniverse-vsd-sources snapshot scan.json <candidate-id> ./private-snapshots \
  --manifest-file snapshot-manifest.json
tooluniverse-vsd-sources handoff handoff.json scan.json \
  --candidate-id <candidate-id> --snapshot snapshot-manifest.json \
  --reviewed-by "Local Maintainer" \
  --decision-note "Reviewed source ownership, coverage, contract, and terms." \
  --consent
tooluniverse-vsd-sources render handoff.json
```

`submit handoff.json --confirm` is the only command that transmits anything. It
uses the fixed `mims-harvard/ToolUniverse` issue endpoint and reads the token
only from `TOOLUNIVERSE_VSD_GITHUB_TOKEN`.

## Reviewed Multi-protocol Runtime Portfolio

`reviewed_runtime_case_study.py` asks whether one spinal muscular atrophy study
can combine heterogeneous reviewed providers after contract inspection. Ten
focused runtime cases cover an OAuth-protected GraphQL registry, paginated CSV
natural-history data, a SOAP molecular panel, an HTML trial table, a binary
evidence report, bounded server-sent safety events, in-memory multipart cohort
analysis, gRPC variant evidence, a fixed MCP literature tool, and a signed
webhook event. An eleventh case binds a WSDL candidate to a reviewed SOAP
configuration and completes draft, three-case verification, approval,
publication, fresh ToolUniverse loading, and a new execution.

The runtime does not turn arbitrary POST operations into tools. POST is allowed
only when an administrator records it as a read-only query, GraphQL accepts one
query operation and rejects mutations/subscriptions, multipart accepts bounded
base64 bytes rather than filesystem paths, pagination is page/item/byte bounded,
and event validation opens no listener. OAuth client credentials and HMAC
secrets come from narrowly named environment variables and are excluded from
results and artifacts.

Run the deterministic offline portfolio from the repository root:

```console
PYTHONPATH=src python examples/vsd/reviewed_runtime_case_study.py
```

Review `artifacts/reviewed_runtime_snapshot.md` and the machine-verifiable JSON
counterpart. The portfolio checks 33 properties across the ten runtime cases
and the complete promotion proof.

## Multi-format Contract Inspection Portfolio

`multiformat_contract_case_study.py` asks whether an SMA evidence workflow can
inventory providers whose contracts are expressed as GraphQL SDL, AsyncAPI 3,
a Postman collection, WSDL/SOAP, gRPC/protobuf, and an MCP manifest. Its six
focused cases cover a rare-disease registry, post-market safety alerts, natural
history motor scores, a molecular diagnostics laboratory, variant evidence,
and literature synthesis. The proof produces ten content-addressed operation
candidates and checks 27 properties without making a provider request.

The result is deliberately not ten new tools. It is a reviewable inventory:
GraphQL and Postman reads can be distinguished from mutations and writes;
event transports remain closed; SOAP and gRPC operations require a reviewed
runtime; and a local-command MCP server is identified and blocked. Every
candidate remains inert, retains the exact local source hash, and states the
specific work still required before execution can be considered.

Run the deterministic offline portfolio from the repository root:

```console
PYTHONPATH=src python examples/vsd/multiformat_contract_case_study.py
```

Review `artifacts/multiformat_contract_snapshot.md` and its machine-verifiable
JSON counterpart. The administrator CLI can inspect the same formats with
`tooluniverse-vsd-contracts CONTRACT [--format FORMAT] [--endpoint HTTPS_URL]`.

## Total Demand-To-Reviewed-Tool System Proof

`total_system_case_study.py` answers one complete operational question: can a
repeatedly missing capability in a real workflow become a reviewed ToolUniverse
tool, be reused safely, and remain governed when its provider changes? The case
starts with an ALS evidence workflow that needs one protected rare-disease
registry operation returning genes, phenotypes, and clinical-trial identifiers.
The initial registry cannot satisfy that step.

Three independent workflow preflights record the same missing capability in the
private demand ledger. An administrator selects one sanitized proposal, reviews
a source through the mutable source CLI, searches the fixed public API catalog,
and inspects the protected provider's local OpenAPI contract. Both discovered
candidates remain inert. The reviewed OpenAPI candidate becomes a draft with an
environment-backed header credential reference, passes exact ALS, Duchenne
muscular dystrophy, and spinal muscular atrophy verification cases, receives an
explicit approval, and is published with a lifecycle anchor.

A fresh ToolUniverse instance cannot see the tool until it explicitly loads the
publication. After loading, capability resolution, workflow replanning, and
Tool Finder agree that the original gap now has exact coverage. The runtime
executes two disease records across credential rotation without changing the
reviewed operation identity. The demand ledger records that exact coverage and
is then explicitly cleared by its local administrator.

Finally, the case classifies a provider endpoint move as breaking, explicitly
suspends the publication, and proves a fresh runtime cannot load it. An
unchanged assessment of the repaired reviewed contract permits explicit
reactivation, after which a fresh runtime executes the third disease record.
The checked report contains 26 end-to-end assertions and SHA-256 identities for
the proposal, draft, operation, verification, approval, publication, lifecycle
events, and complete case audit.

Run the deterministic offline proof from the repository root:

```console
PYTHONPATH=src python examples/vsd/total_system_case_study.py
```

Review the human-readable
`artifacts/total_system_snapshot.md`, the machine-verifiable
`artifacts/total_system_snapshot.json`, and the sanitized
`artifacts/total_system_demand_proposal.json`. The protected provider and fixed
catalog responses are deterministic because the repository cannot bundle a
live credential; all registry, planning, demand, administration, inspection,
promotion, runtime, credential, lifecycle, and audit logic uses production
code. Docker provisioning remains the independent administrator-only boundary
reviewed in [#420](https://github.com/mims-harvard/ToolUniverse/pull/420).

## Provider Drift And Publication Lifecycle

Published VSD tools retain the exact provider contract that was reviewed, but
provider OpenAPI documents can change later. The administrator-only
`tooluniverse-vsd-lifecycle` CLI compares a local current OpenAPI file with the
published operation and persists an inert, content-addressed assessment:

- `unchanged` means the source document and inspected operation are identical.
- `metadata_only` means documentation changed without changing request or
  response validation behavior.
- `review_required` means an input or response schema changed and a new draft,
  verification run, and approval are required.
- `breaking` means the operation disappeared, became policy-blocked, cannot be
  reconstructed, or changed its endpoint, authentication, fixed query, or
  argument mapping.

`review_required` and `breaking` assessments recommend suspension, but an
assessment cannot change state. An administrator must explicitly append a
`suspended`, `active`, or `retired` event. Events are immutable, contiguous,
hash-chained, bound to one exact publication digest, and can reference one
validated assessment. Reactivation requires an `unchanged` or `metadata_only`
assessment for that publication. Retirement is terminal for that publication.
A newly reviewed replacement has a new publication digest and begins active.

The publication loader validates the complete applicable history before it
registers any tool. Suspended and retired publications are excluded from fresh
ToolUniverse instances. A missing, modified, noncontiguous, or invalid event or
referenced assessment fails the load before registration. Lifecycle changes do
not remove a tool from an already-running instance; its host must restart or
otherwise unload that instance.

The checked protected rare-disease study promotes one authenticated operation,
classifies unchanged, metadata-only, response-schema, endpoint, and unsafe-auth
contracts, explicitly suspends the publication, proves fresh loading is empty,
and proves a modified event fails closed. It then reassesses the repaired
contract, explicitly activates it, executes two records across credential
rotation, retires it, and proves both exclusion and terminal state. All six
assessments remain inert, all three state events form one hash chain, and no
credential value appears in an artifact or ToolUniverse result.

Run the deterministic offline study from the repository root:

```console
PYTHONPATH=src python examples/vsd/lifecycle_drift_case_study.py
```

The study writes `artifacts/lifecycle_drift_snapshot.md` and its JSON audit
snapshot. Its protected provider is deterministic because the repository
cannot bundle a live credential; only network transport is replaced.

A cron or release job can download a provider contract to a local file and run
assessment separately from state decisions:

```console
tooluniverse-vsd-lifecycle --workspace ./vsd-review assess-openapi \
  VSDProtectedEvidenceById current-provider-openapi.yaml
tooluniverse-vsd-lifecycle --workspace ./vsd-review status \
  VSDProtectedEvidenceById
tooluniverse-vsd-lifecycle --workspace ./vsd-review suspend \
  VSDProtectedEvidenceById --changed-by "Local Maintainer" \
  --reason "Suspended while the changed provider contract is reviewed." \
  --assessment-sha256 <assessment-sha256>
```

The CLI does not fetch contracts, make provider requests, change state based on
an assessment, create a replacement draft, approve, publish, or transmit
evidence. Those boundaries remain deliberate administrator actions.

## Environment-Backed Credentials For Reviewed APIs

VSD can promote a reviewed OpenAPI operation that requires either one header
API key or one HTTP bearer token. The inspector derives the authentication
contract from the OpenAPI security scheme, while the administrator supplies a
`TOOLUNIVERSE_VSD_*` environment-variable reference during drafting. Only the
reference is persisted; the credential value is read separately for every
execution and is excluded from the operation result and provenance.

Query and cookie API keys, HTTP basic authentication, OAuth flows, scopes,
multiple simultaneous schemes, and ambiguous security alternatives remain
blocked. Header names and values are bounded and validated before transport.
Missing or malformed credentials fail before a request, and a provider payload
that contains the exact credential value is rejected before result
construction. Because the environment value is not part of the reviewed
operation digest, an operator can rotate it without republishing the tool.

The checked rare-disease study inspects a protected OpenAPI 3.1 contract,
creates an inert candidate, binds the reviewed `X-Rare-Disease-Key` header to an
environment reference, verifies ALS, Duchenne muscular dystrophy, and spinal
muscular atrophy records, approves and publishes the hash-bound operation, and
loads it into a fresh ToolUniverse instance. It then proves credential rotation,
pre-network failure, provider-reflection rejection, and absence of all test
credential values from persisted JSON and ToolUniverse results.

Run the deterministic offline study from the repository root:

```console
PYTHONPATH=src python examples/vsd/credential_reference_case_study.py
```

The study writes `artifacts/credential_reference_snapshot.md` and the
corresponding JSON audit snapshot. A deterministic protected rare-disease
provider replaces only network transport because the repository cannot bundle
a live credential; OpenAPI inspection, promotion, verification, publication,
fresh loading, and execution all use the production code paths.

For a real reviewed contract, use the same administrator flow:

```console
tooluniverse-vsd-promote inspect-openapi protected-api.yaml > inspection.json
tooluniverse-vsd-promote --workspace ./vsd-review draft-openapi inspection.json \
  --candidate-id <candidate-id> \
  --tool-name VSDProtectedEvidenceById \
  --description "Retrieve one reviewed protected evidence record by identifier." \
  --credential-env TOOLUNIVERSE_VSD_PROVIDER_KEY
```

Configure `TOOLUNIVERSE_VSD_PROVIDER_KEY` in the runtime's secret manager or
process environment before verification and execution. Do not put a credential
value in the inspection file, command line, tool configuration, or case
artifact.

## Private Capability-Demand Ledger

`demand_ledger_case_study.py` demonstrates how a library user can learn which
capabilities recur without silently sending searches to the ToolUniverse team.
The administrator-only `tooluniverse-vsd-demand` CLI resolves current registry
coverage, records an explicit local observation, ranks repeated missing and
partial coverage, and writes only explicitly selected proposals to a sanitized
file. It is not registered as an agent-facing tool.

The private ledger never stores the raw capability description or caller event
ID. Each observation requires a separate 10-240 character public summary; URLs,
email addresses, and credential-like assignments are rejected. The ledger is
bounded, requests restrictive filesystem modes, uses atomic replacement, locks
across threads and processes, and carries a content digest. Replayed event IDs
are represented only by hashes and do not increase counts.

Workflow plans can be recorded as one transaction with
`record_plan_demands()`. The function verifies the complete plan SHA-256 and its
non-execution boundary before it validates every selected step and public
summary. A missing summary or altered plan aborts the entire batch without
writing a partial ledger.

The checked ALS study records three hash-bound seven-step workflow preflights, then
replays one run to prove deduplication. It adds two observations for a distinct
adaptive-optics retinal calibration gap and one exact FDA-label observation.
The resulting unmet ranking contains six entries: the repeated ALS calibration
gap scores 15, retinal calibration scores 10, and four partially covered ALS
retrieval capabilities score 6 each. The satisfied FDA capability remains
local but does not enter the ranking or export.

Run the offline study from the repository root:

```console
PYTHONPATH=src python examples/vsd/demand_ledger_case_study.py
```

The study writes `artifacts/demand_ledger_snapshot.md`, the corresponding JSON
audit snapshot, and `artifacts/demand_proposals.json`. The proposal file contains
only the two reviewer-selected unmet capabilities and explicitly records that
no transmission occurred. Its reduced public capability schema includes the
provider identity, method, operation ID, and field names, but omits endpoint
paths so tenant or record identifiers cannot cross the export boundary.

A direct CLI lifecycle is:

```console
tooluniverse-vsd-demand --workspace ./private-vsd-demand record \
  --description "calibrate adaptive optics retinal imaging phantoms" \
  --public-summary "Adaptive-optics retinal calibration for research workflows" \
  --source scheduled_scan --event-id scan-2026-08-01
tooluniverse-vsd-demand --workspace ./private-vsd-demand rank
tooluniverse-vsd-demand --workspace ./private-vsd-demand export proposals.json \
  --demand-id 0123456789abcdef --reviewed-by "Local Maintainer" \
  --decision-note "Selected after reviewing repeated unmet local demand."
```

The user must deliberately share the resulting proposal file through a normal
issue or pull-request process if the core team should see it. There is no
telemetry, upload endpoint, background reporting, candidate execution, tool
registration, or approval bypass.

## Registry-First ALS Workflow Planning

`workflow_planning_case_study.py` tests whether an agent can preflight a
multi-step ALS research workflow before it searches for another API. It asks
for genes, phenotypes, literature, trials, an FDA label, quantitative
microscopy calibration, and a final synthesis, with explicit dependencies
between the steps.

The planner reads one local registry snapshot without loading or executing the
registered tools. It preserves dependency order, classifies each step as exact,
partial, or missing coverage, routes known tools to full specification review,
and routes only the intentionally absent microscopy capability to bounded API
discovery. The final synthesis is explicitly agent-fulfilled, so it remains in
the dependency graph but can never be mistaken for an API gap. A separate
whole-goal check proves that the existing
`ComprehensiveDrugDiscoveryPipeline` is selected only when every named workflow
dependency is present in the registry.

The same run calls `Tool_Finder_Keyword` with optional VSD enrichment and proves
that Finder and the workflow planner used the same registry digest. The default
Finder response remains unchanged when enrichment is not requested.

Run the offline study from the repository root:

```console
PYTHONPATH=src python examples/vsd/workflow_planning_case_study.py
```

The run writes `artifacts/workflow_planning_snapshot.md` and
`artifacts/workflow_planning_snapshot.json`. Both capture the ordered decisions,
candidate matches, dependency blockers, non-executable handoffs, twelve runtime
assertions, and a SHA-256 audit digest. The study does not call scientific APIs,
execute selected tools, create candidates, persist demand, or publish tools.

## OpenAPI-to-Tool ALS Registry Pipeline

`openapi_als_case_study.py` demonstrates how an administrator can turn one
operation from a provider's official OpenAPI document into a narrow, reviewed
ToolUniverse tool. The inspector reads only a local JSON or YAML file; it does
not fetch the contract, execute candidates, register tools, or make candidates
available to an agent.

The live study uses the current ClinicalTrials.gov OpenAPI 3.0 contract. It
inspects all nine operations, selects `fetchStudy`, exposes only the required
`nctId` path argument, fixes the provider format to JSON, and preserves the
provider's complete response schema. The candidate remains inert until the
existing promotion pipeline verifies three distinct ALS records, records an
explicit approval, publishes the exact hash chain, and loads it into a fresh
ToolUniverse instance.

Download the official contract and run the study from the repository root:

```console
curl -fsS https://clinicaltrials.gov/api/oas/v2 -o ctg-oas-v2.yaml
PYTHONPATH=src python examples/vsd/openapi_als_case_study.py --spec ctg-oas-v2.yaml
```

The checked run retrieved `NCT03019419`, `NCT04428775`, and `NCT04745299`.
Each verification required nested title, status, condition, and identifier
fields and asserted that the returned NCT identifier exactly matched the
request. It also proved that malformed identifiers are rejected by the reviewed
input schema before transport and that every live response used HTTPS, returned
HTTP 200, and followed zero redirects.

Review `artifacts/openapi_als_snapshot.md` for the readable report,
`artifacts/openapi_als_snapshot.json` for the machine-readable audit ledger, and
`artifacts/openapi_ingestion_workspace/` for the draft, verification, approval,
and publication records. The checked audit links the official document hash to
the candidate, generated operation, verification evidence, approval, and
publication.

For administrator scripting, the same two entry points are available through
the promotion CLI:

```console
tooluniverse-vsd-promote inspect-openapi ctg-oas-v2.yaml > inspection.json
tooluniverse-vsd-promote --workspace ./vsd-review draft-openapi inspection.json \
  --candidate-id 47a4c7402dfb7b86 \
  --tool-name VSDClinicalTrialsStudyByNCT \
  --description "Fetch one reviewed ClinicalTrials.gov record by NCT identifier." \
  --fixed-query-file fixed-query.json
```

`candidate-id` values are content-addressed and change when the provider
contract changes. Administrators must select the value produced by their own
inspection rather than reuse the example value above. Authentication schemes
outside the supported header API-key and bearer-token subset, write methods,
external schema references, non-JSON responses, unsupported parameter styles,
and oversized schemas are emitted with explicit blockers and cannot be drafted.

## Complete Oncology Source-Governance Pipeline

`complete_pipeline_case_study.py` exercises the entire VSD stack in one
continuous workflow. It starts with a breast-cancer evidence need and crosses
each trust boundary explicitly:

1. The administrator CLI registers, probes, lists, queries, and removes a
   temporary openFDA tamoxifen source in an isolated catalog.
2. A real ToolUniverse instance confirms that the administrative operations are
   absent, discovers the packaged openFDA integration offline, and retrieves the
   same label through the fixed `VSDOpenFDALabelBySetId` contract.
3. Two reviewed dynamic REST operations search active or upcoming New York
   breast-cancer studies and retrieve one deterministic NCT record.
4. `VSDDiscoverAPICandidates` searches the fixed Socrata catalog for a source
   with six demanded trial fields. The selected candidate remains explicitly
   non-executable.
5. The administrator creates two narrow drafts from that candidate, runs three
   live cases per draft, approves the exact evidence hashes, and publishes the
   approved records.
6. A fresh ToolUniverse instance proves the new tools were absent before the
   explicit load, loads both publications, and executes independent site and
   phase queries.

The first live attempt was rejected because twenty unprojected ClinicalTrials.gov
records exceeded the transport's 1 MB response ceiling. The reviewed search
contract was corrected to request only the ten fields used by the study; the
successful response retained twenty records while shrinking to roughly 372 KB.
The safety limit was not weakened.

Run the complete case from the repository root:

```console
PYTHONPATH=src python examples/vsd/complete_pipeline_case_study.py
```

The checked live run passed all 12 end-to-end assertions, six promotion cases,
two post-publication executions, catalog cleanup, search/detail identity, and
the final cross-stage audit digest. Review the detailed report at
`artifacts/complete_pipeline_snapshot.md`, the complete machine-readable ledger
at `artifacts/complete_pipeline_snapshot.json`, and the draft/evidence/approval/
publication records under `artifacts/complete_pipeline_workspace/promotion/`.

The report is a software-governance and public-record retrieval proof. It does
not match patients, establish trial eligibility, compare treatments, or join
the state and national registries at record level.

## Heart-Health Evidence Dossier

This example builds a reproducible population-health screening dossier for
Autauga County, Alabama. It asks which census tracts show concurrent modeled
coronary heart disease (CHD) and heart-health context signals that merit local
data review, then uses ToolUniverse to retrieve candidate literature, active or
upcoming Alabama-matched trial records, global indicator metadata, and a public
drug-label safety record.

The output is designed for an analyst deciding what to investigate next. It is
not a neighborhood ranking, patient-risk model, causal analysis, clinical
recommendation, or resource-allocation algorithm.

### Workflow

The script creates one `ToolUniverse` instance, selectively loads six tools, and
executes all work through the documented `run_one_function()` API with caching
disabled:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(include_tools=list(TOOL_NAMES), quiet=True)
result = tu.run_one_function(
    {"name": tool_name, "arguments": arguments},
    use_cache=False,
)
```

| Step | Tool | Purpose |
| ---: | --- | --- |
| 1 | `VSDDiscoverSources` | Resolve reviewed VSD integrations to concrete tool names without a network call. |
| 2 | `VSDCDCPlacesHeartHealthProfile` | Retrieve a fixed eight-measure, tract-level heart-health profile for one county. |
| 3 | `VSDWHOHypertensionIndicator` | Retrieve one validated WHO hypertension-indicator definition. |
| 4 | `VSDOpenFDALabelBySetId` | Retrieve one normalized public label and bounded warning terms. |
| 5 | `PubMed_search_articles` | Discover up to eight tract-level CHD articles with a recorded query. |
| 6 | `ClinicalTrials_search_studies` | Discover up to ten active or upcoming CHD records matching an Alabama location-area query. |

The CDC tool does not accept an arbitrary measure. Its reviewed contract always
requests CHD, high blood pressure, high cholesterol, smoking, physical
inactivity, obesity, lack of insurance, and routine checkups. It validates the
measure IDs and names, county, unique tract-measure pairs, percentage bounds,
and confidence-interval ordering before returning data.

### Analysis

The live Autauga query is expected to form a complete 17-tract by 8-measure grid.
The script refuses to build a dossier if the response reaches its record limit or
any tract lacks a measure.

For each measure, it reports the unweighted tract mean, median, interquartile
range, minimum, maximum, observed range, and 95% confidence intervals at the
extremes. It then applies one reproducible, direction-aware screening rule:

> Include a tract when its CHD point estimate is above the county tract median
> and at least four of seven context measures are on the attention side of their
> respective county tract medians.

For adverse measures, higher values trigger a point signal. For routine
checkups, lower values trigger a point signal. A separate conservative count
requires the entire reported confidence interval to be beyond the median. The
resulting set is shown in census-tract order and is explicitly not ranked.

Because the four-of-seven threshold is a modeling choice, the report includes a
three-through-seven signal sensitivity table. It also reports a stricter
heuristic that requires the CHD confidence interval and at least three context
confidence intervals to be entirely beyond their respective tract medians. That
heuristic is not a statistical-significance test.

The report also calculates descriptive Pearson correlations between tract CHD
point estimates and each context measure. These are diagnostics only: they do
not use confidence intervals or adjust for shared model inputs, demographics, or
spatial dependence.

### Run And Artifacts

From the repository root:

```bash
python examples/vsd/public_health_case_study.py
```

The live run performs one offline discovery plus bounded provider calls and
writes four synchronized artifacts:

- `artifacts/snapshot.json`: machine-readable calls, normalized inputs,
  findings, source records, and VSD provenance.
- `artifacts/snapshot.md`: a decision-oriented report with methods, result
  tables, evidence candidates, guardrails, and exact calls.
- `artifacts/tract_profiles.csv`: one row per tract with every estimate,
  confidence interval, and screening flag.
- `artifacts/measure_summary.csv`: one row per measure with descriptive
  statistics and population semantics.

Raw openFDA warning text is intentionally omitted from the checked outputs. VSD
results retain the exact endpoint and query, retrieval time, media type, response
size, redirect count, and raw-payload SHA-256. PubMed and ClinicalTrials.gov are
supporting ToolUniverse integrations and do not inherit the VSD transport or
provenance contract.

### Scientific Boundaries

CDC PLACES estimates are modeled aggregates derived from BRFSS and Census inputs,
not patient observations. CDC cautions against using the estimates to rank the
overall health of counties, places, census tracts, or ZCTAs. This example uses a
transparent screening rule only to form follow-up questions; local counts,
population denominators, stakeholder knowledge, and other data are required
before a decision.

The measures do not all share a denominator. Insurance covers adults aged 18-64,
and high cholesterol covers adults who have ever been screened. The WHO result
is metadata, the trial output is a registry scan, and the openFDA output is label
safety context. None is joined to the CDC records or used as evidence that an
intervention is effective, safe for a person, locally available, or appropriate.

Official references:

- ToolUniverse Python guide: https://zitniklab.hms.harvard.edu/ToolUniverse/getting_started.html
- ToolUniverse loading guide: https://zitniklab.hms.harvard.edu/ToolUniverse/guide/loading_tools.html
- CDC PLACES methodology: https://www.cdc.gov/places/methodology/index.html
- CDC PLACES measure definitions: https://www.cdc.gov/places/measure-definitions/index.html
- CDC PLACES FAQ: https://www.cdc.gov/places/faqs/index.html
- ClinicalTrials.gov API: https://clinicaltrials.gov/data-about-studies/learn-about-api
- openFDA label API: https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/
