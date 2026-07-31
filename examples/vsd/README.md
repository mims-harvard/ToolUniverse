# ToolUniverse VSD Coronary-Heart-Disease Study

This example asks a bounded descriptive question: what variation does CDC
PLACES report in modeled adult coronary-heart-disease prevalence across Autauga
County, Alabama census tracts? It retrieves WHO hypertension-indicator metadata
and one public aspirin label as independent context, without joining those
sources or turning them into treatment evidence.

## How ToolUniverse Is Used

The script follows the documented Python execution model:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(include_tools=list(TOOL_NAMES), quiet=True)
result = tu.run_one_function(
    {"name": tool_name, "arguments": arguments},
    use_cache=False,
)
```

It loads and calls exactly four agent-facing tools:

1. `VSDDiscoverSources` identifies packaged reviewed integrations and their
   concrete ToolUniverse tool names without a network request.
2. `VSDWHOHypertensionIndicator` calls a fixed WHO endpoint and returns one
   validated indicator definition.
3. `VSDCDCPlacesCoronaryHeartDisease` accepts only a state, county, and bounded
   limit, then returns normalized tract-level CHD estimates from a fixed CDC
   endpoint.
4. `VSDOpenFDALabelBySetId` accepts a UUID and returns a normalized label from a
   fixed openFDA endpoint.

The checked JSON artifact records every `run_one_function` call, exact arguments,
status, normalized output keys, and a bounded result summary such as returned
tract count and whether the limit may have truncated the response. Mutable source
registration and generic JSON querying are not loaded into ToolUniverse; they are
available only through the explicit `tooluniverse-vsd-admin` command for
human-controlled administration.

## Run

From the repository root:

```bash
python examples/vsd/public_health_case_study.py
```

The run performs one offline discovery and three bounded HTTPS requests. It
retrieves all matching Autauga County census tracts up to a hard maximum of 500,
computes an unweighted descriptive mean, median, minimum, maximum, and observed
range, and writes:

- `artifacts/snapshot.json`: machine-readable calls, findings, and provenance.
- `artifacts/snapshot.md`: human-readable method, findings, VSD contribution,
  and interpretation limits.

## Why VSD Helps

The value is not merely fetching JSON. Each reviewed source has a fixed endpoint,
constrained parameters, a concrete return schema, source-specific response
validation, and common provenance. The transport resolves and pins one vetted
public address, preserves TLS hostname validation, verifies the connected peer,
rejects redirects and encoded bodies, requires strict JSON, caps the raw body at
1 MB, and applies one wall-clock deadline.

This turns a broad network capability into three inspectable scientific data
contracts. A source adapter being reviewed means its technical integration and
schema handling were reviewed; it does not certify the provider's methodology or
scientific conclusions.

## Evidence Boundaries

CDC explains that PLACES estimates use small-area estimation and are derived from
BRFSS, Census, and American Community Survey inputs. The values are modeled
aggregate estimates, not patient records. The tract mean in this example is
unweighted and is only a compact description of the retrieved rows.

The WHO result is indicator metadata, not an Autauga County measurement. The
openFDA result is public labeling and warning context, not evidence that aspirin
causes, prevents, or treats the CDC estimates. The three sources are independent
and must not be joined at record level or used for clinical advice.

Official references:

- ToolUniverse Python guide: https://zitniklab.hms.harvard.edu/ToolUniverse/getting_started.html
- ToolUniverse loading guide: https://zitniklab.hms.harvard.edu/ToolUniverse/guide/loading_tools.html
- CDC PLACES methodology: https://www.cdc.gov/places/methodology/index.html
- CDC PLACES data portal: https://www.cdc.gov/places/tools/data-portal.html
- openFDA label API: https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/
- WHO cardiovascular diseases: https://www.who.int/news-room/fact-sheets/detail/cardiovascular-diseases-(cvds)
