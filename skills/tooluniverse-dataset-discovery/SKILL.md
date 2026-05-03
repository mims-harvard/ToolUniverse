---
name: tooluniverse-dataset-discovery
description: Find and evaluate research datasets for any scientific question. Teaches how to reason about data needs, search across public repositories, evaluate dataset fitness, and identify access requirements. Use whenever users ask to find data, search for datasets, identify cohort studies, or need data for analysis. Also use when users ask about a specific survey or cohort (NHANES, HRS, UK Biobank, TCGA, etc.), when they want to know what data exists for a research question, or when they need to compare available data sources. If the user mentions "where can I get data" or "is there a dataset for X", this is the right skill.
---

# Dataset Discovery

## When to Use
- User asks "find me data about X" or "where can I get data on Y"
- User wants to analyze a relationship between variables
- User needs specific study designs (longitudinal, cross-sectional, experimental)
- User asks about specific surveys or cohorts

## Step 1: Understand What the Research Question Requires

Before searching, determine the **minimum data requirements**:

**Study design needed:**
- "Does X predict CHANGES in Y over time?" → longitudinal (same people measured repeatedly). Cross-sectional data CANNOT answer this — don't settle for it.
- "Is X associated with Y?" → cross-sectional is sufficient (one-time measurement)
- "Does intervention X cause outcome Y?" → experimental (clinical trial with controls)
- "What genes/proteins are involved in X?" → omics (sequencing, expression, proteomics)

**Variables needed:**
- List the specific exposure, outcome, and confounder variables
- For each variable, note the measurement type (continuous, categorical, biomarker vs self-report)
- Identify minimum confounders needed (age, sex are almost always required; domain-specific confounders depend on the question)

**Population needed:**
- Age range, geography, clinical status, sample size requirements
- Power analysis: to detect a small effect (r=0.1), you need ~800 subjects at 80% power

## Step 2: Search Strategy

Search from broadest to most specific. Use `find_tools` to discover available dataset search tools — don't rely on memorized tool names.

**Layer 1 — Cross-repository search (cast wide net):**
Search tools that index datasets across thousands of repositories. These find datasets you didn't know existed.
- Search by: research topic keywords, variable names, population descriptors
- Look for: DOI-registered datasets, repository listings, government data portals

**Layer 2 — Domain-specific repositories:**
Search repositories specialized for your data type.
- Health surveys: CDC, NHANES (search by variable name, not topic keywords)
- Genomics: SRA, ENA, ArrayExpress, GEO
- Proteomics: PRIDE, MassIVE
- Metabolomics: MetaboLights, Metabolomics Workbench
- Clinical: ClinicalTrials.gov (for trial data with results)

**Layer 3 — Literature-based discovery:**
Many datasets aren't in any repository — they're described in paper methods sections.
- Search PubMed/EuropePMC for papers that analyzed the relationship you're interested in
- Read their methods: "We used data from [DATASET NAME]" tells you exactly what exists
- Check supplementary materials for deposited data (GEO/SRA accession numbers)
- This is often the MOST effective strategy for finding niche datasets

## Step 3: Evaluate Dataset Fitness

For each candidate dataset, assess these dimensions:

**Variables:**
- Does it contain your SPECIFIC exposure and outcome variables?
- Are they measured the way you need? (biomarker vs self-report, continuous vs categorical)
- Are key confounders available? (missing confounders = biased analysis)

**Design match:**
- If you need longitudinal: does it follow the SAME individuals over time? How many waves? What's the follow-up interval?
- Beware: "repeated cross-sections" (different people each wave) are NOT longitudinal
- If you need experimental: is there a proper control group? Randomization?

**Sample:**
- Is the sample large enough for your analysis? (logistic regression needs ~10 events per predictor)
- Does the population match? (age range, geography, clinical characteristics)
- Are there subgroups you need? (stratified by sex, race, disease status)

**Access:**
- Publicly downloadable (best) vs registration required (days) vs collaboration agreement (months) vs restricted (may be impossible)
- Data format: CSV/TSV (easy), XPT/SAS (need conversion), proprietary database (may need special software)

**Quality:**
- Is it from a well-known study with published methods? (NHANES, HRS, UK Biobank = high quality)
- Has it been used in peer-reviewed publications? (indicates data is usable)
- What's the response rate / missingness pattern?

## Step 4: Download and Analyze

Don't stop at finding datasets — download and analyze them. Write and run Python code via Bash. Never describe what you "would do" — execute it.

### Data Loading Cookbook

Choose the loader that matches your data source. When unsure of the format, download a small sample first and inspect.

```python
import requests, io, pandas as pd

# --- Tabular files (most common) ---
df = pd.read_csv("data.csv")                                # CSV / TSV (use sep="\t" for TSV)
df = pd.read_excel("data.xlsx")                              # Excel
df = pd.read_stata("data.dta")                               # Stata
df = pd.read_sas("data.xpt", format="xport")                # SAS transport (XPT)
df = pd.read_sas("data.sas7bdat", format="sas7bdat")        # SAS native
df = pd.read_parquet("data.parquet")                         # Parquet
df = pd.read_json("data.json")                               # JSON (records or columnar)
df = pd.read_fwf("data.dat")                                 # Fixed-width (some legacy surveys)

# --- Download from URL first, then parse ---
resp = requests.get(url, timeout=120)
content = resp.content
# Detect format from URL or content header
if url.endswith(".XPT") or url.endswith(".xpt"):
    df = pd.read_sas(io.BytesIO(content), format="xport")
elif url.endswith(".csv") or url.endswith(".csv.gz"):
    df = pd.read_csv(io.BytesIO(content))
elif url.endswith(".tsv") or url.endswith(".tsv.gz"):
    df = pd.read_csv(io.BytesIO(content), sep="\t")
elif url.endswith(".json"):
    df = pd.read_json(io.BytesIO(content))
else:
    # Try CSV first, then inspect
    df = pd.read_csv(io.BytesIO(content))

# --- REST API pagination (common for GDC, ClinicalTrials.gov, etc.) ---
import json
all_records = []
offset = 0
while True:
    resp = requests.get(f"{api_url}?offset={offset}&limit=100", timeout=30)
    batch = resp.json().get("data", [])
    if not batch:
        break
    all_records.extend(batch)
    offset += len(batch)
df = pd.DataFrame(all_records)
```

### Merge, Clean, Analyze

```python
# Merge multiple files on participant/sample ID
merged = df1.merge(df2, on="id_col", how="inner")

# Filter population
subset = merged[(merged["age"] >= 60) & (merged["age"] <= 80)].copy()

# Handle missing values
missing_pct = subset.isnull().mean() * 100
print("Missing % per variable:\n", missing_pct[missing_pct > 0].sort_values(ascending=False))
subset = subset.dropna(subset=["exposure_var", "outcome_var"])

# Quick regression
import statsmodels.formula.api as smf
model = smf.ols("outcome ~ exposure + age + sex", data=subset).fit()
print(model.summary())

# Visualization
import matplotlib.pyplot as plt
plt.scatter(subset["exposure"], subset["outcome"], alpha=0.3)
plt.xlabel("Exposure"); plt.ylabel("Outcome")
plt.savefig("/tmp/scatter.png", dpi=150, bbox_inches="tight")
```

Always run the code and report actual numbers (β, p-value, CI, N).

## Step 5: Report Honestly

Structure the report as:

1. **Best available dataset** — name, what it contains, access method, key limitation
2. **Analysis results** — actual statistics (β, p-value, CI, N) from running the code
3. **Alternative datasets** — ranked by fitness, with tradeoffs
4. **What CANNOT be answered** — if no dataset matches the study design needed, say so clearly
5. **Recommended next steps** — apply for access to longitudinal data, replicate in other cohorts

**Critical honesty rules:**
- Never claim a dataset answers a temporal question if it's cross-sectional
- Distinguish "data exists but needs registration" from "data doesn't exist"
- Report actual computed statistics, not hypothetical analyses
- State the strongest analysis possible with available data, even if it's weaker than what was asked

## LOOK UP, DON'T GUESS

Never assume a dataset exists — search for it. Never assume access is public — check. Never assume variables are measured the way you need — verify the codebook.
