# Quick Start: GWAS SNP Interpretation

Get started with interpreting genetic variants in under 5 minutes.

## Installation

```bash
# Install ToolUniverse (if not already installed)
pip install tooluniverse

# No additional dependencies required - uses built-in GWAS tools
```

## 60-Second Example

```python
from python_implementation import interpret_snp

# Interpret the famous TCF7L2 type 2 diabetes variant
report = interpret_snp('rs7903146')
print(report)

# Output:
# === SNP Interpretation: rs7903146 ===
# Basic Information:
#   Location: chr10:112998590
#   Consequence: intron_variant
#   Mapped Genes: TCF7L2
# Associations (100 found):
#   1. Type 2 diabetes (p=1.2e-128)
#   ...
# Credible Sets (20 found):
#   1. Type 2 diabetes - Predicted genes: TCF7L2 (0.863)
#   ...
```

## Python SDK Usage

### Basic Usage

```python
from python_implementation import interpret_snp

# Interpret a SNP
report = interpret_snp('rs429358')  # APOE Alzheimer's variant

# Access structured data
print(f"SNP: {report.snp_info.rs_id}")
print(f"Location: chr{report.snp_info.chromosome}:{report.snp_info.position}")
print(f"Genes: {', '.join(report.snp_info.mapped_genes)}")
print(f"Associations: {len(report.associations)}")
print(f"Credible sets: {len(report.credible_sets)}")
```

### Fast Mode (Associations Only)

```python
# Skip fine-mapping for faster results
report = interpret_snp('rs1801133', include_credible_sets=False)

# Takes 2-5 seconds vs 10-30 seconds
print(f"Found {len(report.associations)} associations")
```

### Custom Thresholds

```python
# Adjust significance threshold
report = interpret_snp(
    'rs12913832',  # Eye color variant
    p_threshold=5e-6,  # Suggestive threshold
    max_associations=50
)

# Filter associations
sig_assoc = [a for a in report.associations if a.p_value < 5e-8]
print(f"Genome-wide significant: {len(sig_assoc)}")
```

### Access Individual Components

```python
report = interpret_snp('rs7903146')

# SNP annotation
snp = report.snp_info
print(f"{snp.rs_id}: {snp.consequence} in {snp.mapped_genes[0]}")

# Top associations
for assoc in report.associations[:5]:
    print(f"{assoc.trait}: p={assoc.p_value:.2e}, study={assoc.study_id}")

# Credible sets with gene predictions
for cs in report.credible_sets[:3]:
    genes = [f"{g['gene']}({g['score']:.2f})" for g in cs.predicted_genes[:3]]
    print(f"{cs.trait}: {', '.join(genes)}")
```

## ToolUniverse Direct Usage

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Get SNP info
snp_result = tu.run_one_function({
    'name': 'gwas_get_snp_by_id',
    'arguments': {'rs_id': 'rs7903146'}
})
print(snp_result['data'])

# Get associations
assoc_result = tu.run_one_function({
    'name': 'gwas_get_associations_for_snp',
    'arguments': {
        'rs_id': 'rs7903146',
        'size': 10,
        'sort': 'p_value',
        'direction': 'asc'
    }
})
print(f"Found {len(assoc_result['data'])} associations")

# Get fine-mapping data (requires chr_pos_ref_alt format)
cred_result = tu.run_one_function({
    'name': 'OpenTargets_get_variant_credible_sets',
    'arguments': {
        'variantId': '10_112998590_C_T',
        'size': 10
    }
})
print(f"In {cred_result['data']['variant']['credibleSets']['count']} credible sets")
```

## MCP Integration

For Claude Desktop or other MCP clients:

### 1. Configure MCP Server

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "python",
      "args": ["-m", "tooluniverse.mcp"],
      "env": {
        "TOOLUNIVERSE_TOOLS": "gwas_get_snp_by_id,gwas_get_associations_for_snp,OpenTargets_get_variant_credible_sets"
      }
    }
  }
}
```

### 2. Use in Conversation

```
User: Interpret the SNP rs7903146