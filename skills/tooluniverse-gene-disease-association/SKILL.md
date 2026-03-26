---
name: tooluniverse-gene-disease-association
description: Find and compare gene-disease associations across multiple databases (DisGeNET, OpenTargets, Monarch Initiative, OMIM, GenCC, Orphanet, ClinVar). Produces a unified evidence table with confidence levels and cross-database concordance. Use when users ask about gene-disease links, disease genes, genetic basis of disease, or want to compare association evidence across sources.
---

# Gene-Disease Association Analysis

Systematically query and compare gene-disease associations across 6+ databases to produce a unified, evidence-graded report. Cross-references DisGeNET scores, OpenTargets evidence, Monarch Initiative cross-species data, OMIM Mendelian mappings, GenCC curated validity, and Orphanet rare disease links.

**IMPORTANT**: Always use English gene names and disease terms in tool calls. Respond in the user's language.

---

## When to Use This Skill

Apply when users:
- Ask "what diseases are associated with [gene]?" or "what genes cause [disease]?"
- Want to compare gene-disease evidence across multiple databases
- Need gene-disease association scores with confidence levels
- Ask about genetic basis of a disease with quantitative evidence
- Need a unified view of Mendelian + complex disease associations for a gene
- Want to prioritize disease genes by cross-database concordance

**NOT for** (use other skills instead):
- Comprehensive disease report (all dimensions) -> Use `tooluniverse-disease-research`
- Rare disease differential diagnosis from phenotypes -> Use `tooluniverse-rare-disease-diagnosis`
- Variant pathogenicity interpretation -> Use `tooluniverse-variant-interpretation`
- Drug-target validation -> Use `tooluniverse-drug-target-validation`
- Gene enrichment / pathway analysis -> Use `tooluniverse-gene-enrichment`

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **query** | Yes | Gene symbol OR disease name/ID | `"BRCA1"` or `"breast cancer"` |
| **query_type** | No | `gene` or `disease` (auto-detected if omitted) | `gene` |
| **min_score** | No | Minimum association score filter (0-1, default: 0.1) | `0.3` |
| **sources** | No | Which databases to query (default: all) | `["DisGeNET", "OpenTargets", "OMIM"]` |

---

## Core Principles

1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Multi-database triangulation** - Query 4+ sources minimum, cross-validate
3. **Quantitative scoring** - Report numeric scores from each database
4. **Concordance analysis** - Count how many databases support each association
5. **Evidence grading** - Grade each association T1-T4 based on evidence type
6. **Mendelian vs complex** - Distinguish monogenic (OMIM/Orphanet) from complex (GWAS/DisGeNET) associations
7. **Negative results documented** - "No association found in [database]" is informative

---

## Workflow Overview

```
Phase 1: Gene/Disease Identification & ID Resolution
  Resolve gene symbol to Ensembl ID, HGNC CURIE, MIM number
  OR resolve disease name to UMLS CUI, EFO ID, MONDO ID, ORPHA code
      |
Phase 2: DisGeNET Associations (scored, multi-evidence)
  Gene-disease association scores with evidence type filtering
      |
Phase 3: OpenTargets Associations (integrated evidence)
  Disease phenotypes and genetic associations from OpenTargets
      |
Phase 4: Monarch Initiative (cross-species evidence)
  Gene-disease associations integrating OMIM, ClinVar, model organisms
      |
Phase 5: Mendelian Disease Evidence (curated)
  OMIM gene-disease map, GenCC validity classifications, Orphanet rare diseases
      |
Phase 6: Variant-Disease Associations (optional, if gene query)
  DisGeNET variant-disease links, ClinVar pathogenic variants
      |
Phase 7: Evidence Synthesis
  Unified table, concordance scoring, confidence levels, final report
```

---

## Phase 1: Gene/Disease Identification & ID Resolution

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# --- If query is a GENE ---
gene_symbol = "BRCA1"

# Get Ensembl ID for OpenTargets
gene_info = tu.tools.MyGene_query_genes(
    query=f"symbol:{gene_symbol}",
    species="human",
    fields="symbol,ensembl.gene,entrezgene,name",
    size=5
)
# Extract ensembl_id from results (filter by exact symbol match)

# Get HGNC CURIE for Monarch
monarch_search = tu.tools.MonarchV3_search(
    query=gene_symbol,
    category="biolink:Gene",
    limit=5
)
# Extract HGNC CURIE (e.g., "HGNC:1100" for BRCA1)

# Search OMIM for MIM number
omim_result = tu.tools.OMIM_search(query=gene_symbol, limit=5)
# Extract MIM number(s) for the gene entry

# Get gene summary from Harmonizome
gene_summary = tu.tools.Harmonizome_get_gene(gene_symbol=gene_symbol)

# --- If query is a DISEASE ---
disease_name = "breast cancer"

# Get MONDO ID for Monarch
monarch_disease = tu.tools.MonarchV3_search(
    query=disease_name,
    category="biolink:Disease",
    limit=5
)
# Extract MONDO CURIE (e.g., "MONDO:0007254")

# Get cross-ontology mappings (OMIM, ICD10, SNOMED, MESH, Orphanet)
if mondo_id:
    mappings = tu.tools.MonarchV3_get_mappings(
        entity_id=mondo_id,
        limit=20
    )
```

---

## Phase 2: DisGeNET Associations

> **API KEY REQUIRED**: DisGeNET tools require `DISGENET_API_KEY` environment variable. Without it, all DisGeNET calls will fail. Register at https://www.disgenet.org/api/#/Authorization for a free academic key.
> **Fallback if no key**: Skip this phase and rely on OpenTargets (Phase 3) + Monarch (Phase 4) which are free and cover much of the same data.

```python
# --- Gene query: find associated diseases ---
disgenet_diseases = tu.tools.DisGeNET_search_gene(
    gene=gene_symbol,
    limit=20
)
# Returns: diseases with association scores and evidence counts

# For deeper evidence filtering:
disgenet_gda = tu.tools.DisGeNET_get_gda(
    gene=gene_symbol,
    source="CURATED",      # CURATED, LITERATURE, ANIMAL_MODELS, or ALL
    min_score=0.3,         # 0-1, higher = stronger evidence
    limit=25
)

# --- Disease query: find associated genes ---
disgenet_genes = tu.tools.DisGeNET_search_disease(
    disease=disease_name,  # or UMLS CUI like "C0006142"
    limit=20
)

# Get ranked gene list with score filtering
disgenet_ranked = tu.tools.DisGeNET_get_disease_genes(
    disease=disease_name,  # or UMLS CUI
    min_score=0.3,
    limit=50
)
```

**DisGeNET Score Interpretation**:
- 0.0-0.1: Weak evidence (single source, text-mining)
- 0.1-0.3: Moderate evidence (multiple sources or curated)
- 0.3-0.6: Strong evidence (curated + literature)
- 0.6-1.0: Very strong evidence (definitive, well-replicated)

---

## Phase 3: OpenTargets Associations

```python
# --- Gene query: diseases associated with target ---
ot_diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
    ensemblId=ensembl_id  # e.g., "ENSG00000012048" for BRCA1
)
# Returns disease associations with overall association scores

# --- Specific gene-disease evidence (IntOGen somatic driver data) ---
ot_evidence = tu.tools.OpenTargets_target_disease_evidence(
    ensemblId=ensembl_id,  # e.g., "ENSG00000012048"
    efoId=efo_id           # e.g., "MONDO_0007254" for breast cancer
)
# Returns IntOGen somatic driver evidence for specific target-disease pair
# NOTE: Requires pre-resolved Ensembl and EFO/MONDO IDs (no gene_symbol/disease_name aliases)
```

**Note**: OpenTargets integrates 13 evidence sources (genetic associations, somatic mutations, drugs, text mining, etc.) into a single association score (0-1). Use `OpenTargets_multi_entity_search(queryString="BRCA1")` to discover Ensembl IDs if not already known.

---

## Phase 4: Monarch Initiative Associations

```python
# --- Gene query: cross-species gene-disease associations ---
monarch_diseases = tu.tools.MonarchV3_get_associations(
    subject=hgnc_curie,   # e.g., "HGNC:1100" for BRCA1
    category="biolink:CausalGeneToDiseaseAssociation",
    limit=20
)
# Integrates OMIM, ClinVar, Orphanet, and model organism data

# --- Disease query: genes associated with disease ---
monarch_genes = tu.tools.MonarchV3_get_associations(
    subject=mondo_id,     # e.g., "MONDO:0007254"
    category="biolink:CorrelatedGeneToDiseaseAssociation",
    limit=20
)

# Disease phenotype profile by body system
histopheno = tu.tools.MonarchV3_get_histopheno(
    entity_id=mondo_id    # e.g., "MONDO:0007254"
)
# Returns counts of HPO phenotypes grouped by anatomical system

# Get entity details
entity = tu.tools.MonarchV3_get_entity(
    entity_id=hgnc_curie  # or mondo_id for disease
)
# Returns name, category, description, synonyms, cross-references
```

---

## Phase 5: Mendelian Disease Evidence

> **API KEY REQUIRED**: OMIM tools require `OMIM_API_KEY`. Register at https://omim.org/api for academic access.
> **Fallback if no key**: Use Monarch Initiative (`biolink:CausalGeneToDiseaseAssociation` from Phase 4) which includes OMIM data without requiring a key. Also use GenCC (below) which is fully open.

```python
# --- OMIM: authoritative Mendelian gene-disease mapping ---
omim_entry = tu.tools.OMIM_get_entry(
    mim_number=mim_number  # e.g., "113705" for BRCA1
)
# Returns text description, clinical features, inheritance, molecular genetics

omim_gene_map = tu.tools.OMIM_get_gene_map(
    mim_number=mim_number
)
# Returns gene-disease mapping with phenotypes and inheritance patterns

omim_clinical = tu.tools.OMIM_get_clinical_synopsis(
    mim_number=phenotype_mim  # MIM number of the PHENOTYPE entry
)
# Returns structured clinical features by body system

# --- GenCC: curated gene-disease validity ---
# Gene query:
gencc_result = tu.tools.GenCC_search_gene(
    gene_symbol=gene_symbol  # e.g., "BRCA1"
)
# Returns classifications: Definitive, Strong, Moderate, Limited, Disputed, Refuted
# From multiple panels: ClinGen, Ambry, Genomics England, Orphanet
# NOTE: Uses _gene_matches() which checks BOTH gene_symbol AND submitted_as_hgnc_symbol
# This handles HGNC gene renames (e.g., GBA -> GBA1)

# Disease query (accepts disease name directly):
gencc_disease = tu.tools.GenCC_search_disease(
    disease="Marfan syndrome"  # disease name, MONDO ID, or other disease identifier
)
# Returns gene-disease validity classifications for that disease
# NOTE: Uses _disease_matches() with word-tokenized fallback
# Handles hyphenated disease names like "breast-ovarian cancer"
# Matching logic: exact substring first, then all-words-present fallback

# Combined query (gene + disease):
gencc_classifications = tu.tools.GenCC_get_classifications(
    gene_symbol="BRCA1",       # optional: filter by gene
    disease="breast cancer"     # optional: filter by disease
)
# Returns all matching classifications with submitter info
# NOTE: _disease_matches() tokenizes query words and checks all appear in title
# Example: "breast cancer" matches "hereditary breast-ovarian cancer"

# --- Orphanet: rare disease associations ---
orphanet_result = tu.tools.Orphanet_get_gene_diseases(
    gene_name=gene_symbol  # e.g., "BRCA1"
)
# Returns ORPHA codes, association types, genomic locus info
# IMPORTANT: Orphanet searches by substring, so "BRCA1" also matches
# genes with "BRCA1" in their full name (BAP1, BRCC3, BRAT1).
# Always filter results by checking gene.symbol == gene_symbol exactly.
```

**GenCC Classification Hierarchy** (most to least confident):
1. **Definitive** - Replicated, well-established association
2. **Strong** - Multiple independent studies, compelling evidence
3. **Moderate** - Some independent replication
4. **Limited** - Single study or limited evidence
5. **Disputed** - Conflicting evidence
6. **Refuted** - Evidence against association

**GenCC Matching Behavior** (important for correct queries):
- **Gene search**: `_gene_matches()` checks both `gene_symbol` and `submitted_as_hgnc_symbol` fields. This handles HGNC gene renames (e.g., querying "GBA" will match records filed under "GBA1" and vice versa).
- **Disease search**: `_disease_matches()` first tries exact substring match, then falls back to word-tokenized matching where all query words must appear in the disease title. This handles hyphenated names (e.g., "breast ovarian cancer" matches "hereditary breast-ovarian cancer, type 1").
- **Classification filter**: Optional parameter to filter by evidence level (e.g., "Definitive", "Strong").

---

## Phase 6: Variant-Disease Associations (Optional)

Run when the query is gene-based and variant-level evidence adds value.

```python
# --- DisGeNET variant-disease links ---
vda_result = tu.tools.DisGeNET_get_vda(
    gene=gene_symbol,  # e.g., "BRCA1"
    limit=25
)
# Returns variant rsIDs, associated diseases, evidence scores

# --- ClinVar pathogenic variants ---
# Both ClinVar_search_variants and ClinVar_search_variants work (same tool)
clinvar_result = tu.tools.ClinVar_search_variants(
    gene=gene_symbol,
    max_results=20
)
# Returns variant IDs and basic classification info

# For detailed info on a specific variant:
clinvar_detail = tu.tools.ClinVar_get_variant_details(
    variant_id="12345"  # ClinVar variant ID from search results
)
# Returns accession, title, genes, clinical significance, review status
```

---

## Phase 7: Evidence Synthesis

### Unified Association Table

Compile all results into a single table per gene-disease pair:

```markdown
## Gene-Disease Associations for BRCA1

| Disease | DisGeNET Score | OpenTargets Score | Monarch | OMIM | GenCC | Orphanet | Sources | Confidence |
|---------|---------------|-------------------|---------|------|-------|----------|---------|------------|
| Breast cancer | 0.82 | 0.95 | Yes | #114480 | Definitive | ORPHA:227535 | 6/6 | Very High |
| Ovarian cancer | 0.78 | 0.91 | Yes | #604370 | Definitive | ORPHA:213500 | 6/6 | Very High |
| Pancreatic cancer | 0.35 | 0.42 | Yes | - | Moderate | - | 3/6 | Moderate |
| Fanconi anemia | 0.45 | 0.38 | Yes | #605724 | Strong | ORPHA:84 | 5/6 | High |
```

### Confidence Levels

| Level | Criteria |
|-------|----------|
| **Very High** | 5-6 databases agree, DisGeNET >= 0.6, GenCC Definitive/Strong |
| **High** | 4+ databases agree, DisGeNET >= 0.3, GenCC Moderate+ |
| **Moderate** | 2-3 databases agree, DisGeNET >= 0.1, any GenCC level |
| **Low** | 1 database only, DisGeNET < 0.1, or no curated evidence |
| **Conflicting** | Databases disagree (e.g., GenCC Disputed + DisGeNET high score) |

### Evidence Grading

| Tier | Symbol | Criteria | Sources |
|------|--------|----------|---------|
| **T1** | [T1] | Curated Mendelian or regulatory-approved | OMIM, GenCC Definitive/Strong, Orphanet |
| **T2** | [T2] | Curated multi-source with scores | DisGeNET (CURATED source, score >= 0.3), OpenTargets |
| **T3** | [T3] | Computational or model organism | Monarch (model organism), DisGeNET (LITERATURE/ANIMAL_MODELS) |
| **T4** | [T4] | Single source or text-mining | DisGeNET (score < 0.1), single literature report |

---

## Common Patterns

### Pattern 1: Gene-Centric Query
```
Input: Gene symbol (e.g., "BRCA1")
Flow: MyGene ID resolution -> DisGeNET_search_gene -> OpenTargets diseases ->
      Monarch gene-disease -> OMIM gene map -> GenCC validity -> Orphanet ->
      Unified table with concordance
Output: All diseases associated with gene, ranked by cross-database concordance
```

### Pattern 2: Disease-Centric Query
```
Input: Disease name (e.g., "breast cancer")
Flow: MonarchV3 disease search -> DisGeNET_search_disease -> DisGeNET_get_disease_genes ->
      Monarch disease-gene -> OMIM search -> Histopheno profile ->
      Unified gene table with scores
Output: All genes associated with disease, ranked by evidence strength
```

### Pattern 3: Specific Gene-Disease Pair
```
Input: Gene + disease (e.g., "BRCA1 and breast cancer")
Flow: Resolve both IDs -> DisGeNET_get_gda(gene, disease) ->
      OpenTargets evidence -> Monarch association -> OMIM entry ->
      GenCC classification -> DisGeNET_get_vda for variants ->
      Deep evidence summary for the pair
Output: Detailed evidence profile for one gene-disease relationship
```

### Pattern 4: Mendelian Disease Gene Discovery
```
Input: Disease with suspected Mendelian basis
Flow: OMIM_search -> OMIM_get_gene_map -> GenCC_search_gene per gene ->
      Orphanet_get_gene_diseases -> DisGeNET validation ->
      Filter by GenCC >= Moderate and DisGeNET >= 0.3
Output: High-confidence Mendelian disease genes with curated classifications
```

### Pattern 5: Cross-Species Evidence Integration
```
Input: Gene with limited human evidence
Flow: Monarch gene-disease + gene-phenotype associations ->
      Compare HP (human) vs MP (mouse) vs ZP (zebrafish) phenotypes ->
      DisGeNET ANIMAL_MODELS source filter ->
      Phenotype similarity search if HPO terms available
Output: Model organism evidence supporting gene-disease link
```

### Pattern 6: Gene Rename / Legacy Symbol Handling
```
Input: Old gene symbol (e.g., "GBA" renamed to "GBA1")
Flow: GenCC_search_gene(gene_symbol="GBA")
  -> _gene_matches() checks both gene_symbol AND submitted_as_hgnc_symbol
  -> Returns records filed under both "GBA" and "GBA1"
Note: Other tools may not handle renames; always verify with MyGene_query_genes
```

---

## Tool Parameter Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `MyGene_query_genes` | `query`, `species`, `fields`, `size` | Use `query="symbol:GENE"` for exact match |
| `DisGeNET_search_gene` | `gene` (symbol), `limit` | Requires DISGENET_API_KEY |
| `DisGeNET_search_disease` | `disease` (name or UMLS CUI), `limit` | |
| `DisGeNET_get_gda` | `gene`, `disease`, `source`, `min_score`, `limit` | source: CURATED/LITERATURE/ANIMAL_MODELS/ALL |
| `DisGeNET_get_vda` | `variant` (rsID) or `gene` (symbol), `limit` | |
| `DisGeNET_get_disease_genes` | `disease` (name or CUI), `min_score`, `limit` | |
| `OpenTargets_get_diseases_phenotypes_by_target_ensembl` | `ensemblId` | Requires Ensembl gene ID |
| `OpenTargets_target_disease_evidence` | `ensemblId`, `efoId` | IntOGen somatic driver evidence; needs both IDs pre-resolved |
| `MonarchV3_search` | `query`, `category`, `limit` | category: biolink:Gene, biolink:Disease |
| `MonarchV3_get_entity` | `entity_id` (CURIE) | e.g., HGNC:1100, MONDO:0007254 |
| `MonarchV3_get_associations` | `subject` (CURIE), `category`, `limit` | category: biolink:CausalGeneToDiseaseAssociation, etc. |
| `MonarchV3_get_histopheno` | `entity_id` (disease CURIE) | Returns phenotype counts by body system |
| `MonarchV3_get_mappings` | `entity_id`, `limit` | Cross-ontology ID mappings |
| `MonarchV3_phenotype_similarity_search` | `phenotypes` (HPO array), `group`, `limit` | For phenotype-based disease matching |
| `OMIM_search` | `query`, `limit`, `start` | Requires OMIM_API_KEY |
| `OMIM_get_entry` | `mim_number`, `include` | include: "text,clinicalSynopsis" |
| `OMIM_get_gene_map` | `mim_number` or `chromosome`, `limit` | |
| `OMIM_get_clinical_synopsis` | `mim_number` | Phenotype features by body system |
| `GenCC_search_gene` | `gene_symbol`, `classification` | Checks both current AND submitted HGNC symbol (handles renames like GBA->GBA1) |
| `GenCC_search_disease` | `disease` (name or MONDO ID), `classification` | Word-tokenized matching: "breast cancer" matches "hereditary breast-ovarian cancer" |
| `GenCC_get_classifications` | `gene_symbol`, `disease` (both optional) | Combined gene+disease filter with same matching logic |
| `Orphanet_get_gene_diseases` | `gene_name` (symbol or keyword) | Also accepts `gene_symbol` |
| `ClinVar_search_variants` | `gene`, `condition`, `variant_id`, `max_results` | Also available as `ClinVar_search_variants` (same tool) |
| `ClinVar_get_variant_details` | `variant_id` (ClinVar ID) | Detailed variant info: accession, clinical significance, review status |
| `Harmonizome_get_gene` | `gene_symbol` | Gene summary from 100+ datasets |

---

## Completeness Checklist

Every analysis must verify these items before finalizing:

- [ ] Gene/disease IDs resolved (Ensembl, HGNC CURIE, MIM number, MONDO ID)
- [ ] DisGeNET queried (both search and scored GDA)
- [ ] OpenTargets queried (disease-phenotype associations)
- [ ] Monarch Initiative queried (cross-species gene-disease links)
- [ ] OMIM queried (Mendelian disease mapping)
- [ ] GenCC queried (curated validity classification)
- [ ] Orphanet queried (rare disease associations)
- [ ] Unified association table compiled with all scores
- [ ] Concordance counts calculated (N databases supporting each association)
- [ ] Confidence levels assigned (Very High / High / Moderate / Low / Conflicting)
- [ ] Evidence grading applied (T1-T4)
- [ ] Mendelian vs complex disease distinction noted
- [ ] Report file written with source citations

---

## Troubleshooting

**"DisGeNET returns empty"**: Check DISGENET_API_KEY is set. Try UMLS CUI instead of disease name.

**"OMIM returns no gene map"**: Ensure you use the gene MIM number, not the phenotype MIM number for gene_map queries.

**"Monarch returns no associations"**: Verify CURIE format (HGNC:1100 not HGNC:BRCA1). Use MonarchV3_search first to find correct CURIEs.

**"OpenTargets returns no diseases"**: Verify Ensembl ID is correct. Use MyGene_query_genes with `fields="ensembl.gene"` to get the right ID.

**"GenCC returns empty"**: Not all genes have GenCC classifications. This is expected for non-disease genes. Also check if the gene was recently renamed (GenCC checks both current and submitted HGNC symbols, but the TSV data may lag behind HGNC updates).

**"GenCC disease search misses results"**: The word-tokenized fallback requires ALL query words to appear in the disease title. Simplify the query (e.g., "breast cancer" instead of "hereditary breast and ovarian cancer syndrome"). Single-word queries use exact substring match only.

**"Gene rename causes misses in non-GenCC tools"**: GenCC handles renames via `_gene_matches()`, but other tools (DisGeNET, OpenTargets, OMIM) require the current HGNC symbol. Use MyGene_query_genes to confirm the current canonical symbol before querying other databases.

---

## Resources

For comprehensive disease reports: [tooluniverse-disease-research](../tooluniverse-disease-research/SKILL.md)
For rare disease diagnosis: [tooluniverse-rare-disease-diagnosis](../tooluniverse-rare-disease-diagnosis/SKILL.md)
For variant interpretation: [tooluniverse-variant-interpretation](../tooluniverse-variant-interpretation/SKILL.md)
For drug-target validation: [tooluniverse-drug-target-validation](../tooluniverse-drug-target-validation/SKILL.md)
