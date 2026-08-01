# ToolUniverse VSD Validation Case Studies

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
inspection rather than reuse the example value above. Authentication, write
methods, external schema references, non-JSON responses, unsupported parameter
styles, and oversized schemas are emitted with explicit blockers and cannot be
drafted.

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
