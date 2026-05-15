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
    print(f"{exp['accession']}: {exp['name']}")
    print(f"  Samples: {exp['samples']}")
    print(f"  Type: {exp.get('experimenttype', 'N/A')}")
```

## Example 2: Get Complete Experiment Details

```python
# Get experiment metadata
accession = "E-MTAB-5214"

details = tu.tools.arrayexpress_get_experiment(
    accession=accession
)

print(f"Title: {details['data']['title']}")
print(f"Description: {details['data']['description']}")
print(f"Samples: {details['data']['samples']}")

# Get associated files
files = tu.tools.arrayexpress_get_experiment_files(
    accession=accession
)

print("\nAvailable files:")
for file in files["data"]["files"]:
    print(f"  {file['name']} ({file['size']})")
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
    if "rna-seq" in exp.get("experimenttype", "").lower()
]

print(f"Found {len(rnaseq_studies)} RNA-seq studies")
```

## Example 4: Multi-Omics Study from BioStudies

```python
# Search BioStudies for proteomics
result = tu.tools.biostudies_search(
    query="proteomics breast cancer",
    limit=10
)

# Get first study
study_acc = result["data"]["studies"][0]["accession"]

# Get detailed information
details = tu.tools.biostudies_get_study(
    accession=study_acc
)

print(f"Study: {details['data']['title']}")
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
        accession=exp["accession"]
    )
    experiments.append({
        "accession": exp["accession"],
        "samples": details["data"]["samples"],
        "type": details["data"].get("experimenttype")
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
    accession=accession
)

# Find processed data file
for file in files["data"]["files"]:
    if "processed" in file["name"].lower():
        print(f"Processed data: {file['url']}")
        # Use file download tool to get actual file
```
