# ToolUniverse VSD Validation Case Studies

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
