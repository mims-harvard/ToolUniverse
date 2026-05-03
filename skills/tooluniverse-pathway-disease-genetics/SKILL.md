---
name: tooluniverse-pathway-disease-genetics
description: Connect GWAS variants to biological pathways for drug target discovery. Maps disease-associated SNPs to causal genes via eQTL colocalization (GTEx), links genes to enriched pathways (Reactome, KEGG, MetaCyc), and identifies druggable targets within disease-relevant pathways. Use when asked to translate GWAS findings into mechanistic insights, find pathways enriched for disease genes, discover drug targets from genetic evidence, or answer questions like "What pathways are disrupted in type 2 diabetes based on GWAS data?"
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Pathway-Disease Genetics: GWAS to Drug Targets via Pathways

Connect genome-wide association study (GWAS) variants to biological pathways for mechanistic understanding and drug target discovery.

## When to Use

- "What pathways are disrupted in [disease] based on GWAS?"
- "Which GWAS genes for [trait] are in druggable pathways?"
- "Map [SNP/variant] to its causal gene and pathway"
- "Find drug targets from GWAS data for [disease]"
- "What is the eQTL evidence for [gene] in [tissue]?"

---

## Core Reasoning Principles

### Gene-to-Pathway Reasoning

A gene found in GWAS doesn't tell you which pathway is dysregulated. To connect gene -> pathway -> disease mechanism, ask: what biological process does this gene participate in? Use Reactome/KEGG to find pathways, then ask: which of these pathways is relevant to the disease phenotype?

For example, TCF7L2 is the strongest T2D GWAS gene. It participates in the Wnt signaling pathway. The question is then: how does disrupted Wnt signaling impair beta-cell function or insulin secretion? That reasoning step — from pathway membership to disease mechanism — requires combining pathway data with tissue expression (GTEx) and disease biology.

Non-coding GWAS variants (the majority) rarely affect the nearest gene. They act through regulatory elements that alter expression of genes sometimes hundreds of kilobases away. Always check eQTL evidence before assuming the nearest gene is causal.

### Pathway Convergence

Multiple disease genes mapping to the same pathway is stronger evidence than a single gene. If 5 GWAS hits for a disease all map to the NF-kB pathway, that is strong mechanistic evidence — the pathway is likely causal, not just coincidentally hit. If GWAS genes scatter across unrelated pathways, the mechanism is unclear, and you may need to look at upstream regulators or gene network hubs that connect the scattered genes.

When running enrichment (Reactome, KEGG, STRING), prioritize pathways that appear across multiple databases. A pathway enriched in all three is more reliable than one that appears in only one analysis.

### Druggability Reasoning

A pathway with existing drugs targeting its components is more actionable than a novel pathway. Before proposing a target as novel, check: are any pathway members already drug targets? Use DGIdb and OpenTargets to survey approved and clinical-stage drugs in the pathway.

Priorities: (1) approved drug for a different indication hitting a GWAS-supported target = strong repurposing opportunity; (2) drug in clinical trials hitting a GWAS-supported target = accelerated validation path; (3) druggable gene with no existing drugs + strong GWAS evidence = novel target opportunity.

"Undruggable" by current modalities does not mean permanently undruggable. Flag such genes but do not dismiss them — they may be actionable via gene therapy, RNA therapeutics, or downstream pathway intervention.

---

## Tool Selection Guide

### Phase 1: Disease Resolution and GWAS Collection

Resolve disease name to ontology ID first:
- `OpenTargets_multi_entity_search_by_query_string(queryString=<disease>)` — returns EFO/MONDO IDs

Collect GWAS signals:
- `gwas_search_associations(query=<disease>)` — broad search
- `gwas_get_variants_for_trait(trait=<trait>, p_value_threshold=5e-8)` — genome-wide significant hits
- `gwas_get_snps_for_gene(gene_symbol=<gene>)` — gene-centric search

**Gotcha:** `gwas_get_associations_for_trait` is broken — use `gwas_search_associations` instead. `gwas_get_snps_for_gene` uses `gene_symbol`, not `mapped_gene`.

### Phase 2: Variant Annotation and eQTL Evidence

Annotate variants:
- `EnsemblVEP_annotate_rsid(variant_id=<rsid>)` — functional consequence, nearest gene
- Response format is variable: list, `{data, metadata}`, or `{error}` — handle all three

Query eQTL evidence in tissue relevant to the disease (e.g., pancreas for T2D, brain for neurological):
- `GTEx_query_eqtl(gene_input=<gene>, tissue=<tissue>)` — never pass empty `gene_input`
- `GTEx_get_expression_summary(gene_input=<gene>)` — expression across all tissues
- `GTEx_get_median_gene_expression(gencode_id=[<versioned_id>], tissue_site_detail_id=[<tissue>])` — use versioned Ensembl IDs (e.g., `ENSG00000148737.11`) and `gtex_v8`

### Phase 3: Pathway Enrichment

Run enrichment across multiple databases and cross-validate results:

- `ReactomeAnalysis_pathway_enrichment(identifiers="P04637 P38398 ...")` — space-separated UniProt STRING, not an array
- `Reactome_map_uniprot_to_pathways(uniprot_id=<id>)` — per-gene pathway membership
- `Reactome_get_participants(pathway_id=<R-HSA-XXXXX>)` — all genes in a pathway
- `KEGG_get_gene_pathways(gene_id=<kegg_id>)` — KEGG pathways for one gene
- `kegg_search_pathway(query=<disease_or_process>)` — keyword search
- `STRING_functional_enrichment(protein_ids=[<genes>], species=9606)` — GO/KEGG/Reactome with FDR
- `PANTHER_enrichment(gene_list="GENE1,GENE2,...", organism=9606, annotation_dataset="GO:0008150")` — comma-separated STRING, not array

**MetaCyc note:** Currently unavailable (BioCyc requires authentication). Use KEGG or Reactome for metabolic pathways.

### Phase 4: Druggability and Drug Landscape

- `DGIdb_get_gene_druggability(genes=[<gene_list>])` — categories: clinically actionable, druggable, etc.
- `DGIdb_get_drug_gene_interactions(genes=[<gene_list>])` — use `genes` param (array), not `gene_name`
- `OpenTargets_get_associated_drugs_by_target_ensemblID(ensemblId=<id>)` — approved and clinical drugs
- `OpenTargets_target_disease_evidence(ensemblId=<id>, efoId=<disease_id>)` — genetic + other evidence score

---

## Three-Step Workflow

### Step 1: GWAS to Causal Gene

1. Resolve disease ID via `OpenTargets_multi_entity_search_by_query_string`
2. Pull GWAS hits with `gwas_get_variants_for_trait` (p < 5e-8)
3. Annotate each lead SNP with VEP — is it coding or non-coding?
4. For non-coding variants, check eQTL via GTEx in the disease-relevant tissue
5. Prioritize genes where: GWAS SNP is also a significant eQTL AND the tissue is biologically relevant to the disease
6. Cross-check with `OpenTargets_target_disease_evidence` for additional genetic evidence

Evidence tiers: **High** = GWAS p < 5e-8 + eQTL colocalization in relevant tissue + coding variant; **Medium** = GWAS p < 5e-8 + eQTL in any tissue; **Low** = GWAS p < 5e-8 + positional mapping only.

### Step 2: Gene Set to Pathway Enrichment

1. Collect prioritized gene list from Step 1
2. Run `ReactomeAnalysis_pathway_enrichment` and `STRING_functional_enrichment`
3. Map each gene to KEGG pathways via `KEGG_get_gene_pathways`
4. Identify pathways appearing across multiple databases (convergence = stronger evidence)
5. For metabolic diseases, add tissue-specific network context via `humanbase_ppi_analysis` (all 5 params required: `gene_list`, `tissue`, `max_node`, `interaction`, `string_mode`)
6. Rank pathways by enrichment FDR x number of GWAS genes x biological plausibility

### Step 3: Pathway to Drug Target

1. From enriched pathways, extract all member genes via `Reactome_get_participants` and `KEGG_get_pathway_genes`
2. Assess druggability via `DGIdb_get_gene_druggability`
3. Look up existing drugs via `OpenTargets_get_associated_drugs_by_target_ensemblID`
4. Cross-reference pathway genes with GWAS genes: overlap = top candidate
5. Classify each candidate: repurposing opportunity / novel target / undruggable (for now)

Final ranking: Genetic Evidence x Druggability x Pathway Centrality. Flag novel targets (strong genetic + no existing drugs) and repurposing opportunities (approved drug + genetic support in this disease).

---

## Key Parameter Gotchas

- `gwas_get_snps_for_gene`: use `gene_symbol`, not `mapped_gene`
- `OpenTargets_multi_entity_search_by_query_string`: use `queryString`, not `query`
- `GTEx_query_eqtl`: `gene_input` must never be empty
- `GTEx_get_median_gene_expression`: use versioned gencode IDs; use `gtex_v8`
- `ReactomeAnalysis_pathway_enrichment`: `identifiers` is space-separated STRING, not array
- `DGIdb_get_drug_gene_interactions`: use `genes` (array), not `gene_name`
- `PANTHER_enrichment`: `gene_list` is comma-separated STRING, not array
- `humanbase_ppi_analysis`: all 5 params required
- `EnsemblVEP_annotate_rsid`: use `variant_id`, not `rsid`
- `kegg_find_genes`: include `organism="hsa"` for human genes

---

## Limitations

- GTEx eQTL lookup is not formal statistical colocalization (coloc/ENLOC) — treat as suggestive evidence
- GWAS Catalog may not include recent publications; cross-check with Open Targets
- Reactome and KEGG define pathways differently; some biology is in one but not the other
- DGIdb druggability categories are heuristic — "undruggable" applies only to current modalities
- eQTLs are tissue-specific; querying the wrong tissue may miss causal effects

---

## Related Skills

- **tooluniverse-gwas-trait-to-gene**: Focused GWAS-to-gene mapping
- **tooluniverse-gene-enrichment**: Detailed enrichment analysis
- **tooluniverse-drug-target-validation**: Deep target validation
- **tooluniverse-network-pharmacology**: Network-level drug analysis
- **tooluniverse-variant-functional-annotation**: Detailed variant interpretation
