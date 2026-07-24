# Protein Interaction Network Analysis - Quick Start

**One-minute guide** to analyzing protein networks with ToolUniverse.

## Basic Usage (Copy & Paste)

```python
from tooluniverse import ToolUniverse
from python_implementation import analyze_protein_network

# 1. Initialize (once)
tu = ToolUniverse()

# 2. Analyze your proteins
result = analyze_protein_network(
    tu=tu,
    proteins=["TP53", "MDM2", "ATM"],  # Your proteins here
    species=9606,                       # 9606=human, 10090=mouse
    confidence_score=0.7                # 0.7=high confidence
)

# 3. View results
print(f"✅ {len(result.mapped_proteins)} proteins mapped")
print(f"✅ {result.total_interactions} interactions found")
print(f"✅ {len(result.enriched_terms)} GO terms enriched")
```

## Common Tasks

### Find Interaction Partners

```python
# Single protein → discover partners
result = analyze_protein_network(tu=tu, proteins=["TP53"])

print("Top 5 partners:")
for edge in result.network_edges[:5]:
    print(f"  {edge['preferredName_B']}: score {edge['score']}")
```

### Test if Proteins Form Complex

```python
# Multiple proteins → test functional coherence
proteins = ["TP53", "ATM", "CHEK2", "BRCA1"]
result = analyze_protein_network(tu=tu, proteins=proteins)

p_val = result.ppi_enrichment.get("p_value", 1.0)
if p_val < 0.05:
    print("✅ Proteins form functional module!")
else:
    print("⚠️  Proteins may be unrelated")
```

### Find Enriched Pathways

```python
# Pathway proteins → discover enrichment
proteins = ["MAPK1", "MAPK3", "RAF1", "MAP2K1"]
result = analyze_protein_network(tu=tu, proteins=proteins)

print("\nTop 3 pathways:")
for term in result.enriched_terms[:3]:
    print(f"  {term['term']}: FDR={term['fdr']:.2e}")
```

### Export to Cytoscape

```python
# Build network → export for visualization
result = analyze_protein_network(tu=tu, proteins=["TP53", "BCL2", "BAX"])

import pandas as pd
df = pd.DataFrame(result.network_edges)
df.to_csv("network.tsv", sep="\t", index=False)
```

## Parameters Cheat Sheet

| Parameter | Values | When to Use |
|-----------|--------|-------------|
| `species` | 9606 (human), 10090 (mouse) | Match your organism |
| `confidence_score` | 0.4 (low), 0.7 (high), 0.9 (very high) | Higher = fewer interactions |
| `include_biogrid` | True/False | Use if have API key + want validation |
| `include_structure` | True/False | Add if need 3D structures (slower) |

## Clean Output

ToolUniverse prints many warnings. Filter them:

```bash
python your_script.py 2>&1 | grep -v "Error loading tools"
```

## What You Get Back

```python
result.mapped_proteins      # List of protein mappings
result.network_edges        # List of interactions with scores
result.enriched_terms       # List of GO terms (FDR < 0.05)
result.ppi_enrichment       # Dict with p-value for module test
result.warnings             # List of any issues encountered
```

## Example: TP53 Network

```python
from tooluniverse import ToolUniverse
from python_implementation import analyze_protein_network

tu = ToolUniverse()

result = analyze_protein_network(
    tu=tu,
    proteins=["TP53", "MDM2", "ATM", "CHEK2", "CDKN1A"],
    species=9606,
    confidence_score=0.7
)

# Results:
# ✅ 5/5 proteins mapped (100%)
# ✅ 10 interactions (all high confidence 0.98-0.999)
# ✅ 374 enriched GO terms
# ✅ PPI p-value = 1.99e-06 (highly significant module)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No interactions found | Lower `confidence_score` to 0.4 |
| Slow performance | This is normal (ToolUniverse limitation) |
| 40+ error messages | Filter with `grep -v "Error loading tools"` |
| BioGRID not working | Need BIOGRID_API_KEY in environment |

## Need More?

- **Full docs**: See `SKILL.md`
- **Implementation**: See `python_implementation.py`
- **Known issues**: See `KNOWN_ISSUES.md`
- **Bug report**: See `TOOLUNIVERSE_BUG_REPORT.md`

## Species IDs

- `9606` - Human
- `10090` - Mouse  
- `10116` - Rat
- `7227` - Fly
- `6239` - Worm
- `559292` - Yeast

**That's it!** Start analyzing protein networks in 60 seconds.
