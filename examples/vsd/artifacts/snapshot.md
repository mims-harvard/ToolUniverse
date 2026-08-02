# Autauga County coronary heart disease prevention evidence dossier

**Generated:** `2026-08-01T00:11:13Z`

**Status:** Reproducible population-health screening dossier for human review

> This report identifies follow-up questions. It does not rank neighborhoods,
> estimate individual risk, recommend treatment, or allocate resources.

## Executive Brief

ToolUniverse retrieved **136** validated CDC estimates covering **8 measures** across **17 census tracts**. The unweighted tract CHD mean was **6.75%** and the observed range was **4.0%-10.0%**.

The reproducible screening rule identified **6 tracts** for local validation; the stricter interval heuristic retained **3**. ToolUniverse also returned **8 PubMed records** and **10 of 29 Alabama-matched trial records** as bounded follow-up material.

## Decision Question

Which Autauga County census tracts show concurrent modeled CHD and heart-health context signals that merit local data review, and what literature, trial-registry, and safety records should analysts inspect next?

## Method At A Glance

| Component | ToolUniverse tool | Role | Boundary |
| --- | --- | --- | --- |
| Reviewed local surveillance | `VSDCDCPlacesHeartHealthProfile` | Eight fixed tract-level measures with 95% confidence intervals | Modeled aggregate estimates |
| Reviewed global metadata | `VSDWHOHypertensionIndicator` | Hypertension indicator definition | Not a local measurement |
| Reviewed regulatory record | `VSDOpenFDALabelBySetId` | Public label safety context | Not efficacy evidence or advice |
| Literature discovery | `PubMed_search_articles` | Candidate tract-level CHD literature | Not a systematic review |
| Trial discovery | `ClinicalTrials_search_studies` | Active/upcoming Alabama-matched records | Site and eligibility require verification |

The reproducible screening rule encoded by the script is:

> Flag, without ranking, tracts whose CHD point estimate is above the county tract median and whose point estimates trigger at least four of seven direction-aware context signals.

## Exactly How ToolUniverse Was Used

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
| 2 | `VSDCDCPlacesHeartHealthProfile` | `{"county_name": "Autauga", "limit": 500, "state_abbr": "AL"}` | `{"estimate_count": 136, "measure_count": 8, "possibly_truncated": false, "tract_count": 17}` |
| 3 | `VSDWHOHypertensionIndicator` | `{}` | `{"indicator_code": "NCD_HYP_DIAGNOSIS_C"}` |
| 4 | `VSDOpenFDALabelBySetId` | `{"set_id": "0058175f-3474-40c3-a046-6cfaec86d84b"}` | `{"set_id": "0058175f-3474-40c3-a046-6cfaec86d84b"}` |
| 5 | `PubMed_search_articles` | `{"limit": 8, "query": "census tract[Title/Abstract] AND coronary heart disease[Title/Abstract] AND (smoking[Title/Abstract] OR hypertension[Title/Abstract] OR obesity[Title/Abstract] OR physical activity[Title/Abstract])", "sort": "relevance"}` | `{"article_count": 8}` |
| 6 | `ClinicalTrials_search_studies` | `{"filter_status": "RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION", "page_size": 10, "query_cond": "Coronary Heart Disease", "query_term": "AREA[LocationState]Alabama"}` | `{"returned_count": 10, "total_count": 29}` |

## County Measure Profile

All summaries are unweighted across census tracts.

| ID | Measure | Population | Direction | Mean | Median | IQR | Observed range |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| `ACCESS2` | Current lack of health insurance among adults aged 18-64 years | Adults aged 18-64 years | `higher_is_worse` | 9.04% | 9.0% | 7.5-10.6% | 5.7-12.2% |
| `BPHIGH` | High blood pressure among adults | Adults | `higher_is_worse` | 41.72% | 41.8% | 39.0-42.9% | 33.6-54.3% |
| `CHD` | Coronary heart disease among adults | Adults | `higher_is_worse` | 6.75% | 6.8% | 6.1-7.3% | 4.0-10.0% |
| `CHECKUP` | Visits to doctor for routine checkup within the past year among adults | Adults | `higher_is_better` | 80.73% | 80.5% | 80.2-81.2% | 78.9-83.5% |
| `CSMOKING` | Current cigarette smoking among adults | Adults | `higher_is_worse` | 15.11% | 15.6% | 12.9-16.7% | 9.3-21.3% |
| `HIGHCHOL` | High cholesterol among adults who have ever been screened | Adults who have ever been screened | `higher_is_worse` | 41.12% | 41.2% | 40.3-42.7% | 35.6-45.0% |
| `LPA` | No leisure-time physical activity among adults | Adults | `higher_is_worse` | 27.42% | 26.3% | 24.5-30.3% | 18.0-39.5% |
| `OBESITY` | Obesity among adults | Adults | `higher_is_worse` | 40.05% | 39.4% | 38.1-42.6% | 34.6-49.1% |

## Follow-Up Screening Set

**6 tracts** met the transparent rule. Rows are sorted by census tract ID, not by need or health. A context signal means an adverse measure was above its county tract median, or routine checkups were below their median.

| Census tract | CHD estimate (95% CI) | Context signals | Conservative signals | Signal IDs |
| --- | ---: | ---: | ---: | --- |
| `01001020100` | 7.2% (6.2-8.1%) | 4/7 | 0/7 | `ACCESS2`, `CHECKUP`, `HIGHCHOL`, `LPA` |
| `01001020300` | 7.3% (6.3-8.2%) | 6/7 | 0/7 | `ACCESS2`, `BPHIGH`, `CSMOKING`, `HIGHCHOL`, `LPA`, `OBESITY` |
| `01001020700` | 7.1% (6.3-7.9%) | 6/7 | 0/7 | `ACCESS2`, `BPHIGH`, `CHECKUP`, `CSMOKING`, `LPA`, `OBESITY` |
| `01001020803` | 8.3% (7.4-9.4%) | 7/7 | 3/7 | `ACCESS2`, `BPHIGH`, `CHECKUP`, `CSMOKING`, `HIGHCHOL`, `LPA`, `OBESITY` |
| `01001021000` | 8.4% (7.5-9.3%) | 6/7 | 4/7 | `ACCESS2`, `BPHIGH`, `CSMOKING`, `HIGHCHOL`, `LPA`, `OBESITY` |
| `01001021100` | 10.0% (9.0-11.0%) | 6/7 | 5/7 | `ACCESS2`, `BPHIGH`, `CSMOKING`, `HIGHCHOL`, `LPA`, `OBESITY` |

### Threshold Sensitivity

| Minimum context signals | Candidate tracts | Census tract IDs |
| ---: | ---: | --- |
| 3/7 | 6 | `01001020100`, `01001020300`, `01001020700`, `01001020803`, `01001021000`, `01001021100` |
| 4/7 | 6 | `01001020100`, `01001020300`, `01001020700`, `01001020803`, `01001021000`, `01001021100` |
| 5/7 | 5 | `01001020300`, `01001020700`, `01001020803`, `01001021000`, `01001021100` |
| 6/7 | 5 | `01001020300`, `01001020700`, `01001020803`, `01001021000`, `01001021100` |
| 7/7 | 1 | `01001020803` |

**Strict interval heuristic:** 3 tracts retained (`01001020803`, `01001021000`, `01001021100`). CHD confidence interval entirely above the county tract median and at least three context confidence intervals entirely on the attention side of their respective medians.
This is a sensitivity check, not a statistical-significance test.

### All Tract Profiles

| Census tract | CHD (95% CI) | Above tract median | Context signals | Conservative signals |
| --- | ---: | --- | ---: | ---: |
| `01001020100` | 7.2% (6.2-8.1%) | Yes | 4/7 | 0/7 |
| `01001020200` | 6.5% (5.8-7.3%) | No | 5/7 | 1/7 |
| `01001020300` | 7.3% (6.3-8.2%) | Yes | 6/7 | 0/7 |
| `01001020400` | 7.5% (6.5-8.5%) | Yes | 2/7 | 0/7 |
| `01001020501` | 5.4% (4.7-6.2%) | No | 0/7 | 0/7 |
| `01001020502` | 4.4% (3.8-4.9%) | No | 1/7 | 0/7 |
| `01001020503` | 6.1% (5.3-6.9%) | No | 0/7 | 0/7 |
| `01001020600` | 6.8% (6.0-7.7%) | No | 4/7 | 0/7 |
| `01001020700` | 7.1% (6.3-7.9%) | Yes | 6/7 | 0/7 |
| `01001020801` | 6.8% (6.0-7.6%) | No | 1/7 | 0/7 |
| `01001020803` | 8.3% (7.4-9.4%) | Yes | 7/7 | 3/7 |
| `01001020804` | 4.0% (3.6-4.5%) | No | 1/7 | 0/7 |
| `01001020805` | 6.1% (5.4-6.8%) | No | 0/7 | 0/7 |
| `01001020901` | 6.2% (5.5-6.9%) | No | 2/7 | 0/7 |
| `01001020902` | 6.6% (5.9-7.3%) | No | 2/7 | 0/7 |
| `01001021000` | 8.4% (7.5-9.3%) | Yes | 6/7 | 4/7 |
| `01001021100` | 10.0% (9.0-11.0%) | Yes | 6/7 | 5/7 |

## Exploratory Co-Variation

Exploratory co-variation only; shared modeling inputs, population differences, and spatial dependence are not adjusted.

| Context measure | Pearson r with CHD |
| --- | ---: |
| `ACCESS2` Current lack of health insurance among adults aged 18-64 years | 0.825 |
| `BPHIGH` High blood pressure among adults | 0.943 |
| `CHECKUP` Visits to doctor for routine checkup within the past year among adults | 0.494 |
| `CSMOKING` Current cigarette smoking among adults | 0.878 |
| `HIGHCHOL` High cholesterol among adults who have ever been screened | 0.902 |
| `LPA` No leisure-time physical activity among adults | 0.901 |
| `OBESITY` Obesity among adults | 0.797 |

## Evidence Discovery

### PubMed Candidates

Query: `census tract[Title/Abstract] AND coronary heart disease[Title/Abstract] AND (smoking[Title/Abstract] OR hypertension[Title/Abstract] OR obesity[Title/Abstract] OR physical activity[Title/Abstract])`

| PMID | Year | Article | Journal |
| --- | ---: | --- | --- |
| [40417800](https://pubmed.ncbi.nlm.nih.gov/40417800/) | 2025 | Climate Vulnerability and Cardiovascular-Kidney-Metabolic Disease in the United States. | Journal of the American Heart Association |
| [35354074](https://pubmed.ncbi.nlm.nih.gov/35354074/) | 2023 | Neighborhood-level Social Vulnerability and Prevalence of Cardiovascular Risk Factors and Coronary Heart Disease. | Current problems in cardiology |
| [41171261](https://pubmed.ncbi.nlm.nih.gov/41171261/) | 2025 | Manifestations of Structural Racism and Inequities in Cardiovascular Health Across US Neighborhoods. | JAMA health forum |
| [40925453](https://pubmed.ncbi.nlm.nih.gov/40925453/) | 2026 | Mediating Pathways Between Neighborhood Structural Investment and Cardiometabolic Health Across U.S. Cities. | American journal of preventive medicine |
| [34639726](https://pubmed.ncbi.nlm.nih.gov/34639726/) | 2021 | Google Street View-Derived Neighborhood Characteristics in California Associated with Coronary Heart Disease, Hypertension, Diabetes. | International journal of environmental research and public health |
| [33985498](https://pubmed.ncbi.nlm.nih.gov/33985498/) | 2021 | Risk of cardiovascular mortality, stroke and coronary heart mortality associated with aircraft noise around Congonhas airport, São Paulo, Brazil: a small-area study. | Environmental health : a global access science source |
| [38858276](https://pubmed.ncbi.nlm.nih.gov/38858276/) | 2024 | Historical Structural Racism in the Built Environment and Physical Health among Residents of Allegheny County, Pennsylvania. | Journal of urban health : bulletin of the New York Academy of Medicine |
| [40811585](https://pubmed.ncbi.nlm.nih.gov/40811585/) | 2025 | Exploring the association between smartphone-based place visitation data and neighborhood-level coronary heart disease in the United States. | PloS one |

### ClinicalTrials.gov Candidates

Returned 10 of 29 records matching active/upcoming status, CHD, and an Alabama location-area query. The compact search output does not prove that an Alabama site is currently open or near Autauga County; verify each record before use.

| NCT ID | Status | Phase | Enrollment | Study |
| --- | --- | --- | ---: | --- |
| [NCT04562532](https://clinicaltrials.gov/study/NCT04562532) | `ACTIVE_NOT_RECRUITING` | NA | 1720 | Firehawk Rapamycin Target Eluting Coronary Stent North American Trial |
| [NCT06909565](https://clinicaltrials.gov/study/NCT06909565) | `RECRUITING` | PHASE4 | 6000 | Inclisiran Versus Placebo for the Prevention of Major Adverse Cardiovascular and Limb Events in Patients Undergoing Percutaneous Coronary Intervention or Peripheral Endovascular Intervention |
| [NCT07517263](https://clinicaltrials.gov/study/NCT07517263) | `RECRUITING` | PHASE3 | 5700 | An Open Label Extension (OLE) Study (Following Completion of CTQJ230A12301) to Evaluate Long-term Safety and Tolerability of Pelacarsen (TQJ230) |
| [NCT03968445](https://clinicaltrials.gov/study/NCT03968445) | `ACTIVE_NOT_RECRUITING` | PHASE1 | 6 | Neuroinflammation After Myocardial Infarction - Imaging Substudy |
| [NCT07232069](https://clinicaltrials.gov/study/NCT07232069) | `RECRUITING` | PHASE3 | 1500 | PRE-EMPT: Prospective RandomizEd Evaluation and Management of Premature aTherosclerosis |
| [NCT06164730](https://clinicaltrials.gov/study/NCT06164730) | `RECRUITING` | PHASE1 | 85 | A Study of VERVE-102 in Patients With Familial Hypercholesterolemia or Premature Coronary Artery Disease |
| [NCT03947619](https://clinicaltrials.gov/study/NCT03947619) | `ACTIVE_NOT_RECRUITING` | NA | 527 | Primary Unloading and Delayed Reperfusion in ST-Elevation Myocardial Infarction: The STEMI-DTU Trial |
| [NCT04573660](https://clinicaltrials.gov/study/NCT04573660) | `RECRUITING` | Not applicable | 3784 | Abbott Vascular Medical Device Registry |
| [NCT04634240](https://clinicaltrials.gov/study/NCT04634240) | `RECRUITING` | NA | 4000 | Staged Complete Revascularization for Coronary Artery Disease vs Medical Management Alone in Patients With AS Undergoing Transcatheter Aortic Valve Replacement |
| [NCT07521007](https://clinicaltrials.gov/study/NCT07521007) | `NOT_YET_RECRUITING` | PHASE2 | 456 | A Phase 2b Clinical Trial of YN001 in Adults With Coronary Atherosclerosis |

## Independent Context

- WHO indicator `NCD_HYP_DIAGNOSIS_C`: Hypertension: diagnosis coverage among adults aged 30-79 with hypertension, crude (%).
- openFDA label `0058175f-3474-40c3-a046-6cfaec86d84b`: Low Dose Aspirin (ASPIRIN, ORAL); matched warning terms: `blood thinning`, `heart disease`, `high blood pressure`.

## Why The VSD Layer Matters

- Discovery maps packaged reviewed integrations to concrete ToolUniverse tool names.
- The CDC adapter exposes one fixed eight-measure heart-health contract rather than an arbitrary measure proxy.
- CDC responses are checked for reviewed measure IDs and names, county containment, unique tract-measure pairs, percentage bounds, and confidence-interval ordering.
- The shared transport pins a vetted public address, validates TLS hostname and peer, rejects redirects and encoded bodies, and caps responses at 1 MB.
- Each VSD result carries endpoint, exact query, retrieval time, media type, size, redirect count, and payload hash.
- Mutable registration and generic JSON querying remain in the explicit administration CLI, outside the agent tool surface.

## Guardrails And Limitations

- CDC PLACES values are modeled aggregate estimates, not individual observations.
- CDC advises against using PLACES estimates to rank the overall health of geographic areas; this dossier applies a transparent screening rule and does not produce a rank or composite score.
- Means and medians are unweighted across retrieved census tracts and are not county population estimates.
- Measure populations differ: insurance covers adults aged 18-64 and high cholesterol covers adults who have ever been screened.
- Within-county correlations use point estimates only and do not adjust for confidence intervals, shared model inputs, demographics, or spatial dependence.
- A screening flag is not a statistically significant difference, causal finding, diagnosis, or resource-allocation recommendation.
- The conservative interval-vs-median signal is a sensitivity heuristic, not a hypothesis test or an interval for the county tract median.
- The literature and trial searches are bounded discovery scans, not systematic reviews or endorsements of returned studies.
- An Alabama registry match does not establish an Autauga County site, eligibility, availability, efficacy, or safety.
- WHO metadata, CDC estimates, PubMed records, trial records, and the openFDA label are independent and are not joined at person level.
- The aspirin label is safety context, not evidence of treatment efficacy or advice.
- A reviewed VSD adapter establishes a constrained technical contract, not scientific endorsement.

## VSD Provenance

- **CDC PLACES**: `https://chronicdata.cdc.gov/resource/cwsq-ngmh.json`; HTTP 200; 33390 bytes; SHA-256 `f09485a58f25e14b3cf40c9fec10dd942c26247a6d252aceaae4d4e97d43122a`.
- **openFDA Drug Labels**: `https://api.fda.gov/drug/label.json`; HTTP 200; 8944 bytes; SHA-256 `aa3a391272c7b9be4ef6bd8714395cfbf14cef480fd65a0858f9046cd728ef00`.
- **WHO Global Health Observatory**: `https://ghoapi.azureedge.net/api/Indicator`; HTTP 200; 281 bytes; SHA-256 `49136dfd464ecaad2c2a530d0524316f19a62201e2c35c772da9a959b5e61d3c`.

## Reproducibility

Run `python examples/vsd/public_health_case_study.py` from the repository root.
The command overwrites the checked JSON, Markdown, tract-profile CSV, and measure-summary CSV artifacts.

Official references:

- [ToolUniverse Python API guide](https://zitniklab.hms.harvard.edu/ToolUniverse/getting_started.html)
- [CDC PLACES methodology](https://www.cdc.gov/places/methodology/index.html)
- [CDC PLACES measure definitions](https://www.cdc.gov/places/measure-definitions/index.html)
- [CDC PLACES frequently asked questions](https://www.cdc.gov/places/faqs/index.html)
- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-about-studies/learn-about-api)
- [openFDA drug-label API](https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/)
