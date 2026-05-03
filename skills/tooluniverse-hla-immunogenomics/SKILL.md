---
name: tooluniverse-hla-immunogenomics
description: Analyze HLA genes, MHC binding, epitope-MHC associations, and immunogenomics for transplant compatibility, vaccine design, and immunotherapy. Integrates IMGT, IEDB, BVBRC, UniProt, and DGIdb. Use for HLA typing interpretation, antigen presentation analysis, MHC restriction, neoantigen prediction context, and transplant immunology.
---

# HLA & Immunogenomics Analysis

Pipeline for exploring HLA gene families, MHC-peptide binding, epitope associations, and their clinical implications in transplantation, vaccine development, and cancer immunotherapy. Bridges immunogenetic databases (IMGT, IEDB) with functional annotation (UniProt) and druggability data (DGIdb).

## Reasoning Strategy

HLA analysis is fundamentally about peptide presentation: the polymorphism of HLA molecules determines which peptides are displayed to T cells, which in turn governs disease susceptibility, transplant rejection, drug hypersensitivity, and vaccine immunogenicity. HLA type affects disease susceptibility for autoimmune conditions (HLA-B27 and ankylosing spondylitis), transplant rejection (HLA mismatch drives alloresponse), drug hypersensitivity (abacavir causes severe hypersensitivity reactions only in HLA-B*57:01 carriers), and vaccine design (epitopes must be presented by the recipient's HLA alleles to elicit a T-cell response). Class I and Class II HLA molecules have fundamentally different binding grooves, peptide lengths, and T-cell partners — never conflate them. The absence of an epitope from IEDB means it has not been tested, not that it cannot bind.

**LOOK UP DON'T GUESS**: Never assume an allele's binding properties or population frequency — query IEDB for experimental binding data and IMGT for allele annotation. Do not guess which HLA alleles are common in a population; look up published frequency data via PubMed.

**Guiding principles**:
1. **HLA nomenclature precision** -- HLA allele names follow strict conventions (e.g., HLA-A*02:01); get the resolution level right
2. **MHC class awareness** -- Class I (A, B, C) and Class II (DR, DQ, DP) have different binding properties and clinical roles
3. **Species context** -- most queries target human HLA, but MHC exists across vertebrates; confirm species early
4. **Evidence layering** -- combine binding data (IEDB) with gene annotation (IMGT) and structural context (UniProt)
5. **Clinical translation** -- connect molecular findings to transplant matching, vaccine targets, or immunotherapy response
6. **English-first queries** -- use English terms in all tool calls; respond in the user's language

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Typical triggers:
- "Look up HLA-A*02:01 binding peptides"
- "What epitopes are presented by MHC class I for [pathogen]?"
- "Find HLA gene information for [allele]"
- "What MHC molecules bind [peptide/antigen]?"
- "Assess HLA associations for [disease]"
- "Find immunogenic epitopes for [virus/protein]"
- "What drugs target HLA-related pathways?"

**Not this skill**: For full neoantigen prediction pipelines, use `tooluniverse-immunotherapy-response-prediction`. For general gene function lookup, use `tooluniverse-drug-target-validation`.

---

## Core Databases

| Database | Scope | Best For |
|----------|-------|----------|
| **IMGT** | International ImMunoGeneTics; HLA/MHC gene nomenclature and sequences | Authoritative HLA gene info, allele nomenclature, sequence data |
| **IEDB** | Immune Epitope Database; experimentally validated epitope-MHC data | Epitope binding, MHC restriction, T-cell assay results |
| **BVBRC** | BV-BRC (formerly PATRIC/IRD); pathogen epitopes | Pathogen-derived epitopes with host MHC context |
| **UniProt** | Protein function and structure annotations | HLA protein features, domains, variants |
| **DGIdb** | Drug-Gene Interaction Database | Druggability of HLA-pathway genes |
| **PubMed** | Biomedical literature | Clinical HLA studies, transplant outcomes |

---

## Workflow Overview

```
Phase 0: Query Parsing & HLA Disambiguation
  Resolve allele names, identify MHC class, confirm species
    |
Phase 1: HLA Gene Lookup
  IMGT gene info, allele details, sequence data
    |
Phase 2: MHC Binding & Restriction
  IEDB MHC binding data, allele-specific peptide repertoire
    |
Phase 3: Epitope-MHC Associations
  IEDB/BVBRC epitope search, pathogen-specific epitopes
    |
Phase 4: Functional Annotation
  UniProt protein features, structural domains
    |
Phase 5: Clinical & Therapeutic Context
  DGIdb druggability, PubMed clinical evidence
    |
Phase 6: Report Synthesis
  Integrated immunogenomics report
```

---

## Phase Details

### Phase 0: Query Parsing & HLA Disambiguation

Parse the user's input to identify:
- **HLA allele** (e.g., HLA-A*02:01, HLA-DRB1*04:01) -- note resolution level (2-digit vs 4-digit)
- **MHC class** (I or II) -- determines binding groove structure and peptide length
- **Pathogen or antigen** (e.g., SARS-CoV-2 spike, influenza HA)
- **Clinical context** (transplant, vaccine, autoimmunity, cancer)

HLA nomenclature quick reference:
- `HLA-A*02:01` = gene A, allele group 02, specific protein 01
- Class I: HLA-A, HLA-B, HLA-C (present to CD8+ T cells, peptides 8-11 aa)
- Class II: HLA-DR, HLA-DQ, HLA-DP (present to CD4+ T cells, peptides 13-25 aa)

### Phase 1: HLA Gene Lookup

**Objective**: Get authoritative gene and allele information from IMGT.

**Tools**:
- `IMGT_search_genes` -- search for HLA/MHC genes
  - Input: `query` (gene name or keyword), optional `species`, `locus`
  - Output: gene list with nomenclature, locus, species
- `IMGT_get_gene_info` -- get detailed gene/allele information
  - Input: `gene_name` (IMGT gene name)
  - Output: allele sequences, functional status, reference sequences

**Workflow**:
1. Search IMGT for the target HLA gene or allele
2. Retrieve full gene details including functional status and sequence
3. Note the number of known alleles (HLA-A has >7,000; HLA-B has >8,000)
4. Identify whether the allele is commonly studied or rare

**If allele not found**: Check nomenclature -- older names may have been reassigned. Try searching by the gene name alone (e.g., "HLA-A") and filtering results.

### Phase 2: MHC Binding & Restriction

**Objective**: Find what peptides bind to a specific MHC molecule, or what MHC molecules present a given peptide.

**Tools**:
- `iedb_search_mhc` -- search for MHC molecules in IEDB
  - Input: `mhc_restriction` (allele name), optional `mhc_class`
  - Output: MHC molecules with binding data counts
- `iedb_get_epitope_mhc` -- get MHC binding details for an epitope
  - Input: `epitope_id` (IEDB epitope ID)
  - Output: MHC restriction data, binding assay results, IC50 values

**Workflow**:
1. Search IEDB for the target MHC allele to see available binding data
2. For specific epitope-MHC pairs, retrieve binding assay details
3. Note binding affinity (IC50 < 500 nM is typically considered a binder for class I)
4. Distinguish between binding assays (in vitro) and T-cell assays (functional)

**Binding affinity interpretation** (Class I):
- Strong binder: IC50 < 50 nM
- Moderate binder: IC50 50-500 nM
- Weak binder: IC50 500-5000 nM
- Non-binder: IC50 > 5000 nM

### Phase 3: Epitope-MHC Associations

**Objective**: Find epitopes from specific pathogens or antigens and their MHC restriction.

**Tools**:
- `iedb_search_epitopes` -- search for experimentally validated epitopes
  - Input: `organism_name` (source organism), `source_antigen_name` (protein name)
  - Output: epitope list with sequence, MHC restriction, assay results
- `BVBRC_search_epitopes` -- search pathogen-derived epitopes
  - Input: `query` (pathogen or antigen keyword), optional `host`, `limit`
  - Output: epitopes with host MHC context, assay type

**Workflow**:
1. Search IEDB for epitopes from the target pathogen/antigen
2. Supplement with BVBRC for additional pathogen-specific epitopes
3. Filter by the MHC allele of interest if specified
4. Categorize by assay type: binding assay, T-cell assay (IFN-gamma, cytotoxicity), MHC multimer

**Important**: IEDB epitopes are experimentally validated, not predicted. The absence of an epitope does not mean it won't bind -- it may simply be untested.

**Population coverage for vaccine design**: When selecting epitopes for a vaccine, check how common the restricting HLA allele is in the target population. An epitope restricted to HLA-A*02:01 covers ~50% of Europeans but <15% of some African populations. For broad population coverage, select epitopes across multiple HLA supertypes (A2, A3, B7, B44 cover >95% of most populations).

### Phase 4: Functional Annotation

**Objective**: Get protein-level features for HLA molecules and related proteins.

**Tools**:
- `UniProt_search` -- search for HLA protein entries
  - Input: `query` (protein/gene name), optional `organism`, `limit`
  - Output: protein entries with accession, function, features

**Workflow**:
1. Search UniProt for the HLA protein (e.g., "HLA-A human")
2. Extract functional domains: signal peptide, alpha chains, transmembrane region
3. Note polymorphic positions that define allele specificity
4. Check for structural data (PDB cross-references)

### Phase 5: Clinical & Therapeutic Context

**Objective**: Connect HLA findings to drug interactions and clinical evidence.

**Tools**:
- `DGIdb_get_drug_gene_interactions` -- find drugs targeting HLA-pathway genes
  - Input: `genes` (list of gene names, e.g., ["HLA-A", "B2M"])
  - Output: drug-gene interactions, interaction types, sources
- `PubMed_search_articles` -- find clinical HLA studies
  - Input: `query` (search term), optional `limit`
  - Output: articles with title, abstract, PMID

**Workflow**:
1. Query DGIdb for drug interactions with relevant HLA genes
2. Search PubMed for clinical studies (transplant outcomes, pharmacogenomics, disease associations)
3. For transplant queries, look for HLA matching guidelines and outcomes data
4. For pharmacogenomics, note HLA alleles linked to drug hypersensitivity (e.g., HLA-B*57:01 and abacavir)

**Well-known HLA-drug associations** (for context, always verify with current data):
- HLA-B*57:01: abacavir hypersensitivity
- HLA-B*15:02: carbamazepine SJS/TEN (Southeast Asian populations)
- HLA-B*58:01: allopurinol hypersensitivity
- HLA-A*31:01: carbamazepine drug reaction (European populations)

### Phase 6: Report Synthesis

Structure the report as:

1. **HLA Context** -- gene/allele identification, MHC class, population frequency if available
2. **Binding Profile** -- peptide repertoire, binding affinity distribution
3. **Epitope Landscape** -- pathogen-specific epitopes, assay evidence
4. **Protein Features** -- structural domains, polymorphic sites
5. **Clinical Relevance** -- transplant implications, drug associations, disease links
6. **Evidence Summary** -- graded by source (IEDB experimental > computational prediction > literature mention)

---

## Edge Cases & Fallbacks

- **Ambiguous allele name**: Ask user for resolution level. "HLA-A2" could mean HLA-A*02:01 or the broader A*02 group
- **No IEDB data for allele**: Common for rare alleles. Note the gap; suggest computational prediction tools
- **Cross-species MHC**: IMGT covers multiple species. Confirm species context for non-human queries (e.g., H-2 for mouse)
- **BVBRC empty results**: Try broader organism name or use IEDB as primary source

---

## Limitations

- **No binding prediction**: This skill queries experimental databases, not prediction algorithms (NetMHCpan, MHCflurry). It tells you what has been measured, not what might bind
- **Population frequency gaps**: HLA allele frequencies vary dramatically by ethnicity; databases may not cover all populations equally
- **Class II complexity**: Class II molecules are heterodimers (alpha + beta chains); binding prediction and data are less mature than for Class I
- **Epitope completeness**: IEDB coverage is biased toward well-studied pathogens (HIV, influenza, SARS-CoV-2) and common HLA alleles
