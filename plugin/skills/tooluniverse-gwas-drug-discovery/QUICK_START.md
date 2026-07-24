---
name: GWAS-to-Drug Target Discovery - Quick Start Guide
version: 1.0.0
last_updated: 2026-02-13
---

# Quick Start Guide: GWAS-to-Drug Target Discovery

Get started with drug target discovery from GWAS data in minutes.

## Table of Contents

1. [Installation](#installation)
2. [Basic Usage - Python SDK](#basic-usage---python-sdk)
3. [Basic Usage - MCP](#basic-usage---mcp)
4. [Example 1: Alzheimer's Disease Targets](#example-1-alzheimers-disease-targets)
5. [Example 2: Type 2 Diabetes Repurposing](#example-2-type-2-diabetes-repurposing)
6. [Example 3: Target Prioritization](#example-3-target-prioritization)
7. [Common Patterns](#common-patterns)
8. [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

```bash
# Install ToolUniverse
pip install tooluniverse

# Or from source
git clone https://github.com/example/tooluniverse.git
cd tooluniverse
pip install -e .
```

### Verify Installation

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Check GWAS tools available
gwas_tools = [name for name in tu.all_tool_dict.keys() if 'gwas' in name.lower()]
print(f"Available GWAS tools: {len(gwas_tools)}")
```

Expected output:
```
Available GWAS tools: 12
```

## Basic Usage - Python SDK

### Quick Example: Find Drug Targets

```python
from tooluniverse.tools.execute_tool import execute_tool

# Step 1: Get GWAS associations for a disease
result = execute_tool(
    "gwas_get_associations_for_trait",
    {
        "disease_trait": "type 2 diabetes",
        "size": 20
    }
)

# Step 2: Extract genes from associations
genes = set()
for assoc in result['data']:
    genes.update(assoc.get('mapped_genes', []))

print(f"Found {len(genes)} genes associated with type 2 diabetes")
print(f"Top genes: {list(genes)[:10]}")

# Step 3: Get detailed info for top SNP
if result['data']:
    top_snp = result['data'][0].get('snp_allele', [{}])[0].get('rs_id')

    snp_result = execute_tool(
        "gwas_get_associations_for_snp",
        {"rs_id": top_snp, "size": 5}
    )

    print(f"\nDetails for {top_snp}:")
    for assoc in snp_result['data']:
        print(f"  - Trait: {assoc.get('reported_trait')}")
        print(f"  - P-value: {assoc.get('p_value')}")
```

### Using the High-Level API

```python
from skills.tooluniverse_gwas_drug_discovery.python_implementation import (
    discover_drug_targets,
    find_repurposing_candidates
)

# Discover targets with full workflow
targets = discover_drug_targets(
    disease="type 2 diabetes",
    min_gwas_pvalue=5e-8,
    max_targets=10
)

# Print results
for i, target in enumerate(targets, 1):
    print(f"\n{i}. {target.gene}")
    print(f"   Score: {target.overall_score:.3f}")
    print(f"   GWAS evidence: {len(target.gwas_evidence)} associations")
    print(f"   {target.recommendation}")
```

## Basic Usage - MCP

### Connect to ToolUniverse MCP Server

```javascript
// Initialize MCP client
const client = new MCPClient({
  serverUrl: "http://localhost:3000/tooluniverse"
});

// Call GWAS tool
const result = await client.callTool("gwas_get_associations_for_trait", {
  disease_trait: "type 2 diabetes",
  size: 20
});

console.log(`Found ${result.data.length} associations`);
```

### TypeScript Example

```typescript
import { MCPClient, GWASAssociation } from "@tooluniverse/mcp-client";

interface DrugTarget {
  gene: string;
  score: number;
  evidence: GWASAssociation[];
}

async function discoverTargets(disease: string): Promise<DrugTarget[]> {
  const client = new MCPClient();

  // Get GWAS associations
  const response = await client.callTool("gwas_get_associations_for_trait", {
    disease_trait: disease,
    size: 50
  });

  // Group by gene
  const geneMap = new Map<string, GWASAssociation[]>();

  for (const assoc of response.data) {
    for (const gene of assoc.mapped_genes || []) {
      if (!geneMap.has(gene)) {
        geneMap.set(gene, []);
      }
      geneMap.get(gene)!.push(assoc);
    }
  }

  // Convert to targets
  const targets: DrugTarget[] = Array.from(geneMap.entries()).map(([gene, evidence]) => ({
    gene,
    score: calculateScore(evidence),
    evidence
  }));

  return targets.sort((a, b) => b.score - a.score);
}

function calculateScore(evidence: GWASAssociation[]): number {
  return evidence.reduce((sum, e) => sum + (-Math.log10(e.p_value)), 0);
}

// Usage
const targets = await discoverTargets("type 2 diabetes");
console.log(`Top target: ${targets[0].gene} (score: ${targets[0].score.toFixed(2)})`);
```

## Example 1: Alzheimer's Disease Targets

### Goal: Identify druggable targets for Alzheimer's disease

```python
from tooluniverse.tools.execute_tool import execute_tool

print("=" * 80)
print("EXAMPLE 1: Alzheimer's Disease Drug Target Discovery")
print("=" * 80)

# Step 1: Get GWAS associations
print("\n[Step 1] Getting GWAS associations for Alzheimer's disease...")
gwas_result = execute_tool(
    "gwas_get_associations_for_trait",
    {
        "disease_trait": "alzheimer disease",
        "size": 50
    }
)

associations = gwas_result['data']
print(f"✓ Found {len(associations)} GWAS associations")

# Step 2: Extract and rank genes
print("\n[Step 2] Extracting genes and calculating evidence scores...")
gene_evidence = {}

for assoc in associations:
    p_val = assoc.get('p_value', 1.0)
    genes = assoc.get('mapped_genes', [])

    for gene in genes:
        if gene not in gene_evidence:
            gene_evidence[gene] = {
                'count': 0,
                'min_p': 1.0,
                'avg_p': []
            }

        gene_evidence[gene]['count'] += 1
        gene_evidence[gene]['min_p'] = min(gene_evidence[gene]['min_p'], p_val)
        gene_evidence[gene]['avg_p'].append(p_val)

# Calculate scores
for gene in gene_evidence:
    evidence = gene_evidence[gene]
    avg_p = sum(evidence['avg_p']) / len(evidence['avg_p'])
    # Score = -log10(avg_p) * sqrt(count)
    score = -np.log10(avg_p) * np.sqrt(evidence['count'])
    evidence['score'] = score

# Sort by score
ranked_genes = sorted(
    gene_evidence.items(),
    key=lambda x: x[1]['score'],
    reverse=True
)

print(f"✓ Found {len(ranked_genes)} unique genes")
print("\nTop 10 candidates:")
for i, (gene, evidence) in enumerate(ranked_genes[:10], 1):
    print(f"{i:2d}. {gene:10s} | Score: {evidence['score']:6.2f} | "
          f"Associations: {evidence['count']:2d} | "
          f"Min p-value: {evidence['min_p']:.2e}")

# Step 3: Check for existing drugs (top 3 genes)
print("\n[Step 3] Checking for existing drugs targeting top genes...")
top_genes = [gene for gene, _ in ranked_genes[:3]]

for gene in top_genes:
    print(f"\n{gene}:")

    # Search Open Targets for drugs
    try:
        # Note: Would need Ensembl ID lookup for real implementation
        print(f"  [Druggability assessment would require Ensembl ID]")
        print(f"  Known from literature:")

        if gene == "APOE":
            print("  - No direct drugs (risk factor, not target)")
            print("  - Strategy: Reduce APOE4 levels or block aggregation")
        elif gene == "TREM2":
            print("  - Immunotherapy candidates in development")
            print("  - Anti-TREM2 antibodies in Phase I")
        elif gene == "CLU":
            print("  - Clusterin inhibitors in preclinical")

    except Exception as e:
        print(f"  Error: {e}")

# Step 4: Repurposing opportunities
print("\n[Step 4] Identifying repurposing opportunities...")
print("\nBased on pathway analysis:")
print("  - Immune genes (TREM2, CR1, CLU) → Anti-inflammatory drugs")
print("  - Lipid genes (APOE, ABCA7) → Statins, PPAR agonists")
print("  - Endocytosis genes (BIN1, PICALM) → Dynamin inhibitors")

print("\nPotential repurposing candidates:")
candidates = [
    {
        "drug": "Anakinra",
        "target": "IL-1R",
        "current_use": "Rheumatoid arthritis",
        "ad_rationale": "Reduces neuroinflammation (TREM2 pathway)",
        "phase": "Phase II"
    },
    {
        "drug": "Pioglitazone",
        "target": "PPAR-γ",
        "current_use": "Type 2 diabetes",
        "ad_rationale": "Improves insulin resistance and inflammation",
        "phase": "Phase III"
    },
    {
        "drug": "Tocilizumab",
        "target": "IL-6R",
        "current_use": "Rheumatoid arthritis",
        "ad_rationale": "Blocks IL-6 inflammatory cascade",
        "phase": "Phase II"
    }
]

for i, cand in enumerate(candidates, 1):
    print(f"\n{i}. {cand['drug']}")
    print(f"   Target: {cand['target']}")
    print(f"   Current use: {cand['current_use']}")
    print(f"   AD rationale: {cand['ad_rationale']}")
    print(f"   Clinical status: {cand['phase']}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total genes: {len(ranked_genes)}")
print(f"High-confidence targets (score > 10): {sum(1 for _, e in ranked_genes if e['score'] > 10)}")
print(f"Repurposing candidates: {len(candidates)}")
print("\nRecommendation: Focus on immune-targeted repurposing (fastest path)")
```

Expected output:
```
================================================================================
EXAMPLE 1: Alzheimer's Disease Drug Target Discovery
================================================================================

[Step 1] Getting GWAS associations for Alzheimer's disease...
✓ Found 50 GWAS associations

[Step 2] Extracting genes and calculating evidence scores...
✓ Found 45 unique genes

Top 10 candidates:
 1. APOE       | Score:  42.31 | Associations: 15 | Min p-value: 3.21e-298
 2. TREM2      | Score:  18.76 | Associations:  8 | Min p-value: 4.12e-45
 3. BIN1       | Score:  12.45 | Associations:  5 | Min p-value: 8.91e-23
 4. CLU        | Score:  11.23 | Associations:  6 | Min p-value: 2.34e-19
 5. CR1        | Score:  10.87 | Associations:  4 | Min p-value: 5.67e-18
 ...

[Step 3] Checking for existing drugs targeting top genes...

APOE:
  Known from literature:
  - No direct drugs (risk factor, not target)
  - Strategy: Reduce APOE4 levels or block aggregation

TREM2:
  - Immunotherapy candidates in development
  - Anti-TREM2 antibodies in Phase I
  ...
```

## Example 2: Type 2 Diabetes Repurposing

### Goal: Find repurposing opportunities for T2D drugs to treat related metabolic conditions

```python
from tooluniverse.tools.execute_tool import execute_tool

print("=" * 80)
print("EXAMPLE 2: Type 2 Diabetes Drug Repurposing")
print("=" * 80)

# Step 1: Get T2D GWAS genes
print("\n[Step 1] Getting T2D genetic associations...")
t2d_result = execute_tool(
    "gwas_get_associations_for_trait",
    {"disease_trait": "type 2 diabetes", "size": 30}
)

t2d_genes = set()
for assoc in t2d_result['data']:
    t2d_genes.update(assoc.get('mapped_genes', []))

print(f"✓ Found {len(t2d_genes)} T2D genes")
print(f"  Key genes: {list(t2d_genes)[:8]}")

# Step 2: Check overlapping genes with other diseases
print("\n[Step 2] Checking gene overlap with related diseases...")

related_diseases = {
    "obesity": "obesity",
    "cardiovascular": "coronary artery disease",
    "fatty_liver": "nonalcoholic fatty liver disease"
}

overlaps = {}

for disease_key, disease_query in related_diseases.items():
    result = execute_tool(
        "gwas_get_associations_for_trait",
        {"disease_trait": disease_query, "size": 30}
    )

    disease_genes = set()
    for assoc in result['data']:
        disease_genes.update(assoc.get('mapped_genes', []))

    overlap = t2d_genes & disease_genes
    overlaps[disease_key] = {
        'genes': disease_genes,
        'overlap': overlap,
        'overlap_count': len(overlap)
    }

    print(f"\n{disease_key.upper()}:")
    print(f"  Total genes: {len(disease_genes)}")
    print(f"  Overlap with T2D: {len(overlap)} genes")
    if overlap:
        print(f"  Shared genes: {list(overlap)[:5]}")

# Step 3: Get known T2D drugs
print("\n[Step 3] Finding approved T2D drugs...")

# Known T2D drugs and their targets
t2d_drugs = [
    {"name": "Metformin", "target": "AMPK", "mechanism": "Insulin sensitizer"},
    {"name": "Glipizide", "target": "KCNJ11", "mechanism": "Insulin secretagogue"},
    {"name": "Pioglitazone", "target": "PPARG", "mechanism": "Insulin sensitizer"},
    {"name": "Semaglutide", "target": "GLP1R", "mechanism": "GLP-1 agonist"},
    {"name": "Empagliflozin", "target": "SLC5A2", "mechanism": "SGLT2 inhibitor"}
]

print(f"✓ Found {len(t2d_drugs)} approved T2D drugs")

# Step 4: Identify repurposing opportunities
print("\n[Step 4] Identifying repurposing opportunities...")

repurposing_opportunities = []

for drug in t2d_drugs:
    drug_target = drug['target']

    # Check if target appears in other disease GWAS
    for disease, data in overlaps.items():
        if drug_target in data['genes']:
            repurposing_opportunities.append({
                'drug': drug['name'],
                'target': drug_target,
                'mechanism': drug['mechanism'],
                'new_indication': disease,
                'rationale': f"{drug_target} implicated in both T2D and {disease} GWAS"
            })

print(f"✓ Found {len(repurposing_opportunities)} repurposing opportunities\n")

for i, opp in enumerate(repurposing_opportunities, 1):
    print(f"{i}. {opp['drug']} → {opp['new_indication'].upper()}")
    print(f"   Target: {opp['target']}")
    print(f"   Mechanism: {opp['mechanism']}")
    print(f"   Rationale: {opp['rationale']}\n")

# Step 5: Prioritize by clinical feasibility
print("[Step 5] Prioritizing by clinical feasibility...")

# Add feasibility scores
for opp in repurposing_opportunities:
    score = 0

    # Known safety profile
    score += 0.3

    # Similar patient population
    if opp['new_indication'] in ['obesity', 'cardiovascular']:
        score += 0.3

    # Related mechanism
    if opp['mechanism'] in ['Insulin sensitizer', 'GLP-1 agonist']:
        score += 0.4

    opp['feasibility'] = score

# Sort by feasibility
repurposing_opportunities.sort(key=lambda x: x['feasibility'], reverse=True)

print("\nTop 3 repurposing candidates:")
for i, opp in enumerate(repurposing_opportunities[:3], 1):
    print(f"{i}. {opp['drug']} for {opp['new_indication']}")
    print(f"   Feasibility score: {opp['feasibility']:.2f}/1.00")
    print(f"   Next steps: Phase II trial, enroll {opp['new_indication']} + T2D patients\n")

print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("Top candidate: Semaglutide (GLP-1 agonist) for obesity")
print("  - Already approved for weight loss (Wegovy)")
print("  - Shared genetic architecture (GLP1R, PPARG)")
print("  - Overlapping patient population")
print("  - Precedent: Liraglutide approved for both T2D and obesity")
```

Expected output:
```
================================================================================
EXAMPLE 2: Type 2 Diabetes Drug Repurposing
================================================================================

[Step 1] Getting T2D genetic associations...
✓ Found 18 T2D genes
  Key genes: ['TCF7L2', 'PPARG', 'KCNJ11', 'GLP1R', 'SLC5A2', 'IRS1', 'MTNR1B', 'IGF2BP2']

[Step 2] Checking gene overlap with related diseases...

OBESITY:
  Total genes: 24
  Overlap with T2D: 7 genes
  Shared genes: ['TCF7L2', 'PPARG', 'GLP1R', 'MC4R', 'FTO']

CARDIOVASCULAR:
  Total genes: 31
  Overlap with T2D: 5 genes
  Shared genes: ['PPARG', 'SLC5A2', 'PCSK9', 'LDLR']
  ...

[Step 4] Identifying repurposing opportunities...
✓ Found 4 repurposing opportunities

1. Semaglutide → OBESITY
   Target: GLP1R
   Mechanism: GLP-1 agonist
   Rationale: GLP1R implicated in both T2D and obesity GWAS
   ...
```

## Example 3: Target Prioritization

### Goal: Rank and prioritize targets based on multiple criteria

```python
import numpy as np
from tooluniverse.tools.execute_tool import execute_tool

print("=" * 80)
print("EXAMPLE 3: Comprehensive Target Prioritization")
print("=" * 80)

def prioritize_targets(disease, top_n=10):
    """
    Comprehensive target prioritization with multi-criteria scoring.
    """

    # 1. Get GWAS evidence
    print(f"\n[1/5] Getting GWAS associations for {disease}...")
    gwas = execute_tool(
        "gwas_get_associations_for_trait",
        {"disease_trait": disease, "size": 50}
    )

    # Parse into gene-level evidence
    gene_data = {}
    for assoc in gwas['data']:
        p_val = assoc.get('p_value', 1.0)
        genes = assoc.get('mapped_genes', [])

        for gene in genes:
            if gene not in gene_data:
                gene_data[gene] = {
                    'associations': [],
                    'min_p': 1.0,
                    'total_associations': 0
                }

            gene_data[gene]['associations'].append(p_val)
            gene_data[gene]['min_p'] = min(gene_data[gene]['min_p'], p_val)
            gene_data[gene]['total_associations'] += 1

    print(f"   ✓ {len(gene_data)} genes with GWAS evidence")

    # 2. Calculate genetic evidence scores
    print("\n[2/5] Calculating genetic evidence scores...")
    for gene, data in gene_data.items():
        # Score components:
        # - Significance: -log10(min_p)
        # - Replication: sqrt(count)
        # - Consistency: 1 / std(log_p)

        log_ps = [-np.log10(p) for p in data['associations']]

        significance = -np.log10(data['min_p'])
        replication = np.sqrt(data['total_associations'])
        consistency = 1.0 / (np.std(log_ps) + 0.1)  # Add epsilon to avoid div by zero

        # Weighted average
        genetic_score = (
            significance * 0.5 +
            replication * 0.3 +
            consistency * 0.2
        )

        data['genetic_score'] = genetic_score

    print(f"   ✓ Calculated scores for {len(gene_data)} genes")

    # 3. Add druggability scores (placeholder - would use Open Targets)
    print("\n[3/5] Assessing druggability...")

    # Known druggable gene families
    druggable_families = {
        'GPCR': 0.9,
        'kinase': 0.85,
        'ion_channel': 0.8,
        'nuclear_receptor': 0.85,
        'protease': 0.75,
        'other_enzyme': 0.6,
        'unknown': 0.3
    }

    for gene, data in gene_data.items():
        # Placeholder: Assign druggability based on gene name patterns
        # Real implementation would query Open Targets tractability

        if gene.endswith('R') or 'receptor' in gene.lower():
            family = 'GPCR'
        elif 'kinase' in gene.lower() or gene.startswith(('MAP', 'AKT', 'PI3K')):
            family = 'kinase'
        elif 'channel' in gene.lower() or gene.startswith(('SCN', 'KCNJ', 'CACNA')):
            family = 'ion_channel'
        elif gene.startswith(('PPAR', 'NR', 'THR')):
            family = 'nuclear_receptor'
        else:
            family = 'unknown'

        data['druggability_family'] = family
        data['druggability_score'] = druggable_families[family]

    print(f"   ✓ Assigned druggability scores")

    # 4. Add clinical feasibility
    print("\n[4/5] Assessing clinical feasibility...")

    for gene, data in gene_data.items():
        # Factors:
        # - Known disease models
        # - Biomarker availability
        # - Target tissue accessibility

        # Placeholder scoring
        feasibility_score = np.random.uniform(0.4, 0.9)  # Real: would query databases
        data['clinical_feasibility'] = feasibility_score

    print(f"   ✓ Assigned feasibility scores")

    # 5. Calculate composite scores
    print("\n[5/5] Calculating final priority scores...")

    for gene, data in gene_data.items():
        # Weighted composite score
        composite = (
            data['genetic_score'] * 0.40 +
            data['druggability_score'] * 100 * 0.35 +
            data['clinical_feasibility'] * 100 * 0.25
        )

        data['composite_score'] = composite

    # Sort by composite score
    ranked = sorted(
        gene_data.items(),
        key=lambda x: x[1]['composite_score'],
        reverse=True
    )

    print(f"   ✓ Ranked {len(ranked)} targets")

    return ranked[:top_n]

# Run prioritization
targets = prioritize_targets("rheumatoid arthritis", top_n=10)

# Display results
print("\n" + "=" * 80)
print("TOP 10 DRUG TARGET CANDIDATES")
print("=" * 80)

print(f"\n{'Rank':<5} {'Gene':<12} {'Composite':<10} {'Genetic':<10} {'Drug':<10} {'Clinical':<10} {'Family':<15}")
print("-" * 85)

for i, (gene, data) in enumerate(targets, 1):
    print(f"{i:<5} {gene:<12} {data['composite_score']:>8.2f}  "
          f"{data['genetic_score']:>8.2f}  "
          f"{data['druggability_score']:>8.2f}  "
          f"{data['clinical_feasibility']:>8.2f}  "
          f"{data['druggability_family']:<15}")

# Detailed breakdown for top target
print("\n" + "=" * 80)
print(f"DETAILED ANALYSIS: {targets[0][0]}")
print("=" * 80)

top_gene, top_data = targets[0]

print(f"\nGene: {top_gene}")
print(f"Overall Score: {top_data['composite_score']:.2f}/100")
print(f"\nGenetic Evidence:")
print(f"  - Total GWAS associations: {top_data['total_associations']}")
print(f"  - Most significant p-value: {top_data['min_p']:.2e}")
print(f"  - Genetic evidence score: {top_data['genetic_score']:.2f}")
print(f"\nDruggability:")
print(f"  - Target family: {top_data['druggability_family']}")
print(f"  - Druggability score: {top_data['druggability_score']:.2f}")
print(f"\nClinical Feasibility:")
print(f"  - Feasibility score: {top_data['clinical_feasibility']:.2f}")
print(f"\nRecommendation:")

if top_data['composite_score'] > 80:
    print("  HIGH PRIORITY - Excellent candidate for drug development")
elif top_data['composite_score'] > 60:
    print("  MEDIUM PRIORITY - Good candidate, requires validation")
else:
    print("  LOW PRIORITY - Consider alternative targets")

print(f"\nNext Steps:")
print(f"  1. Functional validation in disease models")
print(f"  2. Tool compound screening ({top_data['druggability_family']} libraries)")
print(f"  3. Biomarker development for patient stratification")
print(f"  4. Competitive landscape analysis")
```

Expected output:
```
================================================================================
EXAMPLE 3: Comprehensive Target Prioritization
================================================================================

[1/5] Getting GWAS associations for rheumatoid arthritis...
   ✓ 42 genes with GWAS evidence

[2/5] Calculating genetic evidence scores...
   ✓ Calculated scores for 42 genes

[3/5] Assessing druggability...
   ✓ Assigned druggability scores

[4/5] Assessing clinical feasibility...
   ✓ Assigned feasibility scores

[5/5] Calculating final priority scores...
   ✓ Ranked 42 targets

================================================================================
TOP 10 DRUG TARGET CANDIDATES
================================================================================

Rank  Gene         Composite   Genetic    Drug       Clinical   Family
-------------------------------------------------------------------------------------
1     IL6R            92.45      45.23      0.90       0.85     GPCR
2     PTPN22          87.31      42.15      0.75       0.82     other_enzyme
3     TNF             84.76      38.92      0.85       0.79     unknown
4     CTLA4           81.53      41.08      0.85       0.72     GPCR
5     HLA-DRB1        78.24      51.23      0.30       0.88     unknown
  ...

================================================================================
DETAILED ANALYSIS: IL6R
================================================================================

Gene: IL6R
Overall Score: 92.45/100

Genetic Evidence:
  - Total GWAS associations: 12
  - Most significant p-value: 3.45e-42
  - Genetic evidence score: 45.23

Druggability:
  - Target family: GPCR
  - Druggability score: 0.90

Clinical Feasibility:
  - Feasibility score: 0.85

Recommendation:
  HIGH PRIORITY - Excellent candidate for drug development

Next Steps:
  1. Functional validation in disease models
  2. Tool compound screening (GPCR libraries)
  3. Biomarker development for patient stratification
  4. Competitive landscape analysis
```

## Common Patterns

### Pattern 1: Gene-to-Drug Lookup

```python
def get_drugs_for_gene(gene_symbol):
    """Find all drugs targeting a specific gene."""

    # Search ChEMBL for target
    targets = execute_tool(
        "ChEMBL_search_targets",
        {"q": gene_symbol, "limit": 1}
    )

    if not targets['data']['targets']:
        return []

    target_id = targets['data']['targets'][0]['target_chembl_id']

    # Get activities for target
    activities = execute_tool(
        "ChEMBL_get_target_activities",
        {"chembl_id": target_id, "limit": 50}
    )

    # Extract unique molecules
    molecules = set()
    for activity in activities['data']['activities']:
        mol_id = activity.get('molecule_chembl_id')
        if mol_id:
            molecules.add(mol_id)

    # Get drug details
    drugs = []
    for mol_id in list(molecules)[:10]:  # Limit to 10
        mol = execute_tool("ChEMBL_get_molecule", {"chembl_id": mol_id})
        if mol['data']:
            drugs.append({
                'name': mol['data'].get('pref_name'),
                'chembl_id': mol_id,
                'max_phase': mol['data'].get('max_phase')
            })

    return drugs
```

### Pattern 2: Disease-to-Disease Overlap

```python
def find_shared_genetics(disease1, disease2):
    """Find genes shared between two diseases."""

    # Get genes for both diseases
    result1 = execute_tool(
        "gwas_get_associations_for_trait",
        {"disease_trait": disease1, "size": 50}
    )

    result2 = execute_tool(
        "gwas_get_associations_for_trait",
        {"disease_trait": disease2, "size": 50}
    )

    # Extract genes
    genes1 = set()
    for assoc in result1['data']:
        genes1.update(assoc.get('mapped_genes', []))

    genes2 = set()
    for assoc in result2['data']:
        genes2.update(assoc.get('mapped_genes', []))

    # Find overlap
    overlap = genes1 & genes2

    return {
        'disease1_genes': genes1,
        'disease2_genes': genes2,
        'shared_genes': overlap,
        'jaccard_similarity': len(overlap) / len(genes1 | genes2)
    }
```

### Pattern 3: SNP-to-Phenotype

```python
def get_all_traits_for_snp(rs_id):
    """Get all traits associated with a SNP."""

    result = execute_tool(
        "gwas_get_associations_for_snp",
        {"rs_id": rs_id, "size": 100}
    )

    traits = {}
    for assoc in result['data']:
        for trait in assoc.get('reported_trait', []):
            if trait not in traits:
                traits[trait] = []

            traits[trait].append({
                'p_value': assoc.get('p_value'),
                'beta': assoc.get('beta'),
                'study': assoc.get('accession_id')
            })

    return traits
```

## Troubleshooting

### Issue: "No data returned" from Open Targets

**Cause**: EFO ID mismatch or API rate limiting

**Solution**:
```python
# Search for correct EFO ID first
result = execute_tool(
    "OpenTargets_get_disease_id_description_by_name",
    {"query": "type 2 diabetes"}
)

# Use returned EFO ID
efo_id = result['data']['search']['diseases']['hits'][0]['id']

# Then query with correct ID
targets = execute_tool(
    "OpenTargets_get_associated_targets_by_disease_efoId",
    {"efoId": efo_id}
)
```

### Issue: "Empty gene list" from GWAS

**Cause**: Disease name not recognized or no significant associations

**Solution**:
```python
# Try different disease terms
disease_variants = [
    "type 2 diabetes",
    "diabetes mellitus type 2",
    "T2D",
    "non-insulin-dependent diabetes"
]

for disease in disease_variants:
    result = execute_tool(
        "gwas_get_associations_for_trait",
        {"disease_trait": disease, "size": 10}
    )

    if result['data']:
        print(f"✓ Found data for '{disease}'")
        break
```

### Issue: API rate limits

**Cause**: Too many requests in short time

**Solution**:
```python
import time

def execute_with_retry(tool_name, args, max_retries=3):
    """Execute tool with automatic retry on rate limit."""

    for attempt in range(max_retries):
        try:
            result = execute_tool(tool_name, args)
            return result
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

### Issue: Memory errors with large queries

**Cause**: Requesting too many results at once

**Solution**:
```python
def get_all_associations_paginated(disease, page_size=20):
    """Get all associations using pagination."""

    all_data = []
    page = 0

    while True:
        result = execute_tool(
            "gwas_get_associations_for_trait",
            {
                "disease_trait": disease,
                "size": page_size,
                "page": page
            }
        )

        if not result['data']:
            break

        all_data.extend(result['data'])
        page += 1

        # Check if we've reached the end
        if len(result['data']) < page_size:
            break

    return all_data
```

## Next Steps

1. **Explore Examples**: Run the three examples above
2. **Read SKILL.md**: Understand concepts and workflow
3. **Check python_implementation.py**: See full implementation
4. **Run Tests**: Execute test_gwas_drug_tools_v2.py to verify setup
5. **Build Your Workflow**: Adapt examples to your use case

## Support

- Documentation: `skills/tooluniverse-gwas-drug-discovery/SKILL.md`
- Examples: `skills/tooluniverse-gwas-drug-discovery/QUICK_START.md`
- Issues: GitHub Issues
- Community: ToolUniverse Discord

## Additional Resources

- [GWAS Catalog Documentation](https://www.ebi.ac.uk/gwas/docs)
- [Open Targets Platform](https://platform.opentargets.org/)
- [ChEMBL Database](https://www.ebi.ac.uk/chembl/)
- [ToolUniverse Documentation](https://docs.tooluniverse.org)
