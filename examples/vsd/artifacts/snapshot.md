# Coronary heart disease estimates in Autauga County, Alabama

Generated: `2026-07-31T23:19:43Z`

## Research Question

What variation does CDC PLACES report in modeled adult coronary heart disease prevalence across Autauga County census tracts, and how can related WHO indicator and public aspirin-label context be retrieved without treating the sources as joinable clinical evidence?

## Exactly How ToolUniverse Was Used

The script created one `ToolUniverse` instance, selectively loaded four VSD tools, and executed every step through `run_one_function()` with caching disabled:

```python
tu = ToolUniverse()
tu.load_tools(include_tools=list(TOOL_NAMES), quiet=True)
result = tu.run_one_function(
    {"name": tool_name, "arguments": arguments},
    use_cache=False,
)
```

| # | Tool | Exact arguments | Result proof |
| ---: | --- | --- | --- |
| 1 | `VSDDiscoverSources` | `{"query": ""}` | `{"reviewed_source_count": 4}` |
| 2 | `VSDWHOHypertensionIndicator` | `{}` | `{"indicator_code": "NCD_HYP_DIAGNOSIS_C"}` |
| 3 | `VSDCDCPlacesCoronaryHeartDisease` | `{"county_name": "Autauga", "limit": 500, "state_abbr": "AL"}` | `{"possibly_truncated": false, "tract_count": 17}` |
| 4 | `VSDOpenFDALabelBySetId` | `{"set_id": "0058175f-3474-40c3-a046-6cfaec86d84b"}` | `{"set_id": "0058175f-3474-40c3-a046-6cfaec86d84b"}` |

## Descriptive Result

CDC PLACES returned **17** Autauga County census-tract estimates for 2023. The unweighted tract mean was **6.75%**, the median was **6.8%**, and the observed range was **6.0 percentage points**.

| Bound | Census tract | Estimate | 95% confidence interval |
| --- | --- | ---: | --- |
| Minimum | 01001020804 | 4.0% | 3.6 to 4.5% |
| Maximum | 01001021100 | 10.0% | 9.0 to 11.0% |

Independent context retrieved by the other typed tools:

- WHO indicator `NCD_HYP_DIAGNOSIS_C`: Hypertension: diagnosis coverage among adults aged 30-79 with hypertension, crude (%).
- openFDA label `0058175f-3474-40c3-a046-6cfaec86d84b`: Low Dose Aspirin (ASPIRIN, ORAL); matched warning terms: `blood thinning`, `heart disease`, `high blood pressure`.

## Why VSD Was Useful

- Discovery maps packaged reviewed integrations to concrete ToolUniverse tool names.
- Each source tool fixes the provider endpoint and validates source-specific inputs and outputs.
- The shared transport pins a vetted public address, validates TLS hostname and peer, rejects redirects and encoded bodies, and caps responses at 1 MB.
- Each result carries endpoint, exact query, retrieval time, media type, size, redirect count, and payload hash.
- Mutable registration and generic JSON querying are available only through the explicit administration CLI, not the agent tool surface.

## What This Does Not Prove

- CDC PLACES values are modeled aggregate estimates, not individual observations.
- The descriptive mean is unweighted across retrieved census tracts.
- Differences between tracts do not establish causes or statistical significance.
- WHO metadata, CDC estimates, and the openFDA label are independent and are not joined.
- The aspirin label is safety context, not evidence of treatment efficacy or advice.
- A reviewed VSD adapter establishes a constrained technical contract, not scientific endorsement.

## Provenance

- **CDC PLACES**: `https://chronicdata.cdc.gov/resource/cwsq-ngmh.json`; HTTP 200; 3607 bytes; SHA-256 `2dd9daed8a50f847e4f3fa9cb7e5e2e3b98288328300e52fdade1b7deeeef41f`.
- **openFDA Drug Labels**: `https://api.fda.gov/drug/label.json`; HTTP 200; 8944 bytes; SHA-256 `aa3a391272c7b9be4ef6bd8714395cfbf14cef480fd65a0858f9046cd728ef00`.
- **WHO Global Health Observatory**: `https://ghoapi.azureedge.net/api/Indicator`; HTTP 200; 281 bytes; SHA-256 `49136dfd464ecaad2c2a530d0524316f19a62201e2c35c772da9a959b5e61d3c`.
