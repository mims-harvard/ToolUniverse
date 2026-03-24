---
name: tooluniverse-pathway-disease-genetics
description: Connect GWAS variants to biological pathways for drug target discovery. Maps disease-associated SNPs to causal genes via eQTL colocalization (GTEx), links genes to enriched pathways (Reactome, KEGG, MetaCyc), and identifies druggable targets within disease-relevant pathways. Use when asked to translate GWAS findings into mechanistic insights, find pathways enriched for disease genes, discover drug targets from genetic evidence, or answer questions like "What pathways are disrupted in type 2 diabetes based on GWAS data?"
---

# Pathway-Disease Genetics: GWAS to Drug Targets via Pathways

Connect genome-wide association study (GWAS) variants to biological pathways for mechanistic understanding and drug target discovery.

## When to Use

Apply when user asks:
- "What pathways are disrupted in [disease] based on GWAS?"
- "Which GWAS genes for [trait] are in druggable pathways?"
- "Map [SNP/variant] to its causal gene and pathway"
- "Find drug targets from GWAS data for [disease]"
- "What is the eQTL evidence for [gene] in [tissue]?"
- "Which pathways are enriched for [disease] risk genes?"

---

## Tool Inventory (Verified Names)

### GWAS Catalog Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `gwas_search_associations` | Search GWAS associations by keyword | `query` |
| `gwas_get_variants_for_trait` | Get variants for a trait | `trait`, `p_value_threshold` (optional) |
| `gwas_get_snps_for_gene` | Get SNPs mapped to a gene | `gene_symbol` (NOT `mapped_gene`) |
| `gwas_search_snps` | Search SNPs by various criteria | `query` |

**GWAS tool notes:**
- `gwas_get_associations_for_trait`: BROKEN -- use `gwas_search_associations(query=trait)` instead
- `gwas_get_variants_for_trait` now accepts `p_value_threshold` for server-side filtering
- Client-side p-value filtering is also applied when the API returns unfiltered results
- Response: `{data: [{...}], metadata: {...}}`

### Open Targets Genetics
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `OpenTargets_search_gwas_studies_by_disease` | Search GWAS studies for a disease | `efoId`, `pageSize` |
| `OpenTargets_target_disease_evidence` | Evidence linking target to disease | `ensemblId`, `efoId` |
| `OpenTargets_get_associated_targets_by_disease_efoId` | Top gene targets for disease | `efoId`, `size` |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | Drugs targeting a gene | `ensemblId`, `size` |
| `OpenTargets_multi_entity_search_by_query_string` | Search for disease/gene/drug | `queryString` (NOT `query`) |

**Open Targets notes:**
- Disease IDs: Use EFO/MONDO format (e.g., `MONDO_0005148` for T2D, NOT `EFO_0001360`)
- Gene IDs: Use Ensembl format (e.g., `ENSG00000148737` for TCF7L2)
- `OpenTargets_multi_entity_search_by_query_string` resolves names to IDs

### GTEx eQTL Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `GTEx_query_eqtl` | Query eQTLs for gene/variant/tissue | `gene_input`, `tissue`, `variant_id` |
| `GTEx_get_expression_summary` | Gene expression across tissues | `gene_input` |
| `GTEx_get_median_gene_expression` | Median expression by tissue | `gencode_id` (VERSIONED, array), `tissue_site_detail_id` (array) |

**GTEx notes:**
- All GTEx tools are SOAP-style, require `operation` parameter
- Use `gencode_id` with version (e.g., `ENSG00000148737.11`)
- `tissue_site_detail_id` uses specific GTEx tissue names (e.g., `Pancreas`, `Liver`)
- Always use `gtex_v8` (v10 returns empty for medianGeneExpression)
- `gene_input` must not be empty (causes silent API failure)

### Reactome Pathway Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `Reactome_get_pathway` | Get pathway details by stable ID | `pathway_id` (e.g., "R-HSA-70326") |
| `Reactome_get_pathway_reactions` | Reactions in a pathway | `pathway_id` |
| `Reactome_get_pathway_hierarchy` | Pathway hierarchy tree | `species` (e.g., "Homo sapiens") |
| `Reactome_map_uniprot_to_pathways` | UniProt accession to pathways | `uniprot_id` |
| `Reactome_get_participants` | Pathway participants (genes/proteins) | `pathway_id` |
| `Reactome_get_diseases` | Disease annotations for pathway | `pathway_id` |
| `ReactomeAnalysis_pathway_enrichment` | ORA/enrichment analysis | `identifiers` (space-separated STRING, NOT array) |
| `ReactomeContent_search` | Full-text search across Reactome | `query` |
| `ReactomeInteractors_get_protein_interactors` | Protein interactors from Reactome | `uniprot_id` |

**Reactome notes:**
- `ReactomeAnalysis_pathway_enrichment`: `identifiers` is a SPACE-SEPARATED STRING (e.g., "P04637 P38398 Q13315"), NOT an array
- `id` param renamed to `uniprot_id` for clarity in mapping tools

### KEGG Pathway Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `kegg_search_pathway` | Search pathways by keyword | `query` |
| `kegg_get_pathway_info` | Get pathway details | `pathway_id` (e.g., "hsa04930") |
| `KEGG_get_pathway_genes` | Genes in a pathway | `pathway_id` |
| `KEGG_get_gene_pathways` | Pathways for a gene | `gene_id` |
| `kegg_find_genes` | Search genes by keyword | `keyword`, `organism` |
| `KEGG_search_disease` | Search KEGG diseases | `query` |
| `KEGG_get_disease_genes` | Genes for a KEGG disease | `disease_id` |
| `KEGG_link_entries` | Cross-reference between databases | `source_db`, `target_db` |

**KEGG notes:**
- Organism-specific gene search: uses `/find/{organism}/{keyword}` (e.g., organism="hsa" for human)
- `organism` param is silently ignored if not passed correctly; use the `/find/{organism}/{keyword}` format

### MetaCyc Pathway Tools

> **NOTE: MetaCyc tools are currently unavailable.** BioCyc now requires a free account for all API access. Use KEGG or Reactome as alternatives for metabolic pathway analysis.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| ~~`MetaCyc_search_pathways`~~ | ⚠️ UNAVAILABLE (requires BioCyc account) | — |

### Variant Annotation
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EnsemblVEP_annotate_rsid` | Annotate variant by rsID | `variant_id` (NOT `rsid`) |
| `EnsemblVEP_annotate_hgvs` | Annotate variant by HGVS notation | `hgvs_notation` |
| `MyGene_query_genes` | Search genes by symbol/name | `query` (NOT `q`) |
| `MyGene_get_gene_annotation` | Full gene annotation | `gene_id` |

**VEP notes:**
- Variable response format: sometimes list, sometimes `{data, metadata}`, sometimes `{error}`. Handle all three
- Returns SIFT/PolyPhen functional predictions

### Gene-Drug Interaction
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DGIdb_get_drug_gene_interactions` | Drug-gene interactions | `genes` (list of strings, NOT `gene_name`) |
| `DGIdb_get_gene_druggability` | Gene druggability categories | `genes` (array) |
| `DGIdb_get_gene_info` | Gene information from DGIdb | `gene_name` |

**DGIdb notes:**
- Client-side filtering for `interaction_types` and `sources`
- All returns wrapped with `{status, data}` envelope
- `DGIdb_get_gene_druggability` returns `{data: {genes: {nodes: [{name, geneCategories}]}}}`

### Supporting Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `STRING_functional_enrichment` | GO/KEGG/Reactome enrichment for gene set | `protein_ids` (array), `species` (9606) |
| `STRING_get_network` | PPI network for genes | `protein_ids` (array), `species` (9606) |
| `humanbase_ppi_analysis` | Tissue-specific PPI | `gene_list`, `tissue`, `max_node`, `interaction`, `string_mode` (ALL 5 required) |
| `PANTHER_enrichment` | GO/pathway enrichment | `gene_list` (comma-separated STRING), `organism` (9606), `annotation_dataset` |

---

## Workflow 1: GWAS to Causal Gene via eQTL Colocalization

```
Phase 0: Disease/Trait Resolution
  -> OpenTargets_multi_entity_search_by_query_string(queryString=<disease_name>)
  -> Get: EFO/MONDO disease ID, standardized name

Phase 1: Collect GWAS Signals
  -> gwas_search_associations(query=<disease_name>)
  -> gwas_get_variants_for_trait(trait=<trait>, p_value_threshold=5e-8)
  -> OpenTargets_search_gwas_studies_by_disease(efoId=<disease_id>)
  -> Collect: lead SNPs, p-values, mapped genes, study IDs

Phase 2: Variant Annotation
  -> For each lead SNP:
     -> EnsemblVEP_annotate_rsid(variant_id=<rsid>)
     -> Get: consequence type, nearest gene, regulatory features
     -> Classify: coding (missense/nonsense) vs non-coding (regulatory/intronic)

Phase 3: eQTL Evidence (GTEx)
  -> For each lead SNP or mapped gene:
     -> GTEx_query_eqtl(gene_input=<gene>, tissue=<relevant_tissue>)
     -> GTEx_get_expression_summary(gene_input=<gene>)
  -> Identify: Which tissue shows strongest eQTL effect?
  -> Colocalization logic:
     - GWAS SNP is also significant eQTL for gene G in tissue T
     - Direction of effect: risk allele increases or decreases expression?
     - Tissue relevance: Is tissue T biologically relevant to disease?

Phase 4: Gene Prioritization
  -> For genes with eQTL support:
     -> OpenTargets_target_disease_evidence(ensemblId=<gene_ensembl>, efoId=<disease_id>)
     -> Score by: GWAS p-value x eQTL significance x tissue relevance
  -> Rank genes by combined evidence score

Phase 5: Gene-to-Target Assessment
  -> DGIdb_get_gene_druggability(genes=[<gene_list>])
  -> DGIdb_get_drug_gene_interactions(genes=[<gene_list>])
  -> OpenTargets_get_associated_drugs_by_target_ensemblID(ensemblId=...)
  -> Classify: druggable (existing drugs), tractable (predicted druggable), undruggable

Phase 6: Summary
  -> Table: Gene | GWAS p-value | eQTL tissue | eQTL p-value | Direction | Druggability
  -> Highlight top causal gene candidates with eQTL + druggability evidence
```

### Evidence Confidence Levels

| Level | Criteria |
|-------|----------|
| **High** | GWAS p < 5e-8 + eQTL colocalizes in disease-relevant tissue + coding variant or L2G > 0.5 |
| **Medium** | GWAS p < 5e-8 + eQTL in any tissue OR multiple independent GWAS signals at locus |
| **Low** | GWAS p < 5e-8 + positional mapping only (nearest gene) |

---

## Workflow 2: Gene Set to Pathway Enrichment

```
Phase 0: Collect Disease Genes
  -> From Workflow 1 output, OR user-provided gene list
  -> MyGene_query_genes(query=<gene>) for each to get Ensembl/Entrez IDs

Phase 1: Reactome Enrichment
  -> For each gene: Reactome_map_uniprot_to_pathways(uniprot_id=...)
  -> Aggregate pathway counts, identify over-represented pathways
  -> ReactomeAnalysis_pathway_enrichment(identifiers="P04637 P38398 ...")
     [space-separated UniProt IDs]

Phase 2: KEGG Pathway Mapping
  -> For each gene: KEGG_get_gene_pathways(gene_id=<kegg_gene_id>)
  -> kegg_search_pathway(query=<disease_name>) for disease-specific pathways
  -> Identify KEGG pathways enriched for GWAS genes

Phase 3: STRING/PANTHER Enrichment
  -> STRING_functional_enrichment(protein_ids=[<gene_symbols>], species=9606)
     [Returns GO terms, KEGG, Reactome with FDR-corrected p-values]
  -> PANTHER_enrichment(gene_list="GENE1,GENE2,...", organism=9606,
     annotation_dataset="GO:0008150")  [GO Biological Process]

Phase 4: Metabolic Pathways (if metabolic disease)
  -> KEGG: kegg_search_pathway(query=<disease_or_process>)
  -> Reactome: ReactomeContent_search(query=<disease_or_process>)
  -> (MetaCyc unavailable — requires BioCyc authentication)

Phase 5: Tissue-Specific Network Context
  -> humanbase_ppi_analysis(gene_list=<genes>, tissue=<relevant_tissue>,
     max_node=20, interaction=0.5, string_mode="default")
  -> Identify hub genes in disease-relevant tissue network

Phase 6: Pathway Summary
  -> Rank pathways by: enrichment p-value x number of GWAS genes x biological relevance
  -> Table: Pathway | Source | p-value | FDR | GWAS Genes | Total Genes
  -> Identify converging pathways across Reactome + KEGG + STRING
```

---

## Workflow 3: Pathway to Drug Target Mapping

```
Phase 0: Select Top Pathways
  -> From Workflow 2, select pathways with FDR < 0.05

Phase 1: Extract Pathway Genes
  -> Reactome_get_participants(pathway_id=...)
  -> KEGG_get_pathway_genes(pathway_id=...)
  -> Merge gene lists, remove duplicates

Phase 2: Druggability Assessment
  -> DGIdb_get_gene_druggability(genes=[<pathway_genes>])
  -> DGIdb_get_drug_gene_interactions(genes=[<pathway_genes>])
  -> Categorize: clinically actionable, druggable, gene therapy candidate, undruggable

Phase 3: Existing Drug Landscape
  -> For druggable genes:
     -> OpenTargets_get_associated_drugs_by_target_ensemblID(ensemblId=..., size=10)
     -> Collect: approved drugs, clinical-phase drugs, mechanism of action

Phase 4: Genetic Evidence Integration
  -> Cross-reference pathway genes with GWAS genes from Workflow 1
  -> Prioritize: pathway gene + GWAS evidence + druggable = top candidate
  -> OpenTargets_target_disease_evidence(ensemblId=..., efoId=...) for each candidate

Phase 5: Network Pharmacology Context
  -> STRING_get_network(protein_ids=[<top_targets>], species=9606)
  -> Identify: network hubs, bottleneck genes, pathway crosstalk points

Phase 6: Drug Target Report
  -> Rank targets by: Genetic Evidence x Druggability x Pathway Centrality
  -> Table: Gene | GWAS p-value | Pathway(s) | Druggability | Existing Drugs | Score
  -> Highlight: novel targets (no existing drugs + strong genetic evidence)
  -> Flag: repurposing opportunities (approved drug for different indication)
```

---

## Tool Parameter Gotchas

| Tool | Common Mistake | Correct Usage |
|------|---------------|---------------|
| `gwas_get_snps_for_gene` | `mapped_gene` param | Use `gene_symbol` |
| `gwas_search_associations` | Complex multi-word queries | Use simpler terms, combine results |
| `OpenTargets_multi_entity_search_by_query_string` | `query` param | Use `queryString` |
| `GTEx_query_eqtl` | Empty `gene_input` | Must provide non-empty value |
| `GTEx_get_median_gene_expression` | Unversioned gencode_id | Use versioned ID (e.g., `ENSG00000148737.11`) |
| `ReactomeAnalysis_pathway_enrichment` | Array of IDs | Use space-separated STRING |
| `DGIdb_get_drug_gene_interactions` | `gene_name` param | Use `genes` (array) |
| `PANTHER_enrichment` | Array of genes | Use comma-separated STRING |
| `humanbase_ppi_analysis` | Missing params | ALL 5 params required |
| `EnsemblVEP_annotate_rsid` | `rsid` param | Use `variant_id` |
| `MyGene_query_genes` | `q` param | Use `query` |
| `kegg_find_genes` | Omitting `organism` | Use `organism="hsa"` for human |

---

## Response Format Notes

| Tool | Response Structure |
|------|-------------------|
| `gwas_search_associations` | `{data: [{...}], metadata: {...}}` |
| `gwas_get_variants_for_trait` | `{data: [{...}], metadata: {...}}` -- now supports `p_value_threshold` |
| `GTEx_query_eqtl` | SOAP-style with `operation` param |
| `STRING_functional_enrichment` | List of enriched terms with FDR |
| `ReactomeAnalysis_pathway_enrichment` | Enrichment results with p-values |
| `DGIdb_get_gene_druggability` | `{data: {genes: {nodes: [{name, geneCategories}]}}}` |
| `EnsemblVEP_annotate_rsid` | Variable: list OR `{data, metadata}` OR `{error}` |
| `PANTHER_enrichment` | `{data: {enriched_terms: [{term_id, term_label, pvalue, fdr, fold_enrichment}]}}` |

---

## Evidence Grading

| Tier | Source | Confidence |
|------|--------|------------|
| T1 | GWAS (p < 5e-8) + eQTL colocalization + pathway enrichment (FDR < 0.01) | Highest |
| T2 | GWAS (p < 5e-8) + pathway membership + druggability evidence | High |
| T3 | GWAS suggestive (p < 1e-5) + pathway enrichment | Medium |
| T4 | Pathway membership only (no direct genetic evidence) | Low |

---

## Completeness Checklist

- [ ] Disease/trait resolved to ontology ID (EFO/MONDO)
- [ ] GWAS associations collected (GWAS Catalog + Open Targets)
- [ ] Lead variants annotated (VEP consequence, nearest gene)
- [ ] eQTL colocalization assessed (GTEx, disease-relevant tissue)
- [ ] Genes prioritized by combined GWAS + eQTL evidence
- [ ] Pathway enrichment performed (Reactome + KEGG + STRING/PANTHER)
- [ ] Converging pathways identified across databases
- [ ] Druggability assessed (DGIdb categories + existing drugs)
- [ ] Existing drug landscape mapped (OpenTargets)
- [ ] Novel targets vs repurposing opportunities identified
- [ ] Evidence tiers assigned (T1-T4)
- [ ] Summary tables generated for genes, pathways, and drug targets

---

## Common Disease ID Reference

| Disease | MONDO ID | EFO ID | Key Pathways |
|---------|----------|--------|--------------|
| Type 2 Diabetes | MONDO_0005148 | -- | Insulin signaling, beta-cell function |
| Coronary Artery Disease | MONDO_0005010 | EFO_0001645 | Lipid metabolism, inflammation |
| Alzheimer's Disease | MONDO_0004975 | EFO_0000249 | Amyloid, tau, neuroinflammation |
| Breast Cancer | MONDO_0007254 | EFO_0000305 | DNA repair, cell cycle, ER signaling |
| Rheumatoid Arthritis | MONDO_0008383 | EFO_0000685 | TNF, IL-6, JAK-STAT |
| Inflammatory Bowel Disease | MONDO_0005265 | EFO_0003767 | Autophagy, barrier function, IL-23 |

---

## Limitations

1. **eQTL colocalization is not formal colocalization analysis**: GTEx eQTL lookup shows whether a variant is an eQTL, but does not perform statistical colocalization (coloc/ENLOC). Interpret as suggestive, not definitive
2. **GWAS Catalog coverage**: Not all published GWAS are curated; recent studies may be missing
3. **Pathway database overlap**: Reactome and KEGG have different pathway definitions; some biology covered in one but not the other
4. **Druggability prediction limitations**: DGIdb categories are heuristic; "undruggable" does not mean the gene cannot be targeted with novel modalities
5. **GTEx tissue specificity**: eQTLs are tissue-specific; querying wrong tissue may miss causal effects
6. **KEGG organism param**: Silently ignored if format is wrong; use organism code like "hsa"

---

## Related Skills

- **tooluniverse-gwas-trait-to-gene**: Focused GWAS-to-gene mapping (complementary Phase 1)
- **tooluniverse-gene-enrichment**: Detailed enrichment analysis (complementary Phase 2)
- **tooluniverse-drug-target-validation**: Deep target validation (complementary Phase 3)
- **tooluniverse-network-pharmacology**: Network-level drug analysis
- **tooluniverse-variant-functional-annotation**: Detailed variant interpretation

---

## References

- **GWAS Catalog**: https://www.ebi.ac.uk/gwas/
- **Open Targets**: https://platform.opentargets.org/
- **GTEx**: https://gtexportal.org/
- **Reactome**: https://reactome.org/
- **KEGG**: https://www.genome.jp/kegg/
- **DGIdb**: https://www.dgidb.org/
- **STRING**: https://string-db.org/
- **PANTHER**: http://pantherdb.org/
