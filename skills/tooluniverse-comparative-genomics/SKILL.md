---
name: tooluniverse-comparative-genomics
description: Cross-species gene and sequence comparison, ortholog analysis, and evolutionary conservation assessment using ToolUniverse tools. Use when comparing genes across species, finding orthologs, analyzing evolutionary conservation, or performing comparative functional annotation.
---

# Comparative Genomics & Ortholog Analysis

Cross-species gene comparison, ortholog identification, sequence retrieval, and functional conservation analysis integrating Ensembl Compara, NCBI, UniProt, OLS, Monarch, and OpenTargets.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use This Skill

**Triggers**:
- "Find the mouse ortholog of [human gene]"
- "Compare [gene] across species"
- "Is [gene] conserved in [organism]?"
- "What are the orthologs of [gene]?"
- "Cross-species comparison of [gene/protein]"
- "Evolutionary conservation of [gene]"
- "Compare GO annotations between human and mouse [gene]"

**Use Cases**:
1. **Ortholog Discovery**: Find equivalent genes in other species for a human gene
2. **Conservation Analysis**: Assess how conserved a gene is across evolutionary distance
3. **Functional Comparison**: Compare GO terms, domains, and annotations across orthologs
4. **Model Organism Selection**: Determine which model organism best recapitulates human gene function
5. **Gene Tree Analysis**: Visualize evolutionary history of a gene family
6. **Cross-Species Phenotype Bridging**: Link human disease phenotypes to model organism phenotypes via orthologs

---

## Conservation Reasoning Framework

Understanding conservation requires distinguishing between types of evolutionary patterns and what they imply about function.

**High conservation signals functional constraint.** When a gene is maintained as a 1:1 ortholog from yeast to humans, purifying selection has prevented sequence divergence — the gene's function is essential and cannot be easily altered. Highly conserved positions within a protein sequence (high PhastCons scores > 0.8, or GERP RS > 4) are under strong constraint; mutations at these positions are disproportionately pathogenic. For non-coding regions, conservation in mammals at PhastCons > 0.5 suggests a candidate regulatory element.

**Low conservation in one lineage has two possible explanations: relaxed selection or positive selection.** Use the dN/dS ratio (nonsynonymous to synonymous substitution rate) to distinguish them. A dN/dS ratio near 1 suggests neutral evolution — the gene is no longer under purifying selection (relaxed constraint, possibly reflecting loss of function in that lineage). A dN/dS ratio > 1 indicates positive selection — the gene is diverging faster than neutral expectation, often because it is adapting to a new environment or function. A dN/dS ratio << 1 is the signature of purifying selection (functional constraint). When a vertebrate gene shows high divergence in a specific branch of the tree, ask which explanation applies before concluding that function is lost.

**Ortholog relationship type shapes interpretation.** A 1:1 ortholog (one gene in human, one in mouse) is the highest-confidence functional equivalent — it has not been duplicated in either lineage, so it most likely performs the same ancestral role. A 1:many relationship (one gene in human, multiple in mouse) means the target species has duplicated the gene; the copies may have subfunctionalized (each copy performs a subset of the original roles) or neofunctionalized (one copy gained a new role). Do not assume both copies retain full ancestral function. A many:many relationship reflects complex duplication history in both species and requires analyzing each paralog pair individually.

**Conservation depth predicts essentiality.** A gene conserved across all vertebrates suggests a fundamental cellular process. A gene conserved only in mammals suggests a more specialized vertebrate innovation. A gene present only in primates or only in humans is likely a recent evolutionary acquisition, possibly involved in human-specific biology but often lacking the depth of functional characterization available for deeply conserved genes.

**Absence of an ortholog is a finding, not an error.** Lineage-specific genes exist and are biologically meaningful. Before concluding a gene is lineage-specific, check: (1) whether BLAST with relaxed thresholds finds distant homologs, (2) whether a highly divergent ortholog exists that Ensembl Compara missed, and (3) whether the gene belongs to a rapidly evolving family (immune genes, olfactory receptors, reproductive proteins) where turnover is expected.

---

## Workflow Overview

```
Input (gene symbol/ID + reference species)
  |
  v
Phase 1: Gene Identification & Validation
  |
  v
Phase 2: Ortholog Discovery (Ensembl Compara + OpenTargets)
  |
  v
Phase 3: Sequence Retrieval (NCBI + Ensembl)
  |
  v
Phase 4: Functional Annotation Comparison (UniProt + OLS GO terms)
  |
  v
Phase 5: Cross-Species Phenotype Bridging (Monarch)
  |
  v
Phase 6: Gene Tree & Evolutionary Context (Ensembl Compara)
  |
  v
Report: Conservation summary, ortholog evidence, functional comparison, phenotype bridging
```

---

## Phase 1: Gene Identification & Validation

`ensembl_lookup_gene` takes `gene_id` (symbol or Ensembl ID). The `species` parameter is REQUIRED when using gene symbols (e.g., `species="homo_sapiens"`); omitting it causes errors. Extract the Ensembl gene ID, description, biotype, and chromosomal coordinates for downstream queries. For non-human references, adjust `species` accordingly (e.g., "mus_musculus", "danio_rerio").

---

## Phase 2: Ortholog Discovery

`EnsemblCompara_get_orthologues` is the primary tool. It takes `gene` (symbol or Ensembl ID), `species` (source species, default "human"), and optionally `target_species` (e.g., "mouse", "zebrafish") or `target_taxon` (NCBI taxon ID). Omit `target_species` to get all orthologs across the tree; filter client-side for specific species. It returns homology type (one2one, one2many, many2many) and the taxonomy divergence level for each ortholog.

`ensembl_get_homology` is the alternative when you need sequence-level data alongside the ortholog mapping. Use `sequence="protein"` and `aligned=true` for aligned sequence comparison across species.

`OpenTargets_get_target_homologues_by_ensemblID` (takes `ensemblId`) provides supplementary ortholog data from OpenTargets, which can add druggability context and cross-reference with model organism phenotype data.

**Reasoning**: Prioritize 1:1 orthologs as high-confidence functional equivalents. For 1:many cases, report all copies and flag the need for paralog-specific functional analysis. If no Ensembl Compara entry exists, try BLAST as a last resort (note: BLAST protein search against swissprot is slow, 5-30 minutes; against nr may take longer).

Key model organisms to check: mouse (taxon 10090), rat (10116), zebrafish (7955), fruit fly (7227), C. elegans (6239), S. cerevisiae (4932).

---

## Phase 3: Sequence Retrieval

Use `NCBI_search_nucleotide` (takes `organism` as full name, e.g., "Homo sapiens"; `gene`; `seq_type` = "mRNA") to find sequence records, then `NCBI_fetch_accessions` to convert UIDs to accession numbers, then `NCBI_get_sequence` to retrieve FASTA data. Prefer RefSeq (NM_* for mRNA, NP_* for protein) over other accessions for canonical sequence.

When aligned sequences are needed directly, `ensembl_get_homology` with `sequence="cdna"` or `sequence="protein"` is faster than running BLAST. Use BLAST only when Ensembl Compara does not find orthologs.

---

## Phase 4: Functional Annotation Comparison

`UniProt_search` takes a query in UniProt syntax (e.g., `"gene:TP53 AND organism_id:9606 AND reviewed:true"`) and `fields` to retrieve specific annotation columns including GO terms. Use `reviewed:true` to restrict to Swiss-Prot curated entries.

`UniProt_get_function_by_accession` takes a UniProt accession and returns a list of function description strings (not a dict).

For each species being compared, retrieve GO terms and group them by Biological Process (BP), Molecular Function (MF), and Cellular Component (CC). Shared GO terms indicate conserved function; terms present in human but absent in the ortholog may reflect annotation bias (less-studied organisms have fewer GO annotations) rather than true functional divergence. Focus conservation claims on shared terms.

**Reasoning about annotation gaps**: If a mouse ortholog lacks a GO term present in the human protein, consider that this may reflect incomplete annotation of the mouse gene rather than functional divergence. The inverse — a GO term in mouse that is absent in human — is less common but can indicate diverged or acquired function.

---

## Phase 5: Cross-Species Phenotype Bridging

`Monarch_search_gene` (takes `query` as gene symbol) returns gene CURIEs needed for Monarch queries. `Monarch_get_gene_phenotypes` and `Monarch_get_gene_diseases` take a gene CURIE (e.g., "HGNC:11998") and return phenotype/disease associations spanning multiple species.

Phenotype ontologies by species: Human = HP (HPO), Mouse = MP (Mammalian Phenotype), Zebrafish = ZP, Fly = FBcv. Monarch integrates across species; compare phenotype themes (e.g., "tumor susceptibility" in human and "increased tumor incidence" in mouse) rather than requiring exact term matches.

**Reasoning for model organism selection**: A mouse ortholog that has a 1:1 relationship AND shows phenotypes in Monarch that recapitulate the human disease is a strong disease model candidate. If the mouse phenotype diverges significantly from the human disease phenotype, this is worth flagging — it could indicate species-specific function or a limitation of the model.

---

## Phase 6: Gene Tree & Evolutionary Context

`EnsemblCompara_get_gene_tree` (takes `gene`, `species`) returns the gene tree members, species distribution, and speciation vs. duplication events. `EnsemblCompara_get_paralogues` returns all paralogs in the source species.

From the gene tree, assess: (1) how many species contain a member of this gene family; (2) when gene duplication events occurred (ancient vs. recent); (3) whether the gene family expanded in particular lineages. A gene present in a single copy across all vertebrates (deep conservation, no duplication) is likely under strong selective constraint.

---

## Synthesis Questions

When interpreting the assembled evidence, work through these questions:

1. Is the ortholog relationship 1:1 or has duplication created paralogs that may have diverged in function? This determines how directly findings in the model organism translate to the human gene.
2. Do orthologs share conserved GO terms (especially Biological Process), or are there lineage-specific functional annotations suggesting divergence?
3. For disease gene studies, does the model organism ortholog recapitulate relevant human phenotypes (via Monarch), supporting its use as a disease model?
4. Are non-coding regulatory regions around the gene also conserved (PhastCons/GERP from OpenCRAVAT), suggesting conservation of gene regulation beyond protein function?
5. If no ortholog is found, is the gene truly lineage-specific, or might a highly divergent homolog exist that is only detectable by sensitive sequence methods?

---

## Fallback Strategies

- **Ortholog not found in Ensembl Compara**: Try `ensembl_get_homology`, then `OpenTargets_get_target_homologues_by_ensemblID`, then BLAST as last resort
- **Sequence retrieval fails**: Use `ensembl_get_homology` with `sequence="cdna"` as alternative to NCBI
- **UniProt returns empty with reviewed:true**: Try without that filter; organism may have only TrEMBL entries
- **Monarch returns no data**: Use `MonarchV3_get_associations` with `category="biolink:GeneToPhenotypicFeatureAssociation"` as alternative
- **Gene symbol ambiguous across species**: Use Ensembl IDs throughout to avoid symbol confusion (e.g., "p53" vs "tp53" in zebrafish)

---

## Limitations

- **Ensembl Compara**: Best for vertebrates; invertebrate and plant coverage is limited for some gene families
- **BLAST_protein_search**: Very slow (5-30 min); use only as last resort for ortholog discovery
- **Monarch**: Phenotype coverage varies by organism; mouse and zebrafish are best covered; fly and worm data are sparser
- **UniProt GO annotations**: Bias toward well-studied organisms; absence of annotation does not mean absence of function
- **NCBI_search_nucleotide**: May return many isoforms; filter for RefSeq (NM_*) for canonical transcripts
- **Conservation does not equal essentiality**: Some highly conserved genes are dispensable in specific organisms
