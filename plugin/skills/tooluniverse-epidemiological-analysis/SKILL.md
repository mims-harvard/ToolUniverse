---
name: tooluniverse-epidemiological-analysis
description: End-to-end observational epidemiology analysis — from research question (PECO Population/Exposure/Comparator/Outcome) to publication-ready statistical report. Covers cohort/case-control/cross-sectional design, regression with confounders, propensity scoring, sensitivity analysis. Writes Python code for every step. Use for epidemiology study analysis, NHANES/UK-Biobank-style analyses.
disable-model-invocation: true
---

# Epidemiological Data Analysis

Complete workflow for observational epidemiology — from research question to publication-ready report. Write and run Python code for every step. Never describe what you "would do" — do it.

## Step 1: Formulate the Research Question (PECO Framework)

Define **P**opulation, **E**xposure, **C**omparator, **O**utcome before touching data.

- **Population**: Who? (e.g., adults aged 20-79, cancer patients stage III+, ICU admissions)
- **Exposure**: What factor? (e.g., nutrient intake, drug treatment, gene mutation, environmental pollutant)
- **Comparator**: Vs. what? (e.g., lowest tertile, unexposed, wild-type, placebo)
- **Outcome**: What health event? (e.g., disease incidence, survival time, biomarker level, mortality)

**Study design check**: Does the question require temporality?
- Cross-sectional: prevalence, associations at one time point
- Longitudinal/cohort: incidence, causal inference, temporal relationships
- Case-control: rare outcomes, odds ratios (nested within cohort)
- Clinical trial: intervention effects with randomized controls

If the question implies causation ("does X cause Y?") but only cross-sectional data is available, state the limitation explicitly and proceed with association language.

## Step 2: Find and Evaluate Data

Use ToolUniverse to discover datasets and find what prior studies used:

```python
# Search for relevant datasets — use find_tools to discover what's available
find_tools("dataset search")
find_tools("your domain keywords")  # e.g., "cancer genomics", "clinical trial", "survey health"

# Search literature for study precedents — papers cite their data sources
execute_tool("PubMed_search_articles", {"query": "[exposure] [outcome] [study design]", "max_results": 5})
execute_tool("EuropePMC_search_articles", {"query": "[exposure] [outcome] cohort", "limit": 5})
```

**Evaluate dataset fitness**: Does it have the exposure variable? The outcome? Key confounders (age, sex, plus domain-specific)? Adequate sample size?

**Power analysis** (run before committing to a dataset):

```python
from scipy.stats import norm
import numpy as np

def sample_size_logistic(p0, OR, alpha=0.05, power=0.80):
    """Minimum N for logistic regression detecting OR at given power."""
    p1 = (p0 * OR) / (1 - p0 + p0 * OR)
    z_a, z_b = norm.ppf(1 - alpha/2), norm.ppf(power)
    n = ((z_a + z_b)**2 * (1/(p0*(1-p0)) + 1/(p1*(1-p1)))) / (np.log(OR))**2
    return int(np.ceil(n))

print(f"Need N={sample_size_logistic(0.10, 1.5)} for OR=1.5 with 10% baseline prevalence")
```

## Step 3: Download and Prepare Data

Download data programmatically. Adapt the loading code to your data source's format.

```python
import pandas as pd
import requests, io

# Generic download helper — adapt URL and format to your source
def download_and_parse(url, fmt="csv"):
    r = requests.get(url, timeout=120)
    content = io.BytesIO(r.content)
    if fmt == "xpt":
        return pd.read_sas(content, format="xport")
    elif fmt == "csv":
        return pd.read_csv(content)
    elif fmt == "tsv":
        return pd.read_csv(content, sep="\t")
    elif fmt == "stata":
        return pd.read_stata(content)
    elif fmt == "json":
        return pd.read_json(content)
    else:
        return pd.read_csv(content)  # default fallback

# Load and merge multiple files on shared ID column
df1 = download_and_parse(url1, fmt="xpt")
df2 = download_and_parse(url2, fmt="xpt")
df = df1.merge(df2, on="id_col", how="inner")

# Filter population (inclusion/exclusion criteria)
df = df[(df['age'] >= 20) & (df['age'] < 80)]

# Handle missing data
missing_pct = df.isnull().mean() * 100
print("Missing % per variable:\n", missing_pct[missing_pct > 0].sort_values(ascending=False))
# Decision: complete case if <5% missing; multiple imputation if 5-20%; drop variable if >20%

# Variable coding (adapt to your data)
df['age_group'] = pd.cut(df['age'], bins=[20,40,60,80], labels=['20-39','40-59','60-79'])
df['outcome_binary'] = (df['outcome_continuous'] >= threshold).astype(int)
```

**Survey weights**: Some surveys (NHANES, BRFSS, MEPS) require sampling weights for valid inference. Check the survey documentation. For weighted regression, use `statsmodels.stats.weightstats` or linearmodels.

**International/LMIC population health**: for a PECO question outside the US, `DHSProgram_search_indicators`/`DHSProgram_get_data` covers the same kind of national survey indicators (fertility, maternal/child mortality, nutrition, immunization, HIV) across many countries, filterable by country and survey year — the NHANES/BRFSS-style source when the population isn't the US.

**EU health dataset discovery**: for a PECO question centered on Europe, `src/tooluniverse/data/euhealth_tools.json` provides ~20 topic-scoped dataset-discovery tools (`euhealthinfo_search_cancer`, `_search_deaths`, `_search_causes_of_death`, `_search_births`, `_search_infectious_diseases`, `_search_covid_19`, `_search_healthcare_expenditure`, `_search_diabetes_epidemiology_registry`, `_search_hospital_in_patient_data`, `_search_population_health_survey`, `_search_key_indicators_registries_surveys`, `_search_surveillance_mortality_rates`, `_search_surveillance`, `_search_primary_care_workforce`, `_search_obesity`, `_search_vaccination`, `_search_mental_health`, `_search_disability`, `_search_alcohol_tobacco_psychoactive_use`, `_search_cancer_registry`) plus `euhealthinfo_deepdive`. **These find WHERE relevant European datasets/registries live — dataset metadata (title, landing page, keywords, license, spatial/language coverage), not the raw statistics themselves.** They all share one parameter shape: `limit` (default 25), `country` (full name or ISO-3166 code), `language` (ISO 639-1 or full name), `term_override` (replace the tool's built-in topic seed query with your own text), `method` (`keyword`/`embedding`/`hybrid`, default `hybrid`), `alpha` (blend ratio for hybrid), `top_k`. Response shape (verified live): `{"results": [...]}` or a bare array, each hit carrying `uuid`, `title`, `landing_page`, `license`, `keywords`, `themes`, `language`, `spatial`, `snippet` — feed a hit's `uuid` (or the search topic name directly) into `euhealthinfo_deepdive({"uuids": [...]}` or `{"topic": "euhealthinfo_search_cancer", ...}`)` to resolve classified outgoing links (download pages, resource portals) per dataset.

**Setup required before first use**: as of this writing, these tools return `{"warning": "EUHealth datastore not found locally (euhealth.db missing)...", "results": []}` — verified live, not a guess — until the underlying dataset index is synced locally:
```bash
export HF_TOKEN=YOUR_HF_TOKEN
tu-datastore sync-hf download --repo "agenticx/tooluniverse-datastores" --collection euhealth --overwrite
```
Check for this warning in the response before treating an empty result as "no matching dataset exists" — an empty `results` array with the datastore warning means the tool isn't set up yet, not that nothing was found. Once synced, treat this family as Step 2's European counterpart to the NHANES/DHS discovery pattern above: find the right registry/dataset here, then move to Step 3 to actually download and parse it.

**COVID-19 case/death/vaccination time series**: for outbreak-surveillance
PECO questions, `src/tooluniverse/data/diseasesh_tools.json` and
`src/tooluniverse/data/disease_sh_ext_tools.json` (Disease.sh API, sourced
from JHU CSSE) give global/country/historical case-death-recovery counts
and vaccine coverage — no auth, no setup needed (verified live, unlike
euhealth above). `DiseaseSh_get_global_stats` (no params) -> worldwide
totals; `DiseaseSh_get_country_stats {"country": ...}` -> one country's
current snapshot; `DiseaseSh_get_historical {"country": ..., "lastdays":
...}` -> daily cumulative timeline; `DiseaseSH_get_vaccine_coverage
{"country": ..., "lastdays": ...}` -> vaccination-dose timeline. **Note a
real near-duplicate, verified live**: `DiseaseSh_get_historical` (from
`diseasesh_tools.json`) and `DiseaseSH_get_covid_historical` (from
`disease_sh_ext_tools.json`) return the same timeline shape for the same
country/day-range from the same underlying API — pick either one, they are
not two independent data sources despite living in different tool files.
`country: "all"` is not a valid value for the per-country tools (verified
live: `DiseaseSh_get_country_stats {"country": "all"}` errors with
"Country not found or doesn't have any cases") — use
`DiseaseSh_get_global_stats` for a worldwide aggregate instead.

**Global health indicators (WHO GHO)**: for cross-country comparisons or a PECO question needing a WHO-tracked indicator (life expectancy, NCD prevalence, immunization coverage, mortality, air pollution, etc. — 2000+ indicators), `WHOGHO_search_indicators`/`WHOGHO_get_indicator_data`/`WHOGHO_list_dimension_values` query WHO's Global Health Observatory OData API directly, no auth required (verified live). **Parameter gotcha**: these use OData filter syntax, not a plain keyword string — `WHOGHO_search_indicators {"filter": "contains(IndicatorName,'life expectancy')", "top": 5}` (not `{"query": ...}`, which errors), and `WHOGHO_get_indicator_data {"indicator_code": "WHOSIS_000001", "filter": "SpatialDim eq 'USA' and TimeDim eq 2019", "top": 5}` to scope to one country/year (omitting `filter` returns the full multi-country/multi-year series, e.g. 12,936 rows for life expectancy — always filter). `WHOGHO_list_dimension_values {"dimension_code": "COUNTRY"}` resolves valid `SpatialDim` codes; pass `dimension_code: "Dimension"` to list all 195 filterable dimensions. Verified real value: US female life expectancy at birth, 2019 = 81.0 years (WHOSIS_000001).

**Real-time environmental exposure (air quality)**: for a PECO question with an air-pollution exposure arm, `WAQI_get_air_quality {"city": "..."}` returns the current station-measured Air Quality Index for a named city/monitoring station (verified live: Berlin -> AQI 87, dominant pollutant + per-pollutant sub-indices in `data.iaqi`), no auth required. `OpenMeteo_get_air_quality {"latitude": ..., "longitude": ...}` instead returns modeled hourly PM2.5/PM10/CO/NO2/O3/SO2 concentrations (not just an index) for any lat/lon, including short-range forecast hours, and is the better source when the study needs a continuous concentration variable rather than a categorical AQI, or when the location has no nearby WAQI station. Use these as the environmental-exposure counterpart to the health-outcome sources above (e.g. join AQI/PM2.5 by city-day to an outcome dataset) — neither returns historical time series more than a few days back, so for a retrospective cohort's exposure history use `OpenMeteo_get_historical_climate` or a dedicated air-quality archive instead.

**US county/community-level social determinants**: `health_disparities_get_svi_info`/`health_disparities_get_county_rankings_info` (CDC/ATSDR Social Vulnerability Index and County Health Rankings) — **verified live: these are pointer/metadata tools, not data-retrieval tools.** Despite accepting `state`/`county` parameters, the response is a fixed `access_url` to the source website plus a description of what's available there (download URL, data year, geography level) — it does not return per-county SVI scores or ranking numbers in the JSON. Use these to find where the dataset lives and what it covers, then download the actual CSV from the returned URL for analysis, the same "discovery, not data" pattern as the euhealth tools above.

**REST API data**: For sources like GDC (TCGA), ClinicalTrials.gov, or OpenTargets, paginate through the API:
```python
all_records = []
offset = 0
while True:
    resp = requests.get(f"{api_url}?offset={offset}&limit=500", timeout=30)
    batch = resp.json().get("data", [])
    if not batch:
        break
    all_records.extend(batch)
    offset += len(batch)
df = pd.DataFrame(all_records)
```

## Step 4: Descriptive Statistics (Table 1)

```python
# Table 1: mean +/- SD for continuous, N(%) for categorical, by exposure group
continuous_vars = ['age', 'bmi']  # adapt to your variables
for var in continuous_vars:
    print(df.groupby('exposure_group')[var].agg(['mean', 'std', 'count']))

categorical_vars = ['sex', 'race']  # adapt to your variables
for var in categorical_vars:
    print(pd.crosstab(df['exposure_group'], df[var], normalize='index') * 100)
```

Check distributions: `df[var].skew()`, `scipy.stats.shapiro()`, histograms for outliers.

## Step 5: Regression Analysis

**Sequential adjustment strategy** (build evidence for confounding):

```python
import statsmodels.formula.api as smf
import numpy as np

# Model 1: Unadjusted
m1 = smf.logit('outcome ~ exposure', data=df).fit(disp=0)

# Model 2: + demographics
m2 = smf.logit('outcome ~ exposure + age + sex + race', data=df).fit(disp=0)

# Model 3: + clinical factors
m3 = smf.logit('outcome ~ exposure + age + sex + race + bmi + smoking + alcohol', data=df).fit(disp=0)

# Report ORs with 95% CI
for name, model in [('Unadjusted', m1), ('Demographics', m2), ('Fully adjusted', m3)]:
    or_val = np.exp(model.params['exposure'])
    ci = np.exp(model.conf_int().loc['exposure'])
    print(f"{name}: OR={or_val:.2f} (95% CI: {ci[0]:.2f}-{ci[1]:.2f}), p={model.pvalues['exposure']:.4f}")
```

**Model selection by outcome type**:
- Continuous outcome: `smf.ols()`
- Binary outcome: `smf.logit()`
- Ordered categories: `OrderedModel` from statsmodels
- Time-to-event: `CoxPHFitter` from lifelines
- Count data: `smf.poisson()` or `smf.negativebinomial()`

**Assumption checks**:

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

# Multicollinearity (VIF > 5 is concerning, > 10 is severe)
X = df[['age', 'bmi', 'exposure']].dropna()
for i, col in enumerate(X.columns):
    print(f"VIF {col}: {variance_inflation_factor(X.values, i):.1f}")
```

## Step 6: Sensitivity Analyses

```python
# Stratified analysis (effect modification)
for stratum_var in ['sex', 'age_group', 'race']:
    print(f"\n--- Stratified by {stratum_var} ---")
    for level, sub in df.groupby(stratum_var):
        if len(sub) < 50: continue
        try:
            m = smf.logit('outcome ~ exposure + age + bmi', data=sub).fit(disp=0)
            or_val = np.exp(m.params['exposure'])
            ci = np.exp(m.conf_int().loc['exposure'])
            print(f"  {level}: OR={or_val:.2f} ({ci[0]:.2f}-{ci[1]:.2f}), p={m.pvalues['exposure']:.3f}, N={len(sub)}")
        except: print(f"  {level}: model failed (N={len(sub)})")

# Exclude outliers (+/- 3 SD) and re-run
df_no_outliers = df[np.abs(stats.zscore(df['exposure'].dropna())) < 3]
m_robust = smf.logit('outcome ~ exposure + age + sex + bmi', data=df_no_outliers).fit(disp=0)

# Confounder-adjusted exposure (residual method, e.g., energy-adjusted nutrient intake)
# Use when exposure correlates strongly with a confounder (total calories, body size, etc.)
adj_model = smf.ols('exposure ~ confounder', data=df).fit()
df['exposure_adj'] = adj_model.resid

# Multiple comparisons note
n_tests = 5  # number of exposure-outcome pairs tested
bonferroni_threshold = 0.05 / n_tests
```

## Step 7: Biological Interpretation (ToolUniverse Advantage)

This is where ToolUniverse adds value beyond any statistics package. After finding a statistical association, investigate the biological plausibility. Use `find_tools` to discover the right tools for your domain.

```python
# 1. Literature evidence — search for mechanism connecting exposure to outcome
execute_tool("PubMed_search_articles", {"query": "[exposure] [outcome] mechanism", "max_results": 5})
execute_tool("EuropePMC_search_articles", {"query": "[exposure] [outcome] mouse model in vivo", "limit": 5})

# 2. Pathway/molecular context — discover tools for your exposure type
find_tools("[exposure type] pathway")       # e.g., "nutrient pathway", "drug target", "chemical toxicology"
find_tools("[outcome type] gene disease")   # e.g., "diabetes gene", "cancer survival", "cardiac risk"

# 3. Gene-disease evidence (if a gene/variant is involved)
find_tools("gene disease association")
find_tools("variant functional annotation")

# 4. Drug/chemical mechanisms (if a drug or chemical is the exposure)
find_tools("drug mechanism target")
find_tools("chemical gene interaction")
```

**The pattern**: Exposure X → (what molecular pathway?) → (what biological process?) → Outcome Y. Use ToolUniverse tools to fill in the middle steps. This converts a statistical association into a biologically plausible hypothesis.

## Step 8: Visualization

Key plots to produce (use matplotlib):
- **Forest plot**: stratified ORs with 95% CI, vertical reference line at OR=1, log scale x-axis
- **Dose-response curve**: exposure quartile medians on x-axis vs outcome prevalence/mean on y-axis
- **DAG**: directed acyclic graph showing assumed causal structure (exposure, confounders, outcome)
- **Scatter + regression line**: for continuous outcomes with `sns.regplot()`

## Step 9: Report Structure

Write the final report in this order:

1. **Background**: What is known, what gap this analysis addresses (cite PubMed searches from Step 7)
2. **Methods**: PECO, data source, inclusion/exclusion, variable definitions, statistical approach, sensitivity analyses
3. **Results**: Table 1, unadjusted and adjusted ORs/HRs, stratified results, dose-response, sensitivity checks
4. **Discussion**: Compare to prior literature (PubMed), biological plausibility (ToolUniverse pathway/mechanism findings), clinical significance of effect size
5. **Limitations**: Study design constraints, unmeasured confounding, selection bias, measurement error, generalizability

**Key limitations to always state**:
- Cross-sectional design cannot establish temporality (if applicable)
- Residual confounding from unmeasured variables
- Self-reported exposure data may have recall bias
- Survey weights may not fully account for non-response bias

## Completeness Checklist

Before finalizing any epidemiological analysis:

- [ ] PECO defined and documented
- [ ] Study design matches the research question
- [ ] Sample size adequate (power analysis done)
- [ ] Missing data reported and handled
- [ ] Table 1 produced
- [ ] Unadjusted AND adjusted models reported
- [ ] Confounders justified (not just statistically selected)
- [ ] Assumptions checked (VIF, linearity, model fit)
- [ ] At least one sensitivity analysis performed
- [ ] Biological plausibility investigated via ToolUniverse
- [ ] Effect size interpreted in clinical context (not just p-value)
- [ ] Limitations explicitly stated
