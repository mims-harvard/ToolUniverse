---
name: tooluniverse-comparative-genomics
description: Cross-species gene and sequence comparison, ortholog analysis, and evolutionary conservation assessment using ToolUniverse tools. Use when comparing genes across species, finding orthologs, analyzing evolutionary conservation, or performing comparative functional annotation.
---

# Comparative Genomics & Ortholog Analysis

Cross-species gene comparison, ortholog identification, sequence retrieval, and functional conservation analysis integrating Ensembl Compara, NCBI, UniProt, OLS, Monarch, and OpenTargets.

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

## Core Tools Integrated

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| **ensembl_lookup_gene** | Gene info by ID/symbol | `gene_id`, `species` (required for symbols) |
| **EnsemblCompara_get_orthologues** | Find orthologs across species | `gene`, `species`, `target_species` |
| **EnsemblCompara_get_paralogues** | Find paralogous genes | `gene`, `species` |
| **EnsemblCompara_get_gene_tree** | Phylogenetic gene tree | `gene`, `species` |
| **ensembl_get_homology** | Homology with sequences | `species`, `symbol`, `target_species`, `type` |
| **OpenTargets_get_target_homologues_by_ensemblID** | OpenTargets ortholog data | `ensemblId` |
| **UniProt_search** | Cross-species protein search | `query` (UniProt syntax), `organism` |
| **UniProt_get_function_by_accession** | Protein function annotation | `accession` |
| **NCBI_search_nucleotide** | Sequence discovery | `organism`, `gene`, `keywords` |
| **NCBI_get_sequence** | Retrieve nucleotide sequence | `accession_id`, `format` |
| **NCBI_fetch_accessions** | Get accession numbers from UIDs | `uids` |
| **BLAST_protein_search** | Sequence similarity search | `sequence`, `database`, `hitlist_size` |
| **ols_search_terms** | Search ontology terms (GO, etc.) | `query`, `ontology` |
| **ols_get_term_info** | Get GO term details | `term_id`, `ontology` |
| **Monarch_search_gene** | Find gene CURIE for Monarch | `query` |
| **Monarch_get_gene_phenotypes** | Cross-species phenotypes | `subject` (gene CURIE) |
| **Monarch_get_gene_diseases** | Gene-disease associations | `subject` (gene CURIE) |
| **MonarchV3_get_associations** | Cross-species associations | `subject`, `category` |

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
Report: Conservation summary with ortholog table, functional comparison, phenotype bridging
```

---

## Phase 1: Gene Identification & Validation

**Objective**: Validate the input gene and retrieve its Ensembl ID, description, and basic metadata.

### Tools Used

**ensembl_lookup_gene**:
- **Input**: `gene_id` (symbol like "BRCA1" or Ensembl ID like "ENSG00000012048"), `species` ("homo_sapiens" -- REQUIRED for symbols)
- **Output**: Gene metadata (Ensembl ID, description, biotype, chromosome, start, end, strand)
- **Critical**: The `species` parameter is REQUIRED when using gene symbols. Omitting it causes errors.

### Workflow

1. Look up gene in reference organism (default: human)
2. Extract Ensembl gene ID for downstream queries
3. Note gene description, biotype, and chromosomal location

### Decision Logic

- **Gene symbol input**: Use `ensembl_lookup_gene` with `species="homo_sapiens"`
- **Ensembl ID input**: Use `ensembl_lookup_gene` directly (species auto-detected)
- **Gene not found**: Try alternative symbols or check spelling; suggest UniProt_search as fallback
- **Non-human reference**: Adjust `species` parameter (e.g., "mus_musculus", "danio_rerio")

---

## Phase 2: Ortholog Discovery

**Objective**: Find orthologous genes in target species using multiple sources.

### Tools Used

**EnsemblCompara_get_orthologues** (primary):
- **Input**:
  - `gene`: Gene symbol or Ensembl ID (e.g., "BRCA1" or "ENSG00000012048")
  - `species`: Source species (default: "human")
  - `target_species`: Specific target (e.g., "mouse", "zebrafish") -- optional, omit for all species
  - `target_taxon`: NCBI taxon ID to limit search (e.g., 10090 for mouse)
- **Output**: Ortholog list with target gene IDs, species, homology type (one2one, one2many, many2many), and taxonomy divergence level

**ensembl_get_homology** (with sequence data):
- **Input**:
  - `species`: Source species ("human")
  - `symbol`: Gene symbol ("BRCA1")
  - `target_species`: Target species (optional)
  - `type`: "orthologues" or "paralogues"
  - `sequence`: Include sequences ("cdna" or "protein")
  - `aligned`: Return aligned sequences (true/false)
- **Output**: Homologs with gene/protein IDs, chromosomal locations, and optionally aligned sequences
- **Use**: When you need sequence-level comparison alongside ortholog mapping

**OpenTargets_get_target_homologues_by_ensemblID** (supplementary):
- **Input**: `ensemblId` (e.g., "ENSG00000141510")
- **Output**: Homolog data from OpenTargets (may include model organism phenotype data)
- **Use**: Cross-reference orthologs and get druggability context

### Workflow

1. Query EnsemblCompara_get_orthologues for the gene
2. If specific target species requested, filter to that species
3. If broad comparison requested, retrieve all orthologs
4. Cross-reference with OpenTargets homologues for additional annotation
5. Classify orthologs by homology type:
   - **one2one**: True orthologs (highest confidence for functional equivalence)
   - **one2many**: Gene duplication in target species (functional divergence possible)
   - **many2many**: Complex duplication history (interpret with caution)

### Decision Logic

- **Single target species**: Use `target_species` parameter to filter
- **Multiple targets**: Omit `target_species` to get all, then filter client-side
- **Key model organisms**: Prioritize mouse (10090), rat (10116), zebrafish (7955), fly (7227), worm (6239), yeast (4932)
- **No orthologs found**: Gene may be lineage-specific; note this as a finding (not an error)
- **one2many orthologs**: Report all paralogs in target with note about functional divergence

---

## Phase 3: Sequence Retrieval

**Objective**: Retrieve nucleotide or protein sequences for the reference gene and its orthologs.

### Tools Used

**NCBI_search_nucleotide**:
- **Input**: `organism` (e.g., "Homo sapiens"), `gene` (e.g., "BRCA1"), `seq_type` ("mRNA" for transcripts), `limit`
- **Output**: GenBank UIDs for sequence records

**NCBI_fetch_accessions**:
- **Input**: `uids` (array of GenBank UIDs from search)
- **Output**: Accession numbers (RefSeq NM_*, GenBank accessions)

**NCBI_get_sequence**:
- **Input**: `accession_id` (e.g., "NM_007294"), `format` ("fasta" or "genbank")
- **Output**: Sequence data in requested format

**BLAST_protein_search** (for similarity search):
- **Input**: `sequence` (protein sequence, min 10 aa), `database` ("swissprot" for curated, "nr" for comprehensive), `hitlist_size`
- **Output**: BLAST hits with E-values, identities, alignment
- **Note**: NCBI BLAST is SLOW (5-30 minutes). Use "swissprot" or "pdb" for faster results.

### Workflow

1. Search NCBI nucleotide for reference gene mRNA
2. Fetch accession numbers from UIDs
3. Retrieve reference sequence (FASTA format)
4. For each key ortholog (from Phase 2):
   - Search NCBI nucleotide in the target organism
   - Retrieve ortholog sequence
5. Optionally: Use BLAST_protein_search if orthologs not found via Ensembl (sequence-based ortholog discovery)

### Decision Logic

- **Prefer RefSeq**: Filter for NM_* (mRNA) or NP_* (protein) accessions when available
- **BLAST only as fallback**: Use BLAST only when Ensembl Compara does not find orthologs
- **BLAST database choice**: Use "swissprot" for speed; "nr" only for comprehensive but expect 10+ min wait
- **Sequence comparison**: If aligned sequences needed, use `ensembl_get_homology` with `sequence="protein"` and `aligned=true` instead of manual BLAST

---

## Phase 4: Functional Annotation Comparison

**Objective**: Compare functional annotations (GO terms, protein function, domains) between orthologous genes across species.

### Tools Used

**UniProt_search**:
- **Input**: `query` (e.g., `"gene:TP53 AND organism_id:9606 AND reviewed:true"`), `fields` (["accession", "gene_names", "organism_name", "go_p", "go_f", "go_c", "cc_function"])
- **Output**: UniProt entries with GO annotations and function descriptions
- **Use**: Get protein annotations for both reference and ortholog

**UniProt_get_function_by_accession**:
- **Input**: `accession` (UniProt accession, e.g., "P04637")
- **Output**: List of function description strings
- **Note**: Returns a list of strings, NOT a dict

**ols_search_terms**:
- **Input**: `query` (GO term or keyword), `ontology` ("go")
- **Output**: Matching ontology terms with IDs and labels

**ols_get_term_info**:
- **Input**: `term_id` (e.g., "GO:0006915"), `ontology` ("go")
- **Output**: Term details (label, description, synonyms, relationships)

### Workflow

1. For reference gene (human):
   - Search UniProt with `gene:{SYMBOL} AND organism_id:9606 AND reviewed:true`
   - Get function description via UniProt_get_function_by_accession
   - Extract GO terms (BP, MF, CC)
2. For each key ortholog:
   - Search UniProt with `gene:{ORTHOLOG_SYMBOL} AND organism_id:{TAXON} AND reviewed:true`
   - Get function description
   - Extract GO terms
3. Compare:
   - Shared GO terms (conserved function)
   - Human-only GO terms (lineage-specific or annotation gap)
   - Ortholog-only GO terms (diverged or under-annotated in human)
4. For key GO terms of interest, get full details via ols_get_term_info

### Decision Logic

- **Swiss-Prot only**: Use `reviewed:true` in UniProt queries to get curated entries
- **Organism IDs**: Human=9606, Mouse=10090, Rat=10116, Zebrafish=7955, Fly=7227, Worm=6239, Yeast=559292
- **GO term comparison**: Focus on Biological Process (BP) for functional conservation
- **Annotation bias**: Well-studied organisms (human, mouse) have more GO annotations; absence of a term in a less-studied organism does not mean absence of function
- **Empty UniProt results**: Try without `reviewed:true`; some organisms have only TrEMBL entries

---

## Phase 5: Cross-Species Phenotype Bridging

**Objective**: Link human disease/phenotype associations to model organism phenotypes via orthologous genes using Monarch Initiative.

### Tools Used

**Monarch_search_gene**:
- **Input**: `query` (gene symbol, e.g., "TP53"), `limit`
- **Output**: Gene CURIEs (HGNC:*, NCBIGene:*) needed for downstream Monarch queries

**Monarch_get_gene_phenotypes**:
- **Input**: `subject` (gene CURIE, e.g., "HGNC:11998"), `limit`
- **Output**: Human (HP:*) and model organism (MP:* for mouse, ZP:* for zebrafish) phenotypes

**Monarch_get_gene_diseases**:
- **Input**: `subject` (gene CURIE), `limit`
- **Output**: Diseases associated with the gene across species

**MonarchV3_get_associations**:
- **Input**:
  - `subject`: Entity CURIE (e.g., "HGNC:11998")
  - `category`: Biolink association type (e.g., "biolink:GeneToPhenotypicFeatureAssociation", "biolink:GeneToDiseaseAssociation")
  - `limit`: Max results
- **Output**: Cross-species associations with evidence and publications

### Workflow

1. Search Monarch for gene CURIE: `Monarch_search_gene(query="TP53")`
2. Get human phenotypes: `Monarch_get_gene_phenotypes(subject="HGNC:11998")`
3. Get disease associations: `Monarch_get_gene_diseases(subject="HGNC:11998")`
4. For key orthologs, repeat with their species-specific CURIEs
5. Compare:
   - Shared phenotype themes across species (e.g., tumor susceptibility in human and mouse)
   - Species-specific phenotypes (e.g., mouse knockout has embryonic lethality not seen in human heterozygotes)
   - Disease model relevance (does the mouse ortholog phenotype recapitulate the human disease?)

### Decision Logic

- **CURIE format**: Human genes use HGNC:* or NCBIGene:*; mouse uses MGI:*; zebrafish uses ZFIN:*
- **Phenotype ontologies**: Human=HP (Human Phenotype Ontology), Mouse=MP (Mammalian Phenotype), Zebrafish=ZP
- **Cross-species bridging**: Monarch integrates across species; look for phenotype themes not exact term matches
- **Empty results**: Some genes have limited phenotype annotation in Monarch; note and continue

---

## Phase 6: Gene Tree & Evolutionary Context

**Objective**: Assess evolutionary history and conservation breadth of the gene family.

### Tools Used

**EnsemblCompara_get_gene_tree**:
- **Input**: `gene` (symbol or Ensembl ID), `species` (default: "human")
- **Output**: Gene tree members across species, tree structure, speciation/duplication events

**EnsemblCompara_get_paralogues**:
- **Input**: `gene`, `species`
- **Output**: Paralogous genes within the same species (from gene duplication events)

### Workflow

1. Retrieve gene tree for the reference gene
2. Extract tree members and count species represented
3. Identify duplication events vs speciation events
4. Retrieve paralogues to understand gene family expansion
5. Summarize:
   - Conservation depth (vertebrates only? All eukaryotes? Bacteria?)
   - Gene family size (number of paralogues)
   - Duplication history (recent vs ancient duplications)

### Decision Logic

- **Large gene families**: Gene tree may have hundreds of members; focus on key model organisms
- **Conservation depth**: More species = more conserved = likely essential function
- **Recent duplications**: Paralogs from recent duplications may have redundant function (backup)
- **No tree found**: Gene may be too divergent or lineage-specific; note this finding

---

## Output Structure

### Report Format

**Progressive Markdown Report**:

```markdown
# Comparative Genomics Report: {GENE_SYMBOL}

**Reference Species**: {species}
**Date**: {date}

---

## 1. Gene Overview
| Property | Value |
|----------|-------|
| Symbol | {symbol} |
| Ensembl ID | {ensembl_id} |
| Description | {description} |
| Chromosome | {chr}:{start}-{end} |
| Biotype | {biotype} |

---

## 2. Orthologs

### Ortholog Table
| Species | Gene Symbol | Ensembl ID | Homology Type | Taxonomy Level |
|---------|-------------|------------|---------------|---------------|
| Mouse | {symbol} | {id} | one2one | Euarchontoglires |
| Zebrafish | {symbol} | {id} | one2many | Vertebrata |
| ... | ... | ... | ... | ... |

### Conservation Summary
- Total species with orthologs: {N}
- one2one orthologs: {N} species
- Deepest conservation: {taxonomic group}

---

## 3. Sequence Data
| Organism | Accession | Type | Length |
|----------|-----------|------|--------|
| Human | NM_* | mRNA | {len} |
| Mouse | NM_* | mRNA | {len} |

---

## 4. Functional Comparison

### GO Term Conservation
| GO Term | Category | Human | Mouse | Zebrafish |
|---------|----------|-------|-------|-----------|
| GO:000XXXX | BP | Y | Y | Y |
| GO:000YYYY | MF | Y | Y | N |

### Conserved Functions
- {shared functions}

### Diverged or Lineage-Specific Annotations
- {species-specific annotations}

---

## 5. Cross-Species Phenotypes (Monarch)

### Human Phenotypes (HP)
| HPO ID | Phenotype |
|--------|-----------|
| HP:000XXXX | {phenotype} |

### Mouse Phenotypes (MP)
| MP ID | Phenotype |
|-------|-----------|
| MP:000XXXX | {phenotype} |

### Phenotype Conservation Assessment
- {shared phenotype themes}
- {model organism relevance}

---

## 6. Evolutionary Context
- Gene tree species count: {N}
- Paralogues in human: {N}
- Conservation depth: {taxonomic level}
- Key duplication events: {description}

---

## References
| Tool | Parameters | Phase |
|------|-----------|-------|
| ... | ... | ... |
```

---

## Tool Parameter Reference

**Critical Parameter Notes** (verified):

| Tool | Parameter | Correct | Common Mistake |
|------|-----------|---------|----------------|
| ensembl_lookup_gene | `species` | REQUIRED for symbols | Omitting causes error |
| EnsemblCompara_get_orthologues | `gene` | String (symbol or ID) | - |
| EnsemblCompara_get_orthologues | `target_species` | Optional string | - |
| ensembl_get_homology | `species` + `symbol` | Both REQUIRED | Missing `species` |
| UniProt_search | `query` | UniProt syntax | Free-text without field prefixes |
| UniProt_get_function_by_accession | `accession` | UniProt accession | Returns list of strings, NOT dict |
| NCBI_search_nucleotide | `organism` | Full name ("Homo sapiens") | Short name ("human") |
| BLAST_protein_search | `sequence` | Min 10 amino acids | Too short sequences |
| Monarch_search_gene | `query` | Gene symbol | Ensembl ID (not supported) |
| MonarchV3_get_associations | `category` | Full Biolink URI | Short name |

---

## Fallback Strategies

### Ortholog Discovery
- **Primary**: EnsemblCompara_get_orthologues
- **Fallback 1**: ensembl_get_homology (includes sequence data)
- **Fallback 2**: OpenTargets_get_target_homologues_by_ensemblID
- **Fallback 3**: BLAST_protein_search against swissprot (slow, 5-30 min)

### Sequence Retrieval
- **Primary**: NCBI_search_nucleotide + NCBI_fetch_accessions + NCBI_get_sequence
- **Fallback**: ensembl_get_homology with `sequence="cdna"` or `sequence="protein"`

### Functional Comparison
- **Primary**: UniProt_search with GO fields
- **Fallback**: ols_search_terms for individual GO term lookup

### Phenotype Bridging
- **Primary**: Monarch_get_gene_phenotypes (includes cross-species)
- **Fallback**: MonarchV3_get_associations with GeneToPhenotypicFeatureAssociation
- **If no Monarch data**: Use OpenTargets phenotype endpoints

---

## Common Use Patterns

### Pattern 1: Quick Ortholog Lookup
```
Input: Gene symbol + target species
Workflow: Phase 1 → Phase 2 (filtered to target)
Output: Ortholog gene ID, homology type, taxonomy level
```

### Pattern 2: Model Organism Selection
```
Input: Human disease gene
Workflow: Phase 1 → Phase 2 (all species) → Phase 5 (Monarch phenotypes)
Output: Ranked model organisms by ortholog type and phenotype recapitulation
```

### Pattern 3: Full Conservation Analysis
```
Input: Gene symbol
Workflow: All phases (1-6)
Output: Comprehensive report with orthologs, sequences, functional comparison, phenotypes, evolution
```

### Pattern 4: Functional Divergence Assessment
```
Input: Gene with known one2many orthologs
Workflow: Phase 1 → Phase 2 → Phase 4 (GO comparison for each paralog)
Output: Which paralog retained which functions after duplication
```

### Pattern 5: Cross-Species Disease Model Validation
```
Input: Human disease gene
Workflow: Phase 1 → Phase 2 (mouse) → Phase 4 (function comparison) → Phase 5 (phenotype bridging)
Output: Does the mouse ortholog phenotype match the human disease? Suitable model?
```

---

## Quality Checks

### Data Completeness
- [ ] Gene validated with Ensembl ID obtained
- [ ] Orthologs found (or absence noted as lineage-specific)
- [ ] At least 3 model organisms checked (mouse, zebrafish, fly)
- [ ] Functional annotations retrieved for reference and key orthologs
- [ ] Phenotype data retrieved from Monarch
- [ ] Gene tree or conservation depth assessed
- [ ] All data points cite source tool

### Biological Validity
- [ ] one2one orthologs correctly identified as highest-confidence equivalents
- [ ] one2many cases flagged for potential functional divergence
- [ ] GO term comparison accounts for annotation bias
- [ ] Phenotype comparison uses ontology themes, not exact term matching
- [ ] Conservation depth consistent with known gene family history

---

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **High confidence** | 1:1 ortholog in Ensembl Compara, confirmed by reciprocal best BLAST hit, conserved synteny | Human BRCA1 to mouse Brca1: one2one, same chromosomal context |
| **Moderate confidence** | 1:many ortholog, or ortholog confirmed by one method only | Human TP53 to zebrafish tp53: one2one but distant divergence |
| **Low confidence** | many:many relationship, or sequence similarity only (no Compara entry) | Gene family expansion with unclear functional equivalence |
| **Uncertain** | BLAST hit only (E < 1e-5) without Compara orthology call, or low identity (< 30%) | Distant homolog detected by BLAST in invertebrate, no synteny data |

### Interpretation Guidance

- **Orthology confidence levels**: 1:1 orthologs are the strongest evidence for functional equivalence across species. 1:many orthologs (gene duplicated in target) may have subfunctionalized or neofunctionalized -- do not assume both copies retain the ancestral function. many:many relationships require careful analysis of each paralog pair.
- **Conservation score interpretation (PhastCons)**: PhastCons scores range 0-1; scores > 0.5 indicate evolutionary constraint. Coding exons typically score > 0.8. Non-coding regions with PhastCons > 0.5 are candidate regulatory elements. PhastCons is based on a phylogenetic hidden Markov model and captures conservation across a multi-species alignment.
- **Conservation score interpretation (GERP)**: GERP RS (rejected substitution) scores > 2 indicate strong constraint; > 4 indicates extreme constraint. Negative GERP scores suggest faster-than-neutral evolution (possible positive selection). GERP is per-position and complements PhastCons by providing a continuous constraint measure.
- **Annotation bias caveat**: Well-studied organisms (human, mouse) have richer GO annotations. Absence of a GO term in a less-studied ortholog does not imply loss of function -- it may reflect incomplete annotation. Focus on shared terms for conservation claims.
- **Homology type priority**: For model organism selection, rank by: 1:1 ortholog > 1:many with dominant copy > many:many > sequence similarity only. Phenotype recapitulation in Monarch strengthens the case for a good disease model.

### Synthesis Questions

1. Is the ortholog relationship 1:1 across the species of interest, or has gene duplication created paralogs that may have diverged in function?
2. Do the orthologs share conserved GO annotations (especially Biological Process), or are there lineage-specific functional annotations that suggest divergence?
3. For disease gene studies, does the model organism ortholog recapitulate relevant human phenotypes (via Monarch), supporting its use as a disease model?
4. Are non-coding regulatory regions around the gene also conserved (PhastCons/GERP), suggesting conservation of gene regulation in addition to protein function?
5. If no ortholog is found, is the gene truly lineage-specific, or might the search have missed a highly divergent homolog detectable only by sensitive sequence methods?

---

## Limitations & Known Issues

### Tool-Specific
- **Ensembl Compara**: Best for vertebrates; limited invertebrate/plant coverage for some genes
- **BLAST_protein_search**: Extremely slow (5-30 min); use only as last resort for ortholog discovery
- **Monarch**: Phenotype coverage varies by organism; mouse and zebrafish best, fly/worm sparser
- **UniProt GO annotations**: Bias toward well-studied organisms; absence of annotation does not mean absence of function
- **NCBI_search_nucleotide**: May return many isoforms; filter for RefSeq (NM_*) for canonical transcripts

### Conceptual
- **Ortholog vs paralog**: one2many relationships mean the target species has duplicated the gene; both copies may share function or have diverged
- **Annotation transfer**: Assuming an ortholog has the same function as the reference gene is common but not always correct
- **Conservation does not equal essentiality**: Some highly conserved genes are dispensable in specific organisms
- **Gene name confusion**: Same gene symbol may refer to different genes in different species (e.g., "p53" vs "tp53" in zebrafish)
