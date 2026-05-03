---
name: tooluniverse-gene-disease-association
description: Find and compare gene-disease associations across multiple databases (DisGeNET, OpenTargets, Monarch Initiative, OMIM, GenCC, Orphanet, ClinVar). Produces a unified evidence table with confidence levels and cross-database concordance. Use when users ask about gene-disease links, disease genes, genetic basis of disease, or want to compare association evidence across sources.
---

# Gene-Disease Association Analysis

Systematically query and compare gene-disease associations across 6+ databases to produce a unified, evidence-graded report. Cross-references DisGeNET scores, OpenTargets evidence, Monarch Initiative cross-species data, OMIM Mendelian mappings, GenCC curated validity, and Orphanet rare disease links.

**IMPORTANT**: Always use English gene names and disease terms in tool calls. Respond in the user's language.

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## Core Principles

1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Multi-database triangulation** - Query 4+ sources minimum, cross-validate
3. **Quantitative scoring** - Report numeric scores from each database
4. **Concordance analysis** - Count how many databases support each association and reason about independence
5. **Evidence reasoning** - Assess each association using evidence hierarchy, concordance, and mechanism plausibility
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

# Gene query: resolve IDs
gene_info = tu.tools.MyGene_query_genes(query=f"symbol:{gene_symbol}", species="human",
    fields="symbol,ensembl.gene,entrezgene,name", size=5)  # -> ensembl_id
monarch_search = tu.tools.MonarchV3_search(query=gene_symbol, category="biolink:Gene", limit=5)  # -> HGNC CURIE
omim_result = tu.tools.OMIM_search(query=gene_symbol, limit=5)  # -> MIM number
gene_summary = tu.tools.Harmonizome_get_gene(gene_symbol=gene_symbol)

# Disease query: resolve IDs
monarch_disease = tu.tools.MonarchV3_search(query=disease_name, category="biolink:Disease", limit=5)  # -> MONDO CURIE
mappings = tu.tools.MonarchV3_get_mappings(entity_id=mondo_id, limit=20)  # -> OMIM, ICD10, SNOMED, Orphanet
```

---

## Phase 2: DisGeNET Associations

> **API KEY REQUIRED**: DisGeNET tools require `DISGENET_API_KEY` environment variable. Without it, all DisGeNET calls will fail. Register at https://www.disgenet.org/api/#/Authorization for a free academic key.
> **Fallback if no key**: Skip this phase and rely on OpenTargets (Phase 3) + Monarch (Phase 4) which are free and cover much of the same data.

```python
# Gene -> diseases
disgenet_diseases = tu.tools.DisGeNET_search_gene(gene=gene_symbol, limit=20)
disgenet_gda = tu.tools.DisGeNET_get_gda(gene=gene_symbol, source="CURATED", min_score=0.3, limit=25)

# Disease -> genes (accepts name or UMLS CUI like "C0006142")
disgenet_genes = tu.tools.DisGeNET_search_disease(disease=disease_name, limit=20)
disgenet_ranked = tu.tools.DisGeNET_get_disease_genes(disease=disease_name, min_score=0.3, limit=50)
```

**Interpreting DisGeNET scores**: Higher scores reflect more evidence sources and stronger curation. Rather than memorizing cutoffs, ask: is this score driven by curated sources or text-mining? Use `source="CURATED"` to distinguish.

---

## Phase 3: OpenTargets Associations

```python
ot_diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(ensemblId=ensembl_id)
ot_evidence = tu.tools.OpenTargets_target_disease_evidence(ensemblId=ensembl_id, efoId=efo_id)
# Both require pre-resolved Ensembl/EFO IDs. Use OpenTargets_multi_entity_search to discover IDs.
```

---

## Phase 4: Monarch Initiative Associations

```python
# Gene -> diseases (integrates OMIM, ClinVar, Orphanet, model organisms)
monarch_diseases = tu.tools.MonarchV3_get_associations(
    subject=hgnc_curie, category="biolink:CausalGeneToDiseaseAssociation", limit=20)
# Disease -> genes
monarch_genes = tu.tools.MonarchV3_get_associations(
    subject=mondo_id, category="biolink:CorrelatedGeneToDiseaseAssociation", limit=20)
histopheno = tu.tools.MonarchV3_get_histopheno(entity_id=mondo_id)  # phenotypes by body system
entity = tu.tools.MonarchV3_get_entity(entity_id=hgnc_curie)  # details, synonyms, xrefs
```

---

## Phase 5: Mendelian Disease Evidence

> **API KEY REQUIRED**: OMIM tools require `OMIM_API_KEY`. Register at https://omim.org/api for academic access.
> **Fallback if no key**: Use Monarch Initiative (`biolink:CausalGeneToDiseaseAssociation` from Phase 4) which includes OMIM data without requiring a key. Also use GenCC (below) which is fully open.

```python
# OMIM: Mendelian gene-disease mapping (use gene MIM number, not phenotype MIM)
omim_entry = tu.tools.OMIM_get_entry(mim_number=mim_number)
omim_gene_map = tu.tools.OMIM_get_gene_map(mim_number=mim_number)
omim_clinical = tu.tools.OMIM_get_clinical_synopsis(mim_number=phenotype_mim)

# GenCC: curated validity (Definitive/Strong/Moderate/Limited/Disputed/Refuted)
gencc_result = tu.tools.GenCC_search_gene(gene_symbol=gene_symbol)  # handles gene renames
gencc_disease = tu.tools.GenCC_search_disease(disease="Marfan syndrome")  # word-tokenized matching
gencc_classifications = tu.tools.GenCC_get_classifications(gene_symbol="BRCA1", disease="breast cancer")

# Orphanet: rare disease associations (filter results by exact gene.symbol match)
orphanet_result = tu.tools.Orphanet_get_gene_diseases(gene_name=gene_symbol)
```

---

## Phase 6: Variant-Disease Associations (Optional)

Run when the query is gene-based and variant-level evidence adds value.

```python
vda_result = tu.tools.DisGeNET_get_vda(gene=gene_symbol, limit=25)  # variant-disease links
clinvar_result = tu.tools.ClinVar_search_variants(gene=gene_symbol, max_results=20)
clinvar_detail = tu.tools.ClinVar_get_variant_details(variant_id="12345")  # detailed variant info
```

---

## Phase 7: Evidence Synthesis

### Unified Association Table

Compile all results into a single table per gene-disease pair:

```markdown
## Gene-Disease Associations for BRCA1

| Disease | DisGeNET Score | OpenTargets Score | Monarch | OMIM | GenCC | Orphanet | Sources |
|---------|---------------|-------------------|---------|------|-------|----------|---------|
| Breast cancer | 0.82 | 0.95 | Yes | #114480 | Definitive | ORPHA:227535 | 6/6 |
| Ovarian cancer | 0.78 | 0.91 | Yes | #604370 | Definitive | ORPHA:213500 | 6/6 |
| Pancreatic cancer | 0.35 | 0.42 | Yes | - | Moderate | - | 3/6 |
| Fanconi anemia | 0.45 | 0.38 | Yes | #605724 | Strong | ORPHA:84 | 5/6 |
```

### Reasoning Strategies for Evidence Evaluation

**Evidence strength reasoning**: A gene-disease association supported by multiple independent lines of evidence (genetic, functional, model organism) is stronger than one supported by a single study. Ask: how many independent sources support this link? Do they converge on the same mechanism?

**Genetic evidence hierarchy**: Mendelian segregation (gene mutation causes disease in family) > GWAS (statistical association in population) > candidate gene study (hypothesis-driven). The first proves causation. The second shows correlation. The third is hypothesis. OMIM/GenCC "Definitive" entries represent the top of this hierarchy; DisGeNET text-mining hits represent the bottom.

**Cross-database concordance**: If DisGeNET, OpenTargets, AND OMIM all link gene X to disease Y, that's strong concordance. If only one database shows the link, check why -- is it a single study indexed by that database? Concordance across databases does not equal independent evidence if they all cite the same primary study. Count the number of databases supporting each association, but reason about whether they represent truly independent evidence.

**Mechanism reasoning**: Knowing the gene's function helps evaluate the association. A gene encoding a liver enzyme being linked to liver disease is mechanistically plausible. The same gene being linked to a psychiatric disorder needs stronger evidence because the mechanism is less obvious. Use Harmonizome gene summaries and Monarch phenotype profiles to assess mechanistic plausibility.

---

## Common Patterns

- **Gene-centric**: MyGene ID resolution -> DisGeNET/OpenTargets/Monarch/OMIM/GenCC/Orphanet -> unified table ranked by concordance
- **Disease-centric**: MonarchV3 disease search -> DisGeNET disease genes -> Monarch/OMIM -> unified gene table ranked by evidence
- **Gene-disease pair**: Resolve both IDs -> query all databases for the specific pair -> deep evidence summary with variant-level data
- **Mendelian discovery**: OMIM_search -> OMIM_get_gene_map -> GenCC per gene -> Orphanet -> filter by curated validity
- **Cross-species**: Monarch associations (HP/MP/ZP phenotypes) + DisGeNET ANIMAL_MODELS source -> model organism evidence
- **Gene renames**: GenCC handles renames automatically via `_gene_matches()`. Other tools require current HGNC symbol from MyGene_query_genes.

---

## Troubleshooting

- **DisGeNET returns empty**: Check DISGENET_API_KEY. Try UMLS CUI instead of disease name.
- **OMIM returns no gene map**: Use the gene MIM number, not the phenotype MIM number.
- **Monarch returns no associations**: Verify CURIE format (HGNC:1100 not HGNC:BRCA1). Use MonarchV3_search first.
- **OpenTargets returns no diseases**: Verify Ensembl ID via MyGene_query_genes with `fields="ensembl.gene"`.
- **GenCC returns empty**: Not all genes have classifications. Check for gene renames.
- **GenCC disease search misses**: Simplify query (e.g., "breast cancer" not "hereditary breast and ovarian cancer syndrome").
- **Gene rename misses in non-GenCC tools**: Only GenCC handles renames automatically. Use MyGene_query_genes to confirm the current canonical symbol.

---

## Resources

For comprehensive disease reports: [tooluniverse-disease-research](../tooluniverse-disease-research/SKILL.md)
For rare disease diagnosis: [tooluniverse-rare-disease-diagnosis](../tooluniverse-rare-disease-diagnosis/SKILL.md)
For variant interpretation: [tooluniverse-variant-interpretation](../tooluniverse-variant-interpretation/SKILL.md)
For drug-target validation: [tooluniverse-drug-target-validation](../tooluniverse-drug-target-validation/SKILL.md)
