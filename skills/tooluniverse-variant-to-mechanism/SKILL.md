---
name: tooluniverse-variant-to-mechanism
description: >
  End-to-end variant-to-mechanism analysis: given a genetic variant (rsID or coordinates),
  trace its functional impact from regulatory context (GWAS, eQTL, RegulomeDB, ENCODE) through
  target gene identification (GTEx, OpenTargets L2G) to downstream pathway and disease biology
  (STRING, Reactome, GO enrichment, disease associations). Produces an evidence-graded
  mechanistic narrative linking genotype to phenotype. Use when asked "how does this variant
  cause disease?", "what is the mechanism of rs7903146?", "trace variant to pathway", or
  "connect this GWAS hit to biology".
---

# Variant-to-Mechanism Analysis Skill

Trace the full causal chain from a genetic variant to its disease mechanism: regulatory context,
target gene(s), molecular pathways, and phenotypic consequences. Integrates 7+ databases across
3 evidence layers (regulatory, molecular, disease) to build an evidence-graded mechanistic model.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

---

## When to Use This Skill

Apply when users:
- Ask "how does rs7903146 cause type 2 diabetes?"
- Want to trace a GWAS variant to its biological mechanism
- Need to connect a non-coding variant to downstream pathways
- Ask "what gene does this variant affect and through what pathway?"
- Want a mechanistic narrative for a regulatory variant
- Need to identify the causal gene for a GWAS locus
- Ask "what is the functional impact of this intronic SNP?"

**NOT for** (use other skills instead):
- Coding variant pathogenicity / ACMG classification -> Use `tooluniverse-variant-interpretation`
- Pure regulatory element annotation without mechanism -> Use `tooluniverse-regulatory-genomics`
- Pure GWAS hit listing without mechanism -> Use `tooluniverse-gwas-snp-interpretation`
- Pharmacogenomic variant annotation -> Use `tooluniverse-pharmacogenomics`
- Gene-disease association without variant context -> Use `tooluniverse-gene-disease-association`

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **variant** | Yes | rsID or genomic coordinates | `"rs7903146"` or `"10:112998590:C:T"` |
| **trait** | No | Disease/trait context (helps prioritize) | `"type 2 diabetes"` |
| **tissue** | No | Tissue of interest for eQTL/expression | `"pancreas"` |

---

## Core Principles

1. **Causal chain construction** - Build explicit links: variant -> regulatory effect -> target gene -> pathway -> disease
2. **Multi-evidence convergence** - Require 2+ independent evidence lines per mechanistic link
3. **Evidence grading at each step** - T1-T4 for each link in the causal chain
4. **Negative results documented** - "No eQTL in pancreas" constrains the mechanism
5. **Alternative mechanisms considered** - Present competing causal models when evidence is ambiguous
6. **Report-first approach** - Create report file FIRST, populate progressively

---

## Workflow Overview

```
Input (rsID / coordinates + optional trait/tissue)
  |
  v
Phase 1: Variant Characterization
  VEP annotation, population frequency, basic consequence
  |
  v
Phase 2: Regulatory Context
  GWAS associations, RegulomeDB score, ENCODE chromatin marks, cCREs
  |
  v
Phase 3: Target Gene Identification
  GTEx eQTLs, OpenTargets L2G, nearest gene mapping
  |
  v
Phase 4: Gene Function & Pathways
  STRING PPI, GO enrichment, Reactome pathways, gene function
  |
  v
Phase 5: Disease Connection
  OpenTargets gene-disease, DisGeNET, GenCC, GWAS trait mapping
  |
  v
Phase 6: Mechanistic Synthesis
  Causal chain model, evidence integration, confidence scoring
  |
  v
Phase 7: Report
  Evidence-graded mechanistic narrative with causal chain diagram
```

---

## Phase 1: Variant Characterization

Resolve variant identity and get basic annotations.

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Step 1: VEP annotation
vep = tu.tools.EnsemblVEP_annotate_rsid(variant_id="rs7903146")
# NOTE: param is `variant_id`, NOT `rsid`
# Response format variable: list, {data, metadata}, or {error} -- handle all three
# Extract: consequence_type, gene, chromosome, position, alleles

# Step 2: Population frequency and pathogenicity scores
myvar = tu.tools.MyVariant_query_variants(
    variant_id="rs7903146",
    fields="dbsnp,gnomad_genome,cadd,clinvar"
)
# Returns: {hits: [{_id, dbsnp, gnomad_genome: {af: {af, ...ancestry}}, cadd: {phred}, clinvar}]}
# gnomAD AF: frequency in general population
# CADD phred: >=20 = top 1% deleterious, >=30 = top 0.1%

# Step 3: Confirm gene context
gwas_snp = tu.tools.gwas_search_snps(rs_id="rs7903146")
# Returns: SNP location, mapped genes, functional class
```

---

## Phase 2: Regulatory Context

Assess the variant's regulatory environment.

### 2a: GWAS Associations

```python
# All trait associations for this variant
gwas = tu.tools.gwas_search_associations(rs_id="rs7903146", size=50)
# Returns: {data: [{disease_trait, p_value, or_per_copy_number, beta, study_accession}]}
# NOTE: Use gwas_search_associations, NOT gwas_get_associations_for_trait (BROKEN)
```

### 2b: RegulomeDB Score

```python
regulome = tu.tools.RegulomeDB_query_variant(rsid="rs7903146")
# Returns: {status, data: {score/ranking, probability, features}}
# Score 1a-2a = strong regulatory evidence
# Uses GRCh38 (NOT hg19)
```

### 2c: ENCODE Chromatin Context

```python
# Check active enhancer marks in relevant tissue
encode_h3k27ac = tu.tools.ENCODE_search_histone_experiments(
    histone_mark="H3K27ac",
    biosample_term_name="pancreas",  # match to trait-relevant tissue
    limit=10
)

# Check promoter marks
encode_h3k4me3 = tu.tools.ENCODE_search_histone_experiments(
    histone_mark="H3K4me3",
    biosample_term_name="pancreas",
    limit=10
)

# Check chromatin accessibility
encode_atac = tu.tools.ENCODE_search_chromatin_accessibility(
    biosample_term_name="pancreas",
    limit=10
)
```

### 2d: cCRE Overlap (if coordinates known)

```python
# Check candidate cis-regulatory elements
ccres = tu.tools.UCSC_get_encode_cCREs(
    chrom="chr10",
    start=112998000,
    end=112999000
)
# Returns: cCRE type (PLS=promoter, pELS=proximal enhancer, dELS=distal enhancer, CTCF-only)
```

### 2e: OLS Trait Resolution (if trait provided)

```python
# Resolve trait to ontology ID for downstream tools
ols = tu.tools.ols_search_terms(query="type 2 diabetes", ontology="efo")
# Returns: {status, data: [{iri, label, short_form, ontology_name}]}
# For OpenTargets: use MONDO_0005148 for T2D (NOT EFO_0001360)
```

---

## Phase 3: Target Gene Identification

Identify which gene(s) the variant regulates. This is the critical link.

### 3a: GTEx eQTLs (primary evidence)

```python
# Find eQTL associations for the nearest gene
eqtls = tu.tools.GTEx_query_eqtl(gene_symbol="TCF7L2", size=100)
# Returns: {status, data: [{snpId, geneSymbol, tissueSiteDetailId, pValue, nes}]}
# Filter for the specific rsID in the results
# NES > 0: alt allele increases expression; NES < 0: decreases

# Check expression levels to prioritize tissues
expression = tu.tools.GTEx_get_median_gene_expression(gene_symbol="TCF7L2")
# Returns: median TPM across GTEx tissues
# IMPORTANT: GTEx uses v8 data (v10 endpoints may return empty)
```

### 3b: OpenTargets Locus-to-Gene (L2G)

```python
# Get credible sets and L2G predictions
credible = tu.tools.OpenTargets_get_variant_credible_sets(
    variant_id="10_112998590_C_T"  # chr_pos_ref_alt format
)
# Returns: credible set membership, L2G scores for causal genes
# L2G > 0.5: high confidence causal gene
# L2G 0.1-0.5: moderate confidence
```

### 3c: Nearest Gene Mapping

```python
# Get gene details for the candidate target
gene_info = tu.tools.MyGene_query_genes(
    query="symbol:TCF7L2",
    species="human",
    fields="symbol,ensembl.gene,entrezgene,name,summary,go",
    size=5
)
# Extract Ensembl ID for OpenTargets queries
# Filter by exact symbol match (first hit may not be correct gene)
```

### Target Gene Prioritization Criteria

| Evidence | Weight | Interpretation |
|----------|--------|----------------|
| eQTL in disease-relevant tissue | Highest | Direct regulatory link |
| OpenTargets L2G > 0.5 | High | ML-based causal prediction |
| Nearest gene (<10kb) | Moderate | Proximity (but often wrong) |
| eQTL in any tissue | Moderate | Regulatory link, possibly distal |
| Same TAD as gene | Low-Moderate | Topological association |
| Literature co-mention | Low | Not mechanistic |

---

## Phase 4: Gene Function & Pathways

Once target gene(s) identified, characterize molecular function.

### 4a: Protein-Protein Interactions

```python
# STRING PPI network
ppi = tu.tools.STRING_get_interaction_partners(
    protein_ids=["TCF7L2"],
    species=9606,
    required_score=700  # high confidence
)
# Returns: interaction partners with scores
# protein_ids accepts gene names (resolved to STRING IDs)

# STRING functional enrichment
enrichment = tu.tools.STRING_get_functional_enrichment(
    protein_ids=["TCF7L2"],
    species=9606
)
# Returns: GO terms, KEGG pathways, Reactome pathways enriched in network
```

### 4b: Pathway Analysis

```python
# Reactome pathway enrichment
reactome = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers="TCF7L2 CTNNB1 APC"  # space-separated STRING, NOT array
)
# Returns: enriched Reactome pathways

# UniProt function annotation
uniprot_func = tu.tools.UniProt_get_function_by_accession(
    accession="Q9NQB0"  # TCF7L2 UniProt accession
)
# Returns: list of strings (NOT dict) describing function
```

### 4c: Gene Ontology

```python
# PANTHER GO enrichment for target gene network
panther = tu.tools.PANTHER_enrichment(
    gene_list="TCF7L2,CTNNB1,APC,LEF1",  # comma-separated STRING
    organism=9606,
    annotation_dataset="GO:0008150"  # Biological Process
)
# Returns: {data: {enriched_terms: [{term_id, term_label, pvalue, fdr, fold_enrichment}]}}
# annotation_dataset: GO:0008150=BP, GO:0003674=MF, GO:0005575=CC
```

---

## Phase 5: Disease Connection

Link the molecular mechanism to disease phenotype.

### 5a: OpenTargets Gene-Disease Evidence

```python
# Disease associations for the target gene
ot_diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
    ensemblId="ENSG00000148737"  # TCF7L2 Ensembl ID
)
# Returns: disease associations with overall scores

# Specific evidence for gene-disease pair
ot_evidence = tu.tools.OpenTargets_target_disease_evidence(
    ensemblId="ENSG00000148737",
    efoId="MONDO_0005148"  # T2D
)
# Returns: IntOGen somatic driver evidence
# NOTE: Both IDs must be pre-resolved
```

### 5b: Gene-Disease Validation

```python
# GenCC curated validity (handles gene renames)
gencc = tu.tools.GenCC_search_gene(gene_symbol="TCF7L2")
# Returns: classification (Definitive/Strong/Moderate/Limited/Disputed/Refuted)
# NOTE: _gene_matches() checks both current and submitted HGNC symbols

# DisGeNET scored associations
disgenet = tu.tools.DisGeNET_search_gene(gene="TCF7L2", limit=20)
# Returns: diseases with scores (requires DISGENET_API_KEY)
```

### 5c: GWAS Trait Concordance

```python
# OpenTargets GWAS studies for the disease
ot_gwas = tu.tools.OpenTargets_search_gwas_studies_by_disease(
    diseaseIds=["MONDO_0005148"],
    size=20
)
# Returns: GWAS studies, locus-to-gene mappings
# NOTE: Use MONDO_0005148 for T2D (NOT EFO_0001360)
```

---

## Phase 6: Mechanistic Synthesis

### Causal Chain Construction

Build an explicit chain linking each evidence layer:

```
rs7903146 (10:112998590 C>T)
  |
  | [Regulatory] RegulomeDB 1a, in active enhancer (H3K27ac+), open chromatin (ATAC+)
  | [Evidence: T1 - multiple regulatory annotations converge]
  v
TCF7L2 gene expression altered
  |
  | [eQTL] GTEx: NES=-0.35 in pancreas (p=2.1e-12), NES=-0.28 in adipose (p=8.3e-9)
  | [L2G] OpenTargets L2G score = 0.89 for TCF7L2
  | [Evidence: T1 - eQTL + L2G convergence]
  v
TCF7L2 (Transcription Factor 7-Like 2)
  |
  | [Function] Wnt signaling pathway effector, beta-catenin co-activator
  | [Pathway] Reactome: TCF-dependent signaling in Wnt pathway
  | [PPI] STRING: CTNNB1, APC, LEF1 (score >900)
  | [Evidence: T2 - curated pathway knowledge]
  v
Disrupted Wnt signaling in pancreatic beta cells
  |
  | [Disease] OpenTargets T2D association score: 0.92
  | [GenCC] GenCC: Definitive for T2D susceptibility
  | [GWAS] 128 GWAS studies, p < 1e-100 in largest meta-analysis
  | [Evidence: T1 - replicated GWAS + curated gene-disease]
  v
Type 2 Diabetes susceptibility
```

### Confidence Scoring

Rate each link in the causal chain:

| Link | Confidence | Criteria |
|------|-----------|----------|
| Variant -> Regulatory effect | **High** | RegulomeDB <= 2 AND active chromatin marks |
| Regulatory effect -> Target gene | **High** | eQTL (p < 1e-8) AND L2G > 0.5 |
| Regulatory effect -> Target gene | **Moderate** | eQTL only OR L2G only |
| Regulatory effect -> Target gene | **Low** | Nearest gene only, no functional evidence |
| Target gene -> Pathway | **High** | Curated pathway + multiple PPI partners |
| Target gene -> Pathway | **Moderate** | Computational prediction only |
| Pathway -> Disease | **High** | GenCC Definitive/Strong AND GWAS p < 5e-8 |
| Pathway -> Disease | **Moderate** | DisGeNET > 0.3 OR GWAS suggestive |

### Overall Mechanism Confidence

| Level | Criteria |
|-------|----------|
| **Established** | All links High confidence; multiple independent evidence lines |
| **Strong** | Most links High; one link Moderate |
| **Moderate** | Mixed High/Moderate; no Low links |
| **Preliminary** | One or more Low confidence links |
| **Speculative** | Primary evidence is proximity or text-mining only |

---

## Evidence Grading

| Tier | Criteria | Sources |
|------|----------|---------|
| **T1** | Replicated GWAS + functional validation (eQTL + chromatin) | GWAS Catalog + GTEx + RegulomeDB/ENCODE |
| **T2** | Curated pathway/function + gene-disease association | Reactome + OpenTargets + GenCC |
| **T3** | Computational prediction (L2G, PPI network, GO enrichment) | OpenTargets L2G + STRING + PANTHER |
| **T4** | Single source, proximity-based, or text-mining | Nearest gene, literature co-mention |

---

## Tool Parameter Quick Reference

| Tool | Key Params | Notes |
|------|-----------|-------|
| `EnsemblVEP_annotate_rsid` | `variant_id` (NOT rsid) | VEP annotation; variable response format |
| `MyVariant_query_variants` | `variant_id`, `fields` | ClinVar, gnomAD, CADD aggregated |
| `gwas_search_associations` | `rs_id`, `disease_trait`, `p_value`, `size` | Primary GWAS search; NOT gwas_get_associations_for_trait |
| `gwas_search_snps` | `rs_id` | Detailed SNP info from GWAS Catalog |
| `gwas_get_snps_for_gene` | `gene_symbol` | GWAS SNPs mapped to a gene |
| `RegulomeDB_query_variant` | `rsid` | Regulatory score; uses GRCh38 |
| `ENCODE_search_histone_experiments` | `histone_mark`, `biosample_term_name`, `limit` | Histone ChIP-seq |
| `ENCODE_search_chromatin_accessibility` | `biosample_term_name`, `limit` | ATAC-seq / DNase-seq |
| `UCSC_get_encode_cCREs` | `chrom`, `start`, `end` | cCRE overlap (GRCh38, chr prefix) |
| `ols_search_terms` | `query`, `ontology` | Trait to EFO/MONDO ID |
| `GTEx_query_eqtl` | `gene_symbol` or `ensembl_gene_id`, `size` | Tissue-specific eQTLs (v8 data) |
| `GTEx_get_median_gene_expression` | `gene_symbol` or `ensembl_gene_id` | Expression across tissues |
| `OpenTargets_get_variant_credible_sets` | `variant_id` (chr_pos_ref_alt) | L2G and credible sets |
| `MyGene_query_genes` | `query`, `species`, `fields`, `size` | Gene ID resolution |
| `STRING_get_interaction_partners` | `protein_ids` (array), `species` (9606) | PPI network |
| `STRING_functional_enrichment` | `protein_ids` (array), `species` (9606) | GO/KEGG/Reactome enrichment |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (space-separated STRING) | Pathway enrichment |
| `UniProt_get_function_by_accession` | `accession` | Function annotation (returns list of strings) |
| `PANTHER_enrichment` | `gene_list` (comma-separated), `organism` (9606), `annotation_dataset` | GO enrichment |
| `OpenTargets_get_diseases_phenotypes_by_target_ensembl` | `ensemblId` | Gene-disease associations |
| `OpenTargets_target_disease_evidence` | `ensemblId`, `efoId` | Specific gene-disease evidence |
| `OpenTargets_search_gwas_studies_by_disease` | `diseaseIds` (array), `size` | GWAS studies from OT |
| `OpenTargets_get_disease_id_description_by_name` | `queryString` | Entity ID resolution |
| `GenCC_search_gene` | `gene_symbol` | Curated gene-disease validity |
| `DisGeNET_search_gene` | `gene` (symbol), `limit` | Scored gene-disease associations |

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---------|-----------|
| Assuming nearest gene is causal | Use eQTL + L2G evidence; nearest gene is often wrong for non-coding variants |
| Using `gwas_get_associations_for_trait` | BROKEN; use `gwas_search_associations` instead |
| Using `rsid` param for EnsemblVEP | Param is `variant_id`, not `rsid` |
| Using EFO_0001360 for T2D in OpenTargets | Use MONDO_0005148 |
| Passing array to ReactomeAnalysis | `identifiers` is space-separated STRING, NOT array |
| Passing disease name to ENCODE biosample | ENCODE biosamples are tissues/cell lines |
| Skipping negative eQTL results | "No eQTL in pancreas" is informative -- constrains mechanism |
| Treating L2G as definitive | L2G is probabilistic; combine with eQTL for confidence |
| Using `query` for OpenTargets search | Param is `queryString` (NOT `query`) |
| Ignoring tissue specificity | eQTL effects are often tissue-specific; match to disease-relevant tissue |

---

## Fallback Strategies

- **No eQTL for variant** -> Check if variant is in LD with known eQTL; check additional tissues; use L2G alone
- **No GWAS associations** -> Variant may be sub-threshold; check if in LD with GWAS hit; check trait-specific studies
- **RegulomeDB returns no data** -> Check ENCODE directly for chromatin marks at the position
- **OpenTargets variant ID format unclear** -> Use chr_pos_ref_alt (e.g., "10_112998590_C_T"); get alleles from VEP
- **No L2G data** -> Fall back to eQTL + nearest gene; note reduced confidence
- **Gene not in STRING/Reactome** -> Use UniProt function + GO annotations; check Harmonizome for broader context
- **Disease not in OpenTargets** -> Try alternative disease IDs (MONDO vs EFO); use DisGeNET as fallback
- **Multiple candidate causal genes** -> Present all with evidence; rank by eQTL effect size and L2G score

---

## Example Workflows

### Workflow 1: Complete Variant-to-Mechanism (rs7903146 and T2D)

```
Phase 1: EnsemblVEP_annotate_rsid(variant_id="rs7903146")
  -> intron_variant in TCF7L2, chr10:112998590

Phase 2a: gwas_search_associations(rs_id="rs7903146", size=50)
  -> T2D (p=1.2e-128), HbA1c, fasting glucose, etc.
Phase 2b: RegulomeDB_query_variant(rsid="rs7903146")
  -> Score 1a (eQTL + TF binding + motif + DNase)
Phase 2c: ENCODE_search_histone_experiments(histone_mark="H3K27ac", biosample_term_name="pancreas")
  -> Active enhancer marks present

Phase 3a: GTEx_query_eqtl(gene_symbol="TCF7L2", size=100)
  -> eQTL in pancreas (p=2.1e-12, NES=-0.35)
Phase 3b: OpenTargets_get_variant_credible_sets(variant_id="10_112998590_C_T")
  -> L2G: TCF7L2 = 0.89

Phase 4a: STRING_get_interaction_partners(protein_ids=["TCF7L2"], species=9606)
  -> CTNNB1, APC, LEF1, AXIN1 (Wnt pathway core)
Phase 4b: PANTHER_enrichment(gene_list="TCF7L2,CTNNB1,APC,LEF1", organism=9606, annotation_dataset="GO:0008150")
  -> Wnt signaling pathway, beta-catenin regulation

Phase 5a: OpenTargets_get_diseases_phenotypes_by_target_ensembl(ensemblId="ENSG00000148737")
  -> T2D score: 0.92
Phase 5b: GenCC_search_gene(gene_symbol="TCF7L2")
  -> Definitive for T2D susceptibility

Phase 6: Synthesis
  Mechanism: rs7903146 in active enhancer -> reduces TCF7L2 expression via eQTL ->
  disrupts Wnt/beta-catenin signaling in pancreatic beta cells ->
  impaired insulin secretion -> type 2 diabetes susceptibility
  Confidence: ESTABLISHED (all links High)
```

### Workflow 2: Unknown Variant Mechanism (rs12913832 and eye color)

```
Phase 1: EnsemblVEP_annotate_rsid(variant_id="rs12913832")
  -> intergenic_variant near HERC2/OCA2

Phase 2: gwas_search_associations(rs_id="rs12913832", size=20)
  -> eye color, hair color, skin pigmentation

Phase 3: GTEx_query_eqtl(gene_symbol="OCA2", size=50)
  -> Check for OCA2 eQTL (not just nearest gene HERC2)
  GTEx_query_eqtl(gene_symbol="HERC2", size=50)
  -> Compare eQTL evidence for both candidate genes

Phase 4: STRING_get_interaction_partners(protein_ids=["OCA2"], species=9606)
  -> Melanogenesis pathway partners

Phase 5: GenCC_search_gene(gene_symbol="OCA2")
  -> Strong for oculocutaneous albinism type 2

Phase 6: rs12913832 in HERC2 intron -> long-range enhancer for OCA2 ->
  altered melanin synthesis -> eye/hair/skin pigmentation
```

### Workflow 3: Variant with No Clear Target Gene

```
Phase 1-2: VEP + GWAS + RegulomeDB for variant
  -> intergenic, 200kb from nearest gene

Phase 3: GTEx eQTL search for all genes within 1Mb window
  -> No significant eQTL found
  OpenTargets L2G: low scores for all candidates (<0.3)

Phase 6: Report as PRELIMINARY mechanism
  Note: "Target gene uncertain. Nearest gene is [X] but no eQTL or L2G support.
  Possible mechanisms: (1) long-range enhancer not captured by GTEx,
  (2) cell-type-specific eQTL not in GTEx tissues, (3) non-eQTL mechanism
  (splicing, protein binding). Recommend: Hi-C data, single-cell eQTL, CRISPR validation."
```

---

## Completeness Checklist

Every analysis must verify these items before finalizing:

- [ ] Variant annotated (VEP consequence, population frequency, CADD)
- [ ] GWAS associations retrieved (all traits, p-values, effect sizes)
- [ ] RegulomeDB score obtained
- [ ] Chromatin context checked (at least H3K27ac + H3K4me3 in relevant tissue)
- [ ] eQTL evidence queried (GTEx, disease-relevant tissue prioritized)
- [ ] L2G/credible set evidence checked (OpenTargets)
- [ ] Target gene(s) identified with confidence rating
- [ ] Pathway/function annotated for target gene (STRING/Reactome/GO)
- [ ] Gene-disease association validated (OpenTargets + GenCC)
- [ ] Causal chain constructed with evidence at each link
- [ ] Each link graded T1-T4
- [ ] Overall mechanism confidence assigned (Established/Strong/Moderate/Preliminary/Speculative)
- [ ] Alternative mechanisms noted when evidence is ambiguous
- [ ] Report file written with causal chain diagram

---

## Limitations

- eQTL data from GTEx is bulk tissue (not single-cell); cell-type-specific effects may be missed.
- L2G scores are probabilistic predictions, not experimental validation.
- GWAS associations are correlative; fine-mapping needed to distinguish causal from LD-tagged variants.
- Pathway annotations may be incomplete for poorly studied genes.
- Mechanism confidence depends heavily on tissue-specific eQTL availability.
- Long-range regulatory effects (>1Mb) may not be captured by standard eQTL analysis.
- Some GWAS variants may act through mechanisms not captured by eQTLs (e.g., splicing, 3D genome).
- OpenTargets variant credible sets require chr_pos_ref_alt format; allele information needed from VEP.
- GTEx uses v8 data; v10 endpoints may return empty.
