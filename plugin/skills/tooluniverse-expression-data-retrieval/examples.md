# Expression Data Retrieval Examples

## Example 1: Find Diabetes Gene Expression Studies

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Search ArrayExpress
result = tu.tools.arrayexpress_search_experiments(
    keywords="diabetes",
    species="Homo sapiens",
    limit=10
)

# Display results
for exp in result["data"]["experiments"][:5]:
    print(f"{exp['accession']}: {exp['title']}")
    print(f"  Files: {exp['files']}, released: {exp['release_date']}, views: {exp['views']}")
    # keys: accession, type, title, author, links, files, release_date, views, isPublic, content
```

## Example 2: Get Complete Experiment Details

```python
# Get experiment metadata
accession = "E-MTAB-5214"

details = tu.tools.arrayexpress_get_experiment(
    experiment_id=accession
)

# Study fields are name/value pairs under data.section.attributes
section = {a["name"]: a["value"] for a in details["data"]["section"]["attributes"]}
print(f"Title: {section['Title']}")
print(f"Description: {section['Description']}")

samples = tu.tools.arrayexpress_get_experiment_samples(
    experiment_id=accession
)
print(f"Samples: {samples['count']}")  # data is a list of per-sample annotation dicts

# Get associated files (data is a list; it came back empty for every experiment
# tested, so fall back to the BioStudies/GEO pages if it is empty)
files = tu.tools.arrayexpress_get_experiment_files(
    experiment_id=accession
)

print("\nAvailable files:")
for file in files["data"]:
    print(f"  {file}")
```

## Example 3: Search RNA-seq Experiments

```python
# Search for RNA-seq studies
result = tu.tools.arrayexpress_search_experiments(
    keywords="RNA-seq cancer",
    species="Homo sapiens",
    limit=20
)

# Filter for RNA-seq specifically
rnaseq_studies = [
    exp for exp in result["data"]["experiments"]
    if "rna-seq" in exp.get("title", "").lower()
]

print(f"Found {len(rnaseq_studies)} RNA-seq studies")
```

## Example 4: Multi-Omics Study from BioStudies

```python
# Search BioStudies for proteomics
result = tu.tools.biostudies_search(
    query="proteomics breast cancer",
    pageSize=10
)

# Get first study
study_acc = result["data"]["hits"][0]["accession"]

# Get detailed information
details = tu.tools.biostudies_get_study(
    accession=study_acc
)

# the title is an entry in data['attributes'] ([{'name': 'Title', 'value': ...}, ...])
title = next(a["value"] for a in details["data"]["attributes"] if a["name"] == "Title")
print(f"Study: {title}")
print(f"Type: {details['data']['type']}")

# Get files
files = tu.tools.biostudies_get_study_files(
    accession=study_acc
)
```

## Example 5: Compare Multiple Experiments

```python
# Search for related experiments
result = tu.tools.arrayexpress_search_experiments(
    keywords="liver tissue",
    species="Mus musculus",
    limit=10
)

# Get details for each
experiments = []
for exp in result["data"]["experiments"][:5]:
    details = tu.tools.arrayexpress_get_experiment(
        experiment_id=exp["accession"]
    )
    samples = tu.tools.arrayexpress_get_experiment_samples(
        experiment_id=exp["accession"]
    )
    section = {a["name"]: a["value"] for a in details["data"]["section"]["attributes"]}
    experiments.append({
        "accession": exp["accession"],
        "samples": samples["count"],
        "type": section.get("Study type")
    })

# Compare sample sizes
for exp in experiments:
    print(f"{exp['accession']}: {exp['samples']} samples")
```

## Example 6: Download Experiment Data

```python
# Get experiment files
accession = "E-MTAB-1234"

files = tu.tools.arrayexpress_get_experiment_files(
    experiment_id=accession
)

# data is a list of file records (empty for every experiment tested - if so,
# there is nothing to download through this tool)
for file in files["data"]:
    print(file)
    # Use file download tool to get actual file
```
