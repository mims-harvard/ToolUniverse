# BioGRID Tools - Quick Start Guide

## Setup (1 minute)

1. **Get Free API Key**: https://webservice.thebiogrid.org/
2. **Set Environment Variable**:
   ```bash
   export BIOGRID_ACCESS_KEY="your_key_here"
   ```

## Available Tools (4)

| Tool | Purpose | Example Gene |
|------|---------|--------------|
| `BioGRID_get_interactions` | Protein/genetic interactions | TP53, BRCA1 |
| `BioGRID_get_chemical_interactions` | Drug-target data | EGFR, AKT1 |
| `BioGRID_search_by_pubmed` | Interactions from papers | PubMed: 28514442 |
| `BioGRID_get_ptms` | Phosphorylation, etc. | TP53, ERK1 |

## Quick Examples

### 1. Get Protein Interactions

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Get TP53 interactions
result = tu.run({
    "name": "BioGRID_get_interactions",
    "arguments": {
        "gene_names": ["TP53"],
        "organism": "9606",  # Human
        "interaction_type": "physical",
        "limit": 50
    }
})

print(f"Status: {result['status']}")
print(f"Interactions: {len(result['data'])}")
```

### 2. Get Chemical-Protein Interactions

```python
# Get drugs targeting EGFR
result = tu.run({
    "name": "BioGRID_get_chemical_interactions",
    "arguments": {
        "gene_names": ["EGFR"],
        "organism": "9606",
        "limit": 20
    }
})
```

### 3. Get Interactions from a Paper

```python
# Get all interactions from a specific publication
result = tu.run({
    "name": "BioGRID_search_by_pubmed",
    "arguments": {
        "pubmed_ids": ["28514442"],
        "organism": "9606",
        "include_evidence": True
    }
})
```

### 4. Get PTMs (Phosphorylation Sites)

```python
# Get TP53 phosphorylation sites
result = tu.run({
    "name": "BioGRID_get_ptms",
    "arguments": {
        "gene_names": ["TP53"],
        "organism": "9606",
        "ptm_type": ["Phosphorylation"],
        "include_enzymes": True,
        "limit": 50
    }
})
```

## Common Parameters

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `gene_names` | list | `["TP53", "BRCA1"]` | Gene symbols |
| `organism` | string | `"9606"` | Human (9606), Mouse (10090) |
| `interaction_type` | string | `"physical"` | physical, genetic, both |
| `limit` | int | `50` | Max results (default: varies) |

## Interaction Types

**Physical**: Affinity Capture-MS, Two-hybrid, Co-IP
**Genetic**: Synthetic Lethality, Dosage Rescue

## PTM Types

- Phosphorylation
- Ubiquitination
- Acetylation
- Methylation
- Sumoylation

## Common Organisms

| Organism | NCBI Taxon ID |
|----------|---------------|
| Human | 9606 |
| Mouse | 10090 |
| Yeast | 559292 |
| Fly | 7227 |

## Error Handling

```python
if result["status"] == "error":
    print(f"Error: {result['error']}")
else:
    data = result["data"]
    # Process data
```

## Full Documentation

- Implementation: `docs/biogrid_tools_implementation.md`
- API Docs: https://wiki.thebiogrid.org/doku.php/biogridrest
- Get Key: https://webservice.thebiogrid.org/
