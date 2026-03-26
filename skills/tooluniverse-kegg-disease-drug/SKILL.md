---
name: tooluniverse-kegg-disease-drug
description: >
  KEGG-based disease-drug-variant research using KEGG Disease, Drug, Network, and Variant databases.
  Covers disease gene lookup, drug-target analysis, disease-gene-drug network exploration, and variant
  annotation. Use when users ask about KEGG disease entries, KEGG drug targets, disease-variant-drug
  relationships, or KEGG network analysis.
triggers:
  - keywords: [KEGG disease, KEGG drug, KEGG network, KEGG variant, disease genes, drug targets]
  - patterns: ["KEGG .* disease", "KEGG .* drug", "disease.*drug.*variant", "KEGG network"]
---

# KEGG Disease-Drug-Variant Research

Systematic exploration of disease-drug-variant relationships using KEGG's curated databases.

## When to Use

- "What genes are associated with [disease] in KEGG?"
- "Find KEGG drugs targeting [gene/pathway]"
- "What variants are linked to [disease] in KEGG?"
- "Show the KEGG disease-gene-drug network for [condition]"
- "Find drugs targeting BRAF variants in cancer"

## Tool Inventory (12 tools)

| Tool | Key Params | Returns |
|------|-----------|---------|
| KEGG_search_disease | `keyword` | Disease entries matching keyword |
| KEGG_get_disease | `disease_id` (e.g., "H00004") | Disease details: genes, drugs, pathways |
| KEGG_get_disease_genes | `disease_id` | All genes for a disease |
| KEGG_search_drug | `keyword` | Drug entries matching keyword |
| KEGG_get_drug | `drug_id` (e.g., "D00123") | Drug details: targets, pathways, metabolism |
| KEGG_get_drug_targets | `drug_id` | Molecular targets for a drug |
| KEGG_search_network | `keyword` | Network entries (disease-gene-drug) |
| KEGG_get_network | `network_id` | Network details and relationships |
| KEGG_search_variant | `keyword` | Variant entries matching keyword |
| KEGG_get_variant | `variant_id` | Variant details and disease associations |
| KEGG_convert_ids | `source_db`, `target_db`, `ids` | Convert identifiers between KEGG and external databases (e.g., NCBI Gene ↔ KEGG gene IDs, UniProt ↔ KEGG) |
| KEGG_link_entries | `target_db`, `source_db_or_ids` | Find cross-database relationships (e.g., all genes linked to a pathway, all drugs linked to a disease) |

## Workflow

```
Phase 1: Disease Lookup -> Phase 2: Disease Genes -> Phase 3: Drug Search
  -> Phase 4: Drug Targets -> Phase 5: Network/Variant Context -> Report
```

### Phase 1: Disease Lookup

Search and retrieve KEGG disease entries.

```python
# Search for cancer-related diseases
diseases = tu.tools.KEGG_search_disease(keyword="breast cancer")
# Get details for a specific disease
disease = tu.tools.KEGG_get_disease(disease_id="H00031")
```

### Phase 2: Disease Genes

Get genes associated with a KEGG disease entry.

```python
genes = tu.tools.KEGG_get_disease_genes(disease_id="H00031")
```

### Phase 3: Drug Search

Find KEGG drugs by name, target, or keyword.

```python
drugs = tu.tools.KEGG_search_drug(keyword="vemurafenib")
drug_detail = tu.tools.KEGG_get_drug(drug_id="D09996")
```

### Phase 4: Drug Targets

Get molecular targets for a drug.

```python
targets = tu.tools.KEGG_get_drug_targets(drug_id="D09996")
```

### Phase 5: Network & Variant Context

Explore disease-gene-drug networks and variant annotations.

```python
# Search networks linking disease, genes, and drugs
networks = tu.tools.KEGG_search_network(keyword="BRAF melanoma")
network = tu.tools.KEGG_get_network(network_id="N00001")

# Search and get variant details
variants = tu.tools.KEGG_search_variant(keyword="BRAF V600E")
variant = tu.tools.KEGG_get_variant(variant_id="hsa:BRAF")
```

## Example Workflow: Find Drugs Targeting BRAF Variants in Cancer

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# 1. Find BRAF-related diseases
diseases = tu.tools.KEGG_search_disease(keyword="BRAF")

# 2. Get disease genes for melanoma
genes = tu.tools.KEGG_get_disease_genes(disease_id="H00038")

# 3. Search for BRAF-targeting drugs
drugs = tu.tools.KEGG_search_drug(keyword="BRAF inhibitor")

# 4. Get targets for vemurafenib
targets = tu.tools.KEGG_get_drug_targets(drug_id="D09996")

# 5. Get BRAF variant info
variants = tu.tools.KEGG_search_variant(keyword="BRAF V600E")

# 6. Explore disease-gene-drug network
networks = tu.tools.KEGG_search_network(keyword="BRAF melanoma")
```

## ID Conversion & Cross-Linking

Use `KEGG_convert_ids` to map between KEGG identifiers and external databases before or after lookups:

```python
# Convert NCBI Gene IDs to KEGG gene IDs for human (hsa)
result = tu.tools.KEGG_convert_ids(source_db="ncbi-geneid", target_db="hsa", ids=["672", "675"])

# Convert UniProt accessions to KEGG entries
result = tu.tools.KEGG_convert_ids(source_db="up", target_db="hsa", ids=["P38398"])
```

Use `KEGG_link_entries` to retrieve relationships between KEGG databases:

```python
# Find all KEGG pathway IDs that contain a given gene
result = tu.tools.KEGG_link_entries(target_db="pathway", source_db_or_ids="hsa:7157")

# Find all genes linked to a specific pathway
result = tu.tools.KEGG_link_entries(target_db="hsa", source_db_or_ids="path:hsa05210")
```

These tools are especially useful when you have external IDs (Entrez Gene, UniProt, ChEMBL) and need to bridge into KEGG's namespace, or when you want a complete gene-pathway or drug-disease adjacency list.

## Fallback Strategies

| Phase | If Empty | Fallback |
|-------|----------|----------|
| Disease search | No hits | Broaden keyword, try synonyms |
| Disease genes | No genes | Use kegg_find_genes with disease keyword |
| Drug search | No hits | Try generic name, chemical name |
| Drug targets | No targets | Use kegg_search_pathway for pathway context |
| Network | No entries | Combine disease + drug results manually |
| Variant | No entries | Use kegg_find_genes for gene-level info |
| External ID → KEGG | Unknown KEGG ID | Use KEGG_convert_ids with ncbi-geneid or up (UniProt) |

## Integration with Other Skills

- **Pathway details**: Use `tooluniverse-systems-biology` for Reactome/WikiPathways cross-ref
- **Drug mechanisms**: Use `tooluniverse-drug-mechanism-research` for ChEMBL/DailyMed MOA
- **Clinical variants**: Use `tooluniverse-cancer-variant-interpretation` for CIViC/ClinVar
- **Drug safety**: Use `tooluniverse-adverse-event-detection` for FAERS data

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **Strong** | KEGG disease entry with curated gene list, drug with confirmed target, pathway mechanistically linked | H00031 (breast cancer) with BRCA1/BRCA2 genes, D09996 (vemurafenib) targeting BRAF |
| **Moderate** | Disease-gene link in KEGG but no drug-target validation, or network entry without variant data | KEGG disease entry lists gene, but drug targets are inferred from pathway membership |
| **Weak** | Keyword search hit only, no curated disease-gene-drug relationship in KEGG | Drug found by name search but not linked to the disease in KEGG network |
| **Insufficient** | No KEGG entries found, or only cross-database ID conversion available | Rare disease not curated in KEGG Disease |

### Interpretation Guidance

- **KEGG pathway significance**: KEGG pathways are manually curated maps of molecular interactions. A gene appearing in a KEGG disease pathway has been editorially reviewed as relevant to that disease mechanism. However, KEGG coverage is not exhaustive -- absence from KEGG does not mean absence of involvement. Cross-reference with Reactome or WikiPathways for broader coverage.
- **Disease-drug network interpretation**: KEGG Network entries (N-codes) link diseases, genes, and drugs in mechanistic triangles. A drug targeting a gene in a disease network has a curated rationale for therapeutic relevance. The network structure distinguishes direct targets (drug binds gene product) from pathway-level connections (drug affects pathway containing the gene). Prioritize direct target relationships for drug repurposing hypotheses.
- **Variant impact assessment**: KEGG Variant entries are curated for clinical significance (often cancer driver mutations). A variant listed in KEGG with a linked drug entry indicates an established pharmacogenomic or precision oncology relationship (e.g., BRAF V600E linked to vemurafenib). Variants not in KEGG may still be clinically relevant -- cross-reference with ClinVar and CIViC.
- **ID conversion caveat**: KEGG uses its own gene ID namespace (e.g., hsa:7157 for TP53). Always use `KEGG_convert_ids` to map from external IDs (NCBI Gene, UniProt) before querying KEGG-specific tools. Failed conversions may indicate the gene is not in KEGG's curated set.
- **Drug entry completeness**: KEGG Drug entries vary in detail. Approved drugs typically have full target, pathway, and metabolism information. Investigational compounds may have partial entries. Check the drug's "Target" and "Pathway" fields for completeness before drawing conclusions.

### Synthesis Questions

1. Does the KEGG disease entry list the gene of interest with a direct mechanistic role, or is the gene only peripherally connected through a shared pathway?
2. For drug-target relationships, is the target confirmed by KEGG Network (direct link), or inferred from pathway co-membership?
3. Are there KEGG variant entries linking specific mutations to drug response, supporting precision medicine applications?
4. Does the KEGG disease-gene-drug network for the condition align with evidence from other curated sources (CIViC, OncoKB, DrugBank)?
5. If KEGG has limited entries for the query, which complementary databases (Reactome, WikiPathways, CTD) should be consulted to fill gaps?

---

## Output

Markdown report with:
1. Disease summary (KEGG ID, name, associated genes/pathways)
2. Gene list with KEGG gene IDs and symbols
3. Drug candidates with targets and mechanisms
4. Network relationships (disease-gene-drug triangles)
5. Variant annotations if available
