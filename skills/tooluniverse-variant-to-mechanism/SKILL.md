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

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

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

## Workflow Overview

**Phase 1** Variant Characterization (VEP, population frequency, CADD) ->
**Phase 2** Regulatory Context (GWAS, RegulomeDB, ENCODE, cCREs) ->
**Phase 3** Target Gene Identification (GTEx eQTL, OpenTargets L2G) ->
**Phase 4** Gene Function & Pathways (STRING, Reactome, GO) ->
**Phase 5** Disease Connection (OpenTargets, GenCC, DisGeNET) ->
**Phase 6** Mechanistic Synthesis (causal chain, evidence grading, confidence scoring)

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
    query="rs7903146",  # NOTE: param is `query`, NOT `variant_id`
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
# Check enhancer (H3K27ac), promoter (H3K4me3), and accessibility in disease-relevant tissue
encode_h3k27ac = tu.tools.ENCODE_search_histone_experiments(
    histone_mark="H3K27ac", biosample_term_name="pancreas", limit=10)
encode_h3k4me3 = tu.tools.ENCODE_search_histone_experiments(
    histone_mark="H3K4me3", biosample_term_name="pancreas", limit=10)
encode_atac = tu.tools.ENCODE_search_chromatin_accessibility(
    biosample_term_name="pancreas", limit=10)
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

### How to Reason About Target Gene Identification

The nearest gene is often NOT the causal gene for non-coding variants. Regulatory elements can act over hundreds of kilobases, skipping intervening genes entirely. Before looking at tools, reason about which gene is the likely target:

- **eQTL in disease-relevant tissue is the strongest evidence.** If a variant is an eQTL for Gene X in pancreas and the trait is diabetes, that is a direct mechanistic link. An eQTL in an unrelated tissue is weaker but still informative.
- **L2G scores integrate multiple signals** (distance, chromatin interaction, eQTL) into a single prediction. L2G > 0.5 is high confidence, but it is a computational prediction, not experimental proof. Combine it with eQTL data -- when both agree, confidence is high.
- **Proximity alone is unreliable.** Many GWAS loci have the causal gene 2-3 genes away from the lead SNP. Never default to "nearest gene" without checking eQTL and L2G.
- **When multiple candidate genes have evidence**, present all of them ranked by strength. The answer may genuinely be uncertain.

---

## Phase 4: Gene Function & Pathways

Once target gene(s) identified, characterize molecular function.

```python
# STRING PPI network — NOTE: param is `identifiers` (string), NOT `protein_ids`
ppi = tu.tools.STRING_get_interaction_partners(
    identifiers="TCF7L2", species=9606, required_score=700)

# STRING functional enrichment (GO, KEGG, Reactome)
enrichment = tu.tools.STRING_get_functional_enrichment(
    identifiers="TCF7L2", species=9606)

# Reactome pathway enrichment — space-separated STRING, NOT array
reactome = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers="TCF7L2 CTNNB1 APC")

# UniProt function (returns list of strings, NOT dict)
uniprot_func = tu.tools.UniProt_get_function_by_accession(accession="Q9NQB0")

# PANTHER GO enrichment — GO:0008150=BP, GO:0003674=MF, GO:0005575=CC
panther = tu.tools.PANTHER_enrichment(
    gene_list="TCF7L2,CTNNB1,APC,LEF1", organism=9606,
    annotation_dataset="GO:0008150")
```

---

## Phase 5: Disease Connection

Link the molecular mechanism to disease phenotype.

```python
# Disease associations for target gene (requires Ensembl ID)
ot_diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
    ensemblId="ENSG00000148737")

# Specific gene-disease evidence (both IDs must be pre-resolved)
ot_evidence = tu.tools.OpenTargets_target_disease_evidence(
    ensemblId="ENSG00000148737", efoId="MONDO_0005148")

# GenCC curated validity (Definitive/Strong/Moderate/Limited/Disputed/Refuted)
gencc = tu.tools.GenCC_search_gene(gene_symbol="TCF7L2")

# DisGeNET scored associations (requires DISGENET_API_KEY)
disgenet = tu.tools.DisGeNET_search_gene(gene="TCF7L2", limit=20)

# OpenTargets GWAS studies — use MONDO IDs, NOT EFO
ot_gwas = tu.tools.OpenTargets_search_gwas_studies_by_disease(
    diseaseIds=["MONDO_0005148"], size=20)
```

---

## Phase 6: Mechanistic Synthesis

### How to Build and Evaluate the Causal Chain

The goal is an explicit chain: **Variant -> changed protein or expression -> altered pathway -> disease phenotype.** Each arrow is a link that needs evidence. A chain with all links supported is strong. A chain with a missing link is a hypothesis, not a conclusion.

**Start with the variant's location.** Is this coding or non-coding? Coding variants directly change the protein -- a missense variant swaps one amino acid, a nonsense variant truncates it. Non-coding variants change REGULATION -- they affect how much protein is made, not what protein is made. This distinction determines your entire analysis path.

**For coding variants**, ask: Is this position conserved across species? Is it in a functional domain (active site, binding interface, transmembrane helix)? A variant in a conserved active site residue is more likely pathogenic than one in a disordered loop. Check ClinVar and CADD for existing assessments, but reason about the structural context yourself.

**For non-coding variants**, ask: Is there an eQTL linking this variant to a nearby gene? Is the variant in a TFBS, enhancer, or promoter (from RegulomeDB and ENCODE)? A variant in open chromatin with an eQTL in disease-relevant tissue has a clear regulatory mechanism. A variant in a gene desert with no eQTL is much harder to interpret -- acknowledge this uncertainty.

**Evaluate each link independently.** For each arrow in the chain, ask: what is the evidence? Is it replicated? Is it from the right tissue? Then assess the chain as a whole:
- All links well-supported with convergent evidence from multiple databases = **Established** mechanism
- Most links strong but one relies on a single source = **Strong** mechanism
- Evidence is mixed or only moderate across links = **Moderate** mechanism
- One or more links have no direct evidence, only inference = **Preliminary** mechanism
- The connection rests on proximity or text-mining alone = **Speculative** mechanism

**The evidence hierarchy matters.** Clinical observation (ClinVar pathogenic with clinical data) is stronger than functional assays (eQTL, chromatin marks), which are stronger than computational predictions (CADD score, L2G model). A CADD score alone is weak evidence. Multiple convergent computational predictions are moderate. An eQTL replicated across studies in disease-relevant tissue is strong.

**Always consider alternative mechanisms.** If eQTL points to Gene A but L2G favors Gene B, present both models. If the variant could act through splicing rather than expression, note that. Honest uncertainty is more useful than false confidence.

---

## Evidence Grading

Grade each piece of evidence by how directly it supports a mechanistic link:

- **T1 (Strongest)**: Replicated GWAS association combined with functional validation -- an eQTL in the right tissue plus regulatory chromatin marks at the variant position. This is convergent evidence from independent sources.
- **T2**: Curated biological knowledge -- the target gene is in a known disease-relevant pathway (Reactome, GenCC Definitive). This does not prove the variant acts through this pathway, but it makes the mechanism biologically plausible.
- **T3**: Computational predictions -- L2G scores, PPI network enrichment, GO term enrichment. These are hypothesis-generating, not confirmatory. Useful when T1/T2 evidence is sparse.
- **T4**: Single-source or indirect evidence -- nearest gene assignment, literature co-mention, text-mining associations. These should never be the sole basis for a mechanistic claim.

---

## Common Mistakes and Fallbacks

**Parameter pitfalls** (correct param names are shown in code blocks above):
- `EnsemblVEP_annotate_rsid` uses `variant_id`, NOT `rsid`
- `MyVariant_query_variants` uses `query`, NOT `variant_id`
- `ReactomeAnalysis_pathway_enrichment` takes space-separated STRING, NOT array
- OpenTargets disease search uses `queryString`, NOT `query`
- Use MONDO IDs (e.g., MONDO_0005148 for T2D), NOT EFO IDs in OpenTargets
- `gwas_get_associations_for_trait` is BROKEN; use `gwas_search_associations`
- ENCODE biosample names are tissues/cell lines, not disease names

**When data is missing**, adapt the analysis:
- No eQTL: check additional tissues, use L2G alone, note reduced confidence
- No GWAS hits: variant may be sub-threshold or in LD with the true signal
- No RegulomeDB data: check ENCODE directly for chromatin marks at the position
- No L2G data: fall back to eQTL + nearest gene with appropriate caveats
- Gene not in STRING/Reactome: use UniProt function + GO annotations
- Multiple candidate genes: present all ranked by evidence, do not force a single answer

---

## Reasoning Through Common Scenarios

### Scenario 1: Non-coding variant with clear regulatory signal

When VEP shows an intronic or intergenic variant, GWAS shows strong trait associations, and RegulomeDB returns a high score (1a-2a), the path is straightforward: the variant disrupts a regulatory element. The key question becomes WHICH GENE it regulates. Check eQTL in disease-relevant tissue first, then L2G. When both converge on the same gene, follow the pathway analysis through to disease. This is the "happy path" and yields Established confidence.

### Scenario 2: Non-coding variant with ambiguous target gene

When the variant is intergenic with multiple nearby genes and eQTL/L2G evidence is weak or conflicting, resist the temptation to pick the nearest gene. Instead: check eQTLs for ALL candidate genes in the locus, compare L2G scores, and consider whether one candidate has known disease-relevant biology. Present multiple models ranked by evidence. Report as Preliminary or Moderate.

### Scenario 3: No functional signal at all

When there is no eQTL, no L2G support, and minimal regulatory annotation, acknowledge the gap honestly. The variant may act through a mechanism not captured by current databases (cell-type-specific regulation, splicing QTL, 3D genome interactions). State what was checked, what was negative, and what experiments would resolve the question. This is a valid and useful finding.

---

## Programmatic Access (Beyond Tools)

When ToolUniverse tools return partial annotations, aggregate from multiple sources directly:

```python
import requests, pandas as pd

rsid = "rs12345"

# Ensembl VEP REST — functional consequence prediction
vep = requests.get(f"https://rest.ensembl.org/vep/human/id/{rsid}?content-type=application/json").json()

# GTEx eQTL — tissue-specific expression effects
eqtl = requests.get(f"https://gtexportal.org/api/v2/association/singleTissueEqtl",
    params={"snpId": rsid, "datasetId": "gtex_v8"}).json()

# ClinVar bulk (variant_summary.txt.gz, ~200MB, all variants)
# Download once, filter locally:
# df = pd.read_csv("https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz", sep="\t")
# hits = df[df["RS# (dbSNP)"] == int(rsid.replace("rs",""))]

# Combine into unified annotation DataFrame
annotations = {"rsid": rsid, "vep_consequence": vep[0]["most_severe_consequence"] if vep else None,
    "eqtl_tissues": len(eqtl.get("singleTissueEqtl", [])),
    "sources_checked": ["VEP", "GTEx", "ClinVar"]}
```

See `tooluniverse-data-wrangling` skill for API patterns and error handling.

---

## Limitations

- GTEx eQTLs are bulk tissue (v8 data); cell-type-specific and splicing effects may be missed.
- L2G and CADD are computational predictions, not experimental proof.
- GWAS associations are correlative; LD tagging means the lead SNP may not be the causal variant.
- Long-range regulatory effects (>1Mb) and 3D genome interactions are poorly captured by current tools.
- OpenTargets variant credible sets require chr_pos_ref_alt format; get alleles from VEP first.
