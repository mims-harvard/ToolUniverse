---
name: tooluniverse-model-organism-genetics
description: Cross-species genetic analysis using model organism databases. Maps human genes to orthologs in mouse, fly, worm, zebrafish, yeast, and frog, then retrieves phenotypes, expression, and functional data from MGI, FlyBase, WormBase, ZFIN, SGD, and Xenbase. Use when users ask about model organisms, gene orthologs, mouse phenotypes, fly genetics, worm RNAi, zebrafish morphants, cross-species comparison, animal models for human disease, or conservation of gene function.
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Model Organism Genetics Pipeline

Map human genes to model organism orthologs and retrieve phenotype, expression, and functional data across six species. Synthesize cross-species evidence to assess gene function conservation and identify the best animal models for studying human genes and diseases.

**Not for**: human variant interpretation (`tooluniverse-variant-analysis`), drug target validation (`tooluniverse-drug-target-validation`), human disease characterization (`tooluniverse-multiomic-disease-characterization`).

**LOOK UP, DON'T GUESS**: When asked about a species' taxonomy, ecology, or biology, search GBIF/NCBI Taxonomy first. For GBIF: use `GBIF_search_species(query="species name")`, then use the `nubKey` (not `key`) from the result to call `GBIF_get_species(speciesKey=nubKey)` for full taxonomy (kingdom, phylum, class, order, family). The `nubKey` is the GBIF backbone key; the `key` is dataset-specific and often lacks higher taxonomy.

---

## Reasoning Principles

### Ortholog Reasoning
Sequence conservation across species implies functional conservation — but not always. A highly conserved gene in mouse and human likely has the same function. But regulatory differences (when/where a gene is expressed) can cause different phenotypes even from the same gene. Always check: is the protein domain conserved, or just raw sequence? Are there known regulatory differences? A 40% identity ortholog with a conserved catalytic domain can be more functionally equivalent than a 90% identity paralog in the same species.

Paralog contamination is a common pitfall. Gene families (e.g., FOXP1/2/3/4, HOX clusters) generate false ortholog hits. Distinguish true orthologs from paralogs by checking synteny (conserved gene neighborhood) and homology type: 1:1 = likely true ortholog; 1:many or many:many = likely paralog expansion. If the target species has a single gene where humans have multiple (e.g., one fly FoxP vs four human FOXPs), it is the co-ortholog of all human paralogs — note this explicitly.

### Model Organism Selection
Choose your model by the question:
- **Mouse**: mammalian physiology, drug testing, immune system, CNS disease — best when you need human-like biology
- **Fly**: genetic screens, signaling pathways (Notch, Wnt, Hh first characterized here), neural circuits, aging — best for rapid genome-wide genetics
- **Worm**: cell lineage, apoptosis, RNAi screens, aging — best when you need single-cell resolution and mapped connectome
- **Zebrafish**: development, organ formation, live imaging, cardiac biology — best when you need vertebrate biology with optical access
- **Yeast**: cell cycle, DNA repair, metabolism, protein trafficking, chromatin — best for fundamental cell biology
- **Frog (Xenopus)**: early development, cell signaling, oocyte biochemistry — note X. laevis is allotetraploid (two homeologs: .L and .S)

Invertebrates (fly, worm, yeast) lack adaptive immunity and many vertebrate-specific organs — if the question involves those systems, they will be uninformative.

### Phenotype Transfer Reasoning
A knockout phenotype in mouse does not automatically predict the human phenotype. Ask three questions before inferring cross-species relevance:
1. **Is the pathway conserved?** A mouse cardiac phenotype only predicts human cardiac disease if the same developmental pathway operates in both hearts.
2. **Are there compensating paralogs?** If the mouse has one gene but humans have three paralogs, a mouse knockout can be more severe than loss of a single human paralog. Conversely, if humans lost a paralog that mice retain, the mouse KO may overpredict human phenotype.
3. **Is the gene dosage-sensitive?** Haploinsufficiency in mouse (heterozygous phenotype) is a stronger predictor of human dominant disease than phenotypes seen only in homozygous knockouts.

When phenotypes differ across species, consider regulatory divergence: the coding sequence may be conserved while the expression pattern has shifted. This can produce organisms with the "same gene" but different tissues of expression and therefore different phenotypes.

---

## Pipeline

### Phase 0: Human Gene Disambiguation (ALWAYS FIRST)

1. `MyGene_query_genes(query="<gene>")` — get Ensembl ID, Entrez ID, UniProt, symbol (filter by `symbol` match; first hit may be a pseudogene)
2. `ensembl_lookup_gene(gene_id="<ensembl_id>", species="homo_sapiens")` — validate
3. If disease context: `HPO_search_terms(query="<disease>")` — get HPO terms for phenotype matching

Fallback if gene not found: `UniProt_search(query="<gene>", organism="9606")`

**Output**: canonical symbol, Ensembl ID (ENSG), Entrez ID, UniProt accession.

---

### Phase 1: Ortholog Mapping

**Primary**: `EnsemblCompara_get_orthologues(gene="<ENSG>", species="human", target_species="<species>")`

Accepted `target_species` values: `"mouse"`, `"zebrafish"`, `"drosophila_melanogaster"` (NOT "fruitfly" — returns HTTP 400), `"caenorhabditis_elegans"`, `"saccharomyces_cerevisiae"`, `"xenopus_tropicalis"`

**Fallbacks** (if Ensembl Compara returns no results):
1. `PANTHER_ortholog(gene_id="<symbol>", organism=9606, target_organism=<taxon>)` — taxon IDs: mouse=10090, fly=7227, worm=6239, zebrafish=7955, yeast=559292, frog=8364
2. `NCBIDatasets_get_orthologs(gene_id="<entrez_id>")` — broad, all vertebrates
3. For fly: `FlyMine_search(query="<human_gene_symbol>")` — text search finds distant orthologs that automated tools miss; confirm with `FlyBase_get_gene_orthologs`
4. For worm: `WormBase_get_gene(gene_id="<gene_symbol>")` — gene record often contains ortholog info

**Cross-reference via Monarch**:
- `Monarch_search_gene(query="<gene_symbol>")` — get Monarch gene entity
- `MonarchV3_get_associations(subject="HGNC:<id>", category="biolink:GeneHomologAssociation")` — all orthologs

Note: "No ortholog found by tools" is not the same as "no ortholog exists." Sequence divergence does not equal functional divergence. Try manual search before concluding absence.

---

### Phase 2: Mouse Phenotypes (MGI)

1. `MGI_search_genes(query="<mouse_symbol>")` — confirm MGI ID
2. `MGI_get_gene(gene_id="MGI:XXXXXXX")` — full gene details
3. `MGI_get_phenotypes(gene_id="MGI:XXXXXXX", limit=50)` — knockout/transgenic phenotypes

Extract: MP ontology terms, allele types (null KO, conditional KO, point mutation), zygosity, lethality, disease model relevance.

Supplement via Monarch:
- `MonarchV3_get_associations(subject="MGI:XXXXXXX", category="biolink:GeneToPhenotypicFeatureAssociation")`
- `MonarchV3_get_associations(subject="MGI:XXXXXXX", category="biolink:GeneToDiseaseAssociation")`

---

### Phase 3: Invertebrate Models

#### Fly (FlyBase)
1. `FlyBase_get_gene(gene_id="FB:FBgnXXX")` — gene details, function summary
2. `FlyBase_get_gene_alleles(gene_id="FB:FBgnXXX", limit=20)` — LOF, GOF, RNAi lines
3. `FlyBase_get_gene_disease_models(gene_id="FB:FBgnXXX")` — human disease models in fly
4. `FlyBase_get_gene_expression(gene_id="FB:FBgnXXX")` — tissue/stage expression
5. `FlyBase_get_gene_interactions(gene_id="FB:FBgnXXX")` — genetic and physical interactions

#### Worm (WormBase)
1. `WormBase_get_gene(gene_id="WBGene00XXXXXX")` — gene details, concise description
2. `WormBase_get_phenotypes(gene_id="WBGene00XXXXXX")` — RNAi and mutant phenotypes
3. `WormBase_get_expression(gene_id="WBGene00XXXXXX")` — expression pattern

---

### Phase 4: Vertebrate Non-Mammalian Models

#### Zebrafish (ZFIN)
1. `ZFIN_get_gene(gene_id="ZFIN:ZDB-GENE-XXXXXX-X")`
2. `ZFIN_get_gene_phenotypes(gene_id="...", limit=30)` — morpholino/CRISPR/mutant phenotypes
3. `ZFIN_get_gene_expression(gene_id="...")` — spatiotemporal expression

Distinguish: morpholino knockdown (rapid, potential off-target), CRISPR mutant (more reliable), ENU mutant (unbiased forward genetics).

#### Frog (Xenbase)
1. `Xenbase_search_genes(query="<gene_symbol>")`
2. `Xenbase_get_gene(gene_id="<xenbase_id>")` — gene details, expression, phenotypes

---

### Phase 5: Yeast (SGD)

1. `SGD_search(query="<gene_symbol>", category="gene")`
2. `SGD_get_gene(sgd_id="<sgd_id>")` — function, pathway
3. `SGD_get_phenotypes(sgd_id="<sgd_id>")` — deletion and overexpression phenotypes
4. `SGD_get_go_annotations(sgd_id="<sgd_id>")` — GO terms (often best-characterized for conserved genes)
5. `SGD_get_interactions(sgd_id="<sgd_id>")` — synthetic lethal partners = potential drug targets

Most informative for: cell cycle, DNA repair, protein folding, metabolism, autophagy, secretory pathway, chromatin. Not informative for: multicellular processes (development, immunity, neural function).

---

### Phase 6: Cross-Species Synthesis (CRITICAL)

This phase transforms per-organism data into biological insight.

**Step 1: Build the phenotype matrix**

| Feature | Human | Mouse | Fly | Worm | Zebrafish | Yeast |
|---------|-------|-------|-----|------|-----------|-------|
| Ortholog present? | — | | | | | |
| LOF lethality | | | | | | |
| Primary phenotype | | | | | | |
| Expression domain | | | | | | |

**Step 2: Identify the core/ancestral function**
Look for the phenotype that is most consistent across species. Abstract from species-specific terms:
- Mouse "reduced vocalization" + Fly "defective courtship song" + Human "speech apraxia" → **core: motor circuit development for learned sequences**
- Mouse "embryonic lethal" + Worm "lethal" + Yeast "essential" → **core: fundamental cell viability**
- Mouse "cardiac defects" + Zebrafish "heart edema" + Human "cardiomyopathy" → **core: cardiac development**

**Step 3: Cross-species phenotype mapping**
Different species use different ontologies (HPO, MP, FBcv, WBPhenotype, ZP). Use `MonarchV3_phenotype_similarity_search` to find equivalent phenotypes via the uPheno ontology. When automated mapping fails, use biological reasoning to find conceptual equivalents.

**Step 4: Conservation assessment**
- Highly conserved: ortholog in all 6 species, consistent phenotypes, shared pathways
- Vertebrate-specific: ortholog in mouse/fish/frog but not fly/worm/yeast
- Metazoan-specific: ortholog in mouse/fish/fly/worm but not yeast
- Human-specific: no clear ortholog in any model organism

**Step 5: Pathway conservation check**
- `STRING_get_network(identifiers="<human_gene> <mouse_ortholog> <fly_ortholog>", species=9606)` — check if interaction partners are also conserved
- `ReactomeAnalysis_pathway_enrichment(identifiers="<human_gene> <ortholog1> <ortholog2>")` — shared pathway membership

**Step 6: Organism recommendation**
Recommend which organism(s) to use for further study. Consider: phenotype match to human condition, available genetic tools, complementary models (e.g., mouse for physiology + fly for genetic screens), practical considerations (cost, throughput, imaging).

---

### Phase 7: Human Disease Connection (Optional)

- `OMIM_search(query="<gene_symbol>")` — Mendelian disease associations
- `ClinVar_search_variants(query="<gene_symbol>")` — pathogenic variants
- `ClinGen_search_gene_validity(gene="<gene_symbol>")` — gene-disease validity (Definitive/Strong/Moderate/Limited)
- `HPO_search_terms(query="<disease_name>")` — phenotype terms for cross-species comparison

Map HPO terms back to model organism phenotypes (Phase 6) to assess model fidelity.

---

## Bacterial and Classical Genetics Reasoning

These problems require computation and logical deduction, not database lookups. Work through the logic step by step.

### Hfr Conjugation and Chromosome Mapping

**Time-of-entry mapping**: In Hfr x F- crosses, genes transfer in a fixed linear order from the integrated F factor origin. Interrupted mating at different times reveals gene order and map distances (1 minute ~ 1 map unit on the circular E. coli chromosome, ~47 kb).

Key reasoning steps:
1. **Gene order** = order of appearance in recombinants as mating time increases
2. **Map distance** = difference in entry times (minutes) between consecutive markers
3. **Directionality**: Different Hfr strains have F integrated at different positions and orientations. Compare gene orders from multiple Hfr strains to construct the circular map. If Hfr1 transfers A-B-C and Hfr2 transfers C-B-A, their F factors are integrated at opposite orientations near the same site.
4. **F' formation**: Imprecise excision of F captures adjacent chromosomal genes. An F' carrying gene X means X was adjacent to the F integration site. F' x F- = partial diploid (merodiploid) for the carried region -- use for complementation/dominance tests.
5. **Recombinant selection**: Only recombinants that integrate donor markers by double crossover (or even number) are stable. The selected marker must be the LAST to enter (closest to Hfr origin = first to enter is WRONG -- the selected marker is the one you plate for, which requires full transfer or recombination).

### Operon Regulation and Attenuation

**lac operon logic** (negative inducible):
- Repressor (lacI) binds operator (lacO) in absence of inducer (allolactose)
- lacI+ is trans-dominant over lacI- (repressor diffuses)
- lacOc (operator constitutive) is cis-dominant (only affects genes on same DNA molecule)
- In partial diploids: determine genotype of EACH DNA molecule separately, then combine

**trp operon attenuation** (leader peptide mechanism):
- Leader transcript has 4 regions (1-2-3-4) that form alternative stem-loops
- Region 1 encodes a short peptide rich in Trp codons
- High Trp: ribosome translates quickly through region 1-2, region 3-4 forms TERMINATOR hairpin -> transcription stops
- Low Trp: ribosome stalls at Trp codons in region 1, region 2-3 forms ANTITERMINATOR hairpin -> transcription continues
- No ribosome (in vitro): region 1-2 pairs, then 3-4 pairs -> termination (default)
- Key: the ribosome's position relative to the mRNA folding regions determines which stem-loops form

**Catabolite repression**: Even with inducer present, lac operon requires cAMP-CAP for full expression. High glucose -> low cAMP -> low expression. This is POSITIVE regulation layered on top of the negative repressor system.

### Gene Mapping from Cross Data

**Three-point cross** (most common exam problem):
1. Identify the 8 phenotypic classes and their frequencies
2. Parentals = two most frequent classes
3. Double crossovers = two least frequent classes
4. Compare double crossovers to parentals to find the MIDDLE gene (the gene whose allele has switched relative to parentals in the DCO class)
5. Map distances: (single CO region 1 + DCO) / total = distance 1; (single CO region 2 + DCO) / total = distance 2
6. Coefficient of coincidence = observed DCO / expected DCO; Interference = 1 - CoC

**Cotransduction frequency** (phage P1 mapping in bacteria):
- Higher cotransduction frequency = genes are closer together
- Wu's formula: cotransduction freq = (1 - d/L)^3, where d = distance, L = phage headful size (~2.5 min for P1)
- If two genes are cotransduced 50% of the time: d = L(1 - 0.5^(1/3)) ~ 0.5 min

## Completeness Checklist

Before finalizing any report:
- [ ] Human gene resolved to Ensembl ID, Entrez ID, UniProt, symbol
- [ ] Ortholog mapping attempted for all requested species; confidence level noted (1:1, 1:many, none)
- [ ] Phenotype data retrieved for each species with orthologs
- [ ] "No ortholog" or "No data" explicitly stated (not silently omitted)
- [ ] Cross-species conservation summary provided
- [ ] Organism recommendation given if disease context provided
- [ ] Evidence graded: T1 = direct experimental (KO phenotype), T2 = genetic screen, T3 = computational orthology, T4 = sequence similarity only
