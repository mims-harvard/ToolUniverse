---
name: tooluniverse-model-organism-genetics
description: Cross-species genetic analysis using model organism databases (MGI mouse, IMPC systematic knockout phenotyping, ZFIN zebrafish, FlyBase fruit fly, WormBase worm, SGD budding yeast plus protein-domain/PTM/literature detail, PomBase fission yeast, RGD rat, GeneNetwork systems-genetics/eQTL panels, HumanMine/MouseMine cross-species data-warehouse search, GBIF taxonomy) plus VEuPathDB for eukaryotic pathogens (Plasmodium, Toxoplasma, fungi, vectors). Maps human genes to orthologs, retrieves phenotype/expression/functional data, assesses gene function conservation, and identifies the best animal model for studying a human gene or disease.
disable-model-invocation: true
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# Model Organism Genetics Pipeline

Map human genes to model organism orthologs and retrieve phenotype, expression, and functional data across six species. Synthesize cross-species evidence to assess gene function conservation and identify the best animal models for studying human genes and diseases.

**Not for**: human variant interpretation (`tooluniverse-variant-analysis`), drug target validation (`tooluniverse-drug-target-validation`), human disease characterization (`tooluniverse-multiomic-disease-characterization`), pathogen outbreak/drug-repurposing intelligence once a VEuPathDB target gene is identified (`tooluniverse-infectious-disease`).

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

### Phase 2b: Systematic Knockout Phenotyping (IMPC) — statistically-powered, complements MGI's curated calls

MGI (Phase 2) aggregates curated phenotype annotations from the published literature — heterogeneous alleles, heterogeneous assays, no guarantee every gene was ever tested for every system. IMPC (International Mouse Phenotyping Consortium) is a different kind of evidence: one standardized pipeline (EUCOMM/KOMP-derived null alleles, e.g. `Trp53<tm1b(EUCOMM)Hmgu>`) runs the SAME broad battery of tests (viability, eye morphology, clinical chemistry, behavior, etc.) across thousands of knockout lines at IMPC phenotyping centers, with a p-value and effect size attached to every call. Use IMPC when you need a statistically-defensible answer to "does knocking this gene out actually produce a significant phenotype," not just "has anyone ever reported a phenotype."

1. `IMPC_search_genes(query="<mouse_symbol_or_MGI_ID_or_name_fragment>", limit=20)` — resolve a symbol/name fragment to its MGI ID and human ortholog(s); useful for disambiguation when the mouse symbol alone is uncertain
2. `IMPC_get_gene_summary(gene_symbol="<mouse_symbol>")` (or `mgi_id="MGI:XXXXXXX"`) — top-level flags only: `has_phenotype_data`, `phenotype_status`, `production_status`. **Its `mp_terms`/`mp_ids`/`top_level_mp_terms` arrays are empty even when `has_phenotype_data` is true** (verified live) — this tool tells you WHETHER data exists, not WHAT it says; always follow up with step 3 or 4 for the actual phenotype list.
3. `IMPC_get_phenotypes_by_gene(gene_symbol="<mouse_symbol>", limit=100)` — the full genotype-phenotype call list: MP term, zygosity, sex, life stage, procedure/parameter, p-value, effect size, phenotyping center, allele symbol; also returns `phenotype_summary_by_system` (MP top-level term -> list of specific phenotypes), useful for a quick systems-level overview before drilling into individual calls
4. `IMPC_get_gene_phenotype_hits(gene_symbol="<mouse_symbol>", significant_only=true, limit=100)` — similar underlying data to step 3 but oriented around the statistical result itself: adds `classification_tag` (plain-language significance/sex-specificity summary), `statistical_method` (e.g. "Linear Mixed Model framework, LME, including Weight", "Fisher Exact Test framework"), and separate `female_ko_estimate`/`male_ko_estimate` when an effect is sex-specific. Set `significant_only=false` to see tested-but-non-significant parameters too (useful for confirming a system was actually screened and came back negative, vs. never tested).

**No gene found / zero results is informative, not an error**: a real gene can legitimately have zero IMPC phenotype calls if its knockout line hasn't reached statistical analysis yet (verified live: `IMPC_get_phenotypes_by_gene(gene_symbol="Braf")` returns `total_phenotype_calls: 0` with `mgi_id: ""` — Braf has an MGI record but no completed IMPC pipeline data at time of writing). State this plainly rather than treating an empty IMPC result as "no phenotype exists" or silently falling back to MGI without saying so.

**Worked example (verified live)**: `IMPC_get_gene_summary(gene_symbol="Trp53")` resolves `MGI:98834`, human ortholog `TP53`. `IMPC_get_phenotypes_by_gene` returns 6 significant calls / 5 unique MP terms across 4 systems: vision/eye (persistence of hyaloid vascular system, p=1.2e-5; abnormal retina morphology, p=1.9e-7), homeostasis/metabolism (decreased circulating creatine kinase, heterozygote-only, p=6.0e-5), mortality/aging (preweaning lethality with incomplete penetrance, p<0.001), and behavior/neurological (increased startle reflex, female-specific effect size 878 vs. male 355, p=1.7e-12). `IMPC_get_gene_phenotype_hits` on the same gene surfaces the same calls with `statistical_method` and sex-split estimates attached, e.g. tagging the startle-reflex result as "significant in females only."

**Workflow**: for any gene already run through Phase 2 (MGI), also run this phase and compare — a phenotype curated in MGI from an old paper but absent from IMPC's systematic screen (or vice versa) is worth flagging explicitly rather than silently preferring one source.

---

### Phase 2c: Broader Data-Warehouse Search (HumanMine / MouseMine) — free-text fallback when structured lookups come up thin

MGI/IMPC (Phases 2/2b) require you to already have a mouse symbol or MGI ID and answer narrow, structured questions (phenotype calls, gene record). HumanMine and MouseMine are general-purpose InterMine data warehouses that integrate 30+ underlying sources (NCBI Gene, Ensembl, UniProt, Reactome, KEGG, GWAS Catalog, publications) behind one free-text search — useful when you don't yet have a clean ID, want pathway/publication hits alongside gene hits, or need a flexible graph query MGI's fixed endpoints don't offer.

1. `HumanMine_search(q="<term>", size=10)` — free-text across genes/proteins/pathways/diseases for **human, mouse, and rat simultaneously**; results are tagged by `organism.shortName` (e.g. `H. sapiens`, `M. musculus`, `R. norvegicus`) so you see cross-species hits in one call. Verified live: `q="TP53"` returns 32 hits split 21 human / 3 mouse / 8 rat.
2. `HumanMine_search_genes(q="<term>", size=10)` / `HumanMine_search_pathways(q="<term>", size=10)` — narrower convenience wrappers filtering to genes-only or pathways-only (Reactome/KEGG-sourced).
3. `MouseMine_search(q="<term>", size=10, format="json")` — the mouse-only InterMine sibling; broader than MGI's own gene/phenotype endpoints because it also indexes publications and pathway membership in the same search.
4. `MouseMine_search_genes(q="<term>", size=10)` — filters to `ProteinCodingGene` only. Verified live on `q="Trp53"` (same gene used in the Phase 2b IMPC example): 180 hits, with a `pathways.name` facet showing `Transcriptional Regulation by TP53`, `G1/S DNA Damage Checkpoints`, etc. — a fast way to see pathway context without a separate Reactome call.
5. `MouseMine_search_alleles(q="<term>", size=10)` — allele/mutant search returning `attributeString` (e.g. `Null/knockout`) and `alleleType` (Targeted, Endonuclease-mediated, Spontaneous, ...). Verified live on `q="Trp53"`: 170 alleles including `Trp53<em2Mvw>` (endonuclease-mediated null).
6. `InterMine_run_pathquery(query="<XML PathQuery>")` — for HumanMine only, an escape hatch to traverse the InterMine data model graph directly (gene→pathways, gene→protein domains, region→features) when the canned search tools don't expose the relationship you need. Requires hand-written XML with `model`, `view`, and `constraint` elements — verified live with the tool's own worked example (`Gene.symbol Gene.pathways.name` constrained to `PAX6`), which correctly returned `PAX6 → Activation of HOX genes during differentiation`, `Developmental Biology`, etc.

Use these as a **fallback/supplement**, not a replacement for Phases 1-2b: MGI/IMPC give you curated, structured, statistically-scored data; HumanMine/MouseMine give you fast free-text triage across a wider net of sources when you're not sure what you're looking for yet. For dedicated human-disease-association work (not just "does this gene show up near this disease term"), hand off to `tooluniverse-gene-disease-association`'s DisGeNET/OpenTargets/Monarch pipeline instead of treating a HumanMine disease-facet hit as a real association.

**Mouse Phenome Database — do not rely on `MPD_get_phenotype_data`'s name at face value.** Despite being registered as an MPD tool, its own description states MPD's real REST API has no simple strain+phenotype-category search, so it substitutes a keyword search against **ENCODE experiment records mentioning the strain name** — this is a weak proxy for actual MPD phenotype measurements, not MPD data itself. Verified live: `strain="C57BL/6J"` succeeds, but `strain="DBA/2J"` reproducibly 404s (the unescaped `/` in the strain name breaks the outgoing ENCODE query URL) — a strain-name-dependent failure, not evidence the strain lacks data. Treat any result from this tool as circumstantial at best; for real cross-strain phenotype comparisons prefer Phase 2b (IMPC) or Phase 2c's GeneNetwork section below, and do not report "no ENCODE hits" as "no phenotype data exists for this strain."

---

### Phase 2d: Systems Genetics / eQTL Across Recombinant Inbred Panels (GeneNetwork)

GeneNetwork is a different data type again: genetic-cross populations (13+ species) with matched genotype + expression/phenotype measurements per individual/strain, used for QTL mapping (which genomic region drives variation in this trait). Its best-known resource is the **BXD family** (C57BL/6J × DBA/2J recombinant inbred mouse strains — note both parental strains are the same C57BL/6J and DBA/2J from the MPD caveat above), but it also covers rat (HXB/BXH), Arabidopsis, and others.

1. `GeneNetwork_list_species()` — no params; verified live returns `{"FullName": "Mus musculus", "Name": "mouse", "TaxonomyId": 10090}` plus rat/human/arabidopsis/etc.
2. `GeneNetwork_list_groups(species="mouse")` — genetic cross populations for that species; verified live returns `BXD` (`GeneticType: "riset"`, i.e. recombinant inbred set) among others.
3. `GeneNetwork_list_datasets(group="bxd")` — tissue/platform-specific datasets for that cross; verified live returns entries like `Long_Abbreviation: "BXDMicroArray_ProbeSet_August03"` (brain expression) alongside phenotype-only datasets (e.g. `BXDPublish`).
4. `GeneNetwork_get_sample_data(dataset_name="<Long_Abbreviation>", trait_name="<probe_or_trait_id>")` — per-strain measurement values with standard errors for one trait across the whole panel.
5. `GeneNetwork_get_trait_info(dataset_name="<...>", trait_name="<...>")` — trait metadata: gene symbol, chromosome/Mb position, `lrs` (LOD-like linkage score), `additive` effect, best `locus` (peak marker) — this is the QTL-mapping result for that trait. Verified live on the tool's own worked example (`HC_M2_0606_P`/`1436869_at` = Shh probe): returns `symbol: "Shh"`, `chr: "5"`, peak `locus: "rs8253327"`, `lrs: 12.77`.
6. `GeneNetwork_get_dataset_info(dataset_name="<...>")` — dataset-level metadata (tissue, platform, data scale, public/confidential status) to confirm you're querying the right dataset before pulling sample data.

Use this phase when the question is specifically "what genomic locus explains strain-to-strain variation in trait X" (classic QTL mapping) rather than "does gene X have a knockout phenotype" (Phase 2/2b) — GeneNetwork answers a genetics-of-variation question, not a loss-of-function question.

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

### Phase 4b: Rat (RGD) — physiology & disease-model strains

Rat is the premier mammalian model for cardiovascular, metabolic, behavioral, and toxicology physiology. RGD's distinctive asset is its curated **strain** catalog (inbred/congenic/consomic lines) annotated as disease models — data not found in MGI or the Alliance.

Gene-level:
1. `RGD_search_genes(query="<gene_symbol>")` then `RGD_get_gene(rgd_id=<id>)` — rat gene details
2. `RGD_get_annotations(rgd_id=<id>)` — disease/phenotype/GO annotations for the gene
3. `RGD_get_orthologs(rgd_id=<id>)` — rat-to-human/mouse orthologs
4. `RGD_get_qtls_in_region(chromosome="1", start=1, stop=10000000, map_key=360)` — QTLs in a region

Strain-level (rat disease models — use when the question is "which rat strain models disease X?"):
5. `RGD_search_strains(query="hypertensive", strain_type="inbred")` — find strains by keyword/type (types: inbred, congenic, consomic, transgenic, recombinant_inbred, ...)
6. `RGD_get_strain(symbol="SHR")` — full record for a named strain (e.g. SHR = spontaneously hypertensive rat, rgd_id 61000; BN = Brown Norway; SS = Dahl salt-sensitive; GK = Goto-Kakizaki diabetes)
7. `RGD_get_strain_annotations(symbol="SHR", category="disease")` — curated disease/phenotype annotations that define the strain as a model

Example — SHR is annotated to `Left Ventricular Hypertrophy` (DOID:9004616, qualifier `MODEL: spontaneous`) and `arterial blood pressure trait` (VT:2000000), making it the canonical model for essential hypertension and its cardiac sequelae.

---

### Phase 5: Yeast (SGD)

1. `SGD_search(query="<gene_symbol>", category="gene")`
2. `SGD_get_gene(sgd_id="<sgd_id>")` — function, pathway
3. `SGD_get_phenotypes(sgd_id="<sgd_id>")` — deletion and overexpression phenotypes
4. `SGD_get_go_annotations(sgd_id="<sgd_id>")` — GO terms (often best-characterized for conserved genes)
5. `SGD_get_interactions(sgd_id="<sgd_id>")` — synthetic lethal partners = potential drug targets

Most informative for: cell cycle, DNA repair, protein folding, metabolism, autophagy, secretory pathway, chromatin. Not informative for: multicellular processes (development, immunity, neural function).

**Protein-level detail (complements the gene-level steps above)** — these three tools take a `locus` string directly (standard gene name, systematic/ORF name, or SGD ID — no separate ID-resolution step needed):
6. `SGD_get_protein_domains(locus="<gene_or_ORF_name>")` — mapped domains from Pfam/InterPro/SMART/PROSITE/CDD/Gene3D/SUPERFAMILY in one call. Verified live on `locus="CDC28"` (the S. cerevisiae ortholog of fission-yeast **cdc2** from the Phase 5b PomBase example): 12 domain hits including Gene3D's "Phosphorylase Kinase; domain 1" and "Transferase(Phosphotransferase) domain 1" — consistent with CDC28's role as the budding-yeast CDK.
7. `SGD_get_ptm_sites(locus="<gene_or_ORF_name>")` — curated post-translational modification sites (phosphorylation, ubiquitination, etc.) with residue, position, reference, and PMID. Verified live on `locus="CDC28"`: 34 sites, e.g. phosphorylated Ser2 (Lanz et al. 2021, PMID:33491328; also independently reported by Leutert et al. 2023, PMID:37845410).
8. `SGD_get_literature(locus="<gene_or_ORF_name>")` — reference counts by curation category (primary, review, additional, etc.), not full citations — use this to gauge how well-studied a gene is before deciding whether to expect rich Phase 5 data. Verified live: `ACT1` has 1659 total references vs. `CDC28`'s 1971 — both heavily studied, unsurprising for essential cell-cycle/cytoskeletal genes.

---

### Phase 5b: Fission Yeast (PomBase) — S. pombe, distinct from SGD's S. cerevisiae

S. pombe (fission yeast) and S. cerevisiae (budding yeast) diverged ~350-450 million years ago and are about as distant from each other as either is from humans for some pathways — S. pombe's cell-cycle and RNAi machinery is often the MORE human-like of the two yeasts, so check both when a Phase 5 (SGD) search comes up thin or when the process in question is cell-cycle/chromatin/RNA-processing-related.

1. `PomBase_search_genes(query="<gene_name_or_keyword>", limit=10)` — search by gene name, systematic-ID prefix (e.g. `"SPAC"`), or product keyword across 12,600+ genes
2. `PomBase_get_gene(gene_id="<systematic_id>")` — gene name, product, InterPro domains, deletion viability, UniProt cross-reference (systematic IDs look like `SPBC11B10.09`, `SPAC2F7.03c`)
3. `PomBase_get_gene_phenotypes(gene_id="<systematic_id>")` — FYPO (Fission Yeast Phenotype Ontology) terms with evidence codes, plus `deletion_viability`
4. `PomBase_get_orthologs(gene_id="<systematic_id>")` — human orthologs (HGNC IDs, taxon 9606) and S. cerevisiae orthologs (systematic name, taxon 4932) in one call — useful for triangulating a human gene through BOTH yeasts at once
5. `PomBase_get_interactions(gene_id="<systematic_id>")` — physical (Affinity Capture-MS etc.) and genetic interactions with evidence, PMID, throughput, source database
6. `PomBase_get_go_annotations(gene_id="<systematic_id>")` — GO terms by aspect (biological_process/molecular_function/cellular_component)

Worked example (verified live): `PomBase_get_gene(gene_id="SPBC11B10.09")` resolves to **cdc2**, the fission-yeast cyclin-dependent kinase. `PomBase_get_orthologs` on the same ID returns human `HGNC:1722`/`HGNC:1771`/`HGNC:1772` (CDK1/CDK2/CDK3 family) and S. cerevisiae `YBR160W` (CDC28) — cdc2 is the founding member of the CDK family, first characterized in fission yeast. `PomBase_get_gene_phenotypes` confirms `deletion_viability: "inviable"` with 60 FYPO terms including "abnormal cell cycle arrest at mitotic G2/M phase transition," consistent with its essential mitotic role. `PomBase_get_interactions` returns 100 physical interactions (e.g. with `red1`/SPAC1006.03c via Affinity Capture-MS, PMID:24713849).

---

### Phase 3b: Eukaryotic Pathogens (VEuPathDB) — malaria, toxoplasmosis, fungi, vectors

VEuPathDB is a family of pathogen/vector/host genome databases (PlasmoDB for *Plasmodium*/malaria, ToxoDB for *Toxoplasma*, FungiDB, VectorBase, CryptoDB, GiardiaDB, MicrosporidiaDB, PiroplasmaDB, TrichDB, TriTrypDB, AmoebaDB) sharing one WDK REST API. This is the right resource when the "model organism" in question is actually a pathogen and the question is about pathogen gene function rather than human-disease-model translation (for outbreak/drug-repurposing intelligence once a target gene is identified, hand off to `tooluniverse-infectious-disease`).

**Live-verified access limitation (read before using):** as of this writing, only `VEuPathDB_list_record_types` works without authentication. The other 4 tools —
`VEuPathDB_list_gene_searches`, `VEuPathDB_list_organism_searches`, `VEuPathDB_search_genes_by_organism`, `VEuPathDB_get_gene_record` — all fail live with `HTTP 401: Valid API Key required for this endpoint`, even though the tool's own module docstring claims "No authentication required." This is an upstream policy change since the tool was written, not a bug in your request, and the tool currently has **no built-in mechanism to supply an API key** (no `required_api_keys`/env-var support in `veupathdb_tool.py`) — so these 4 operations cannot currently be completed by this skill. Verify with a cheap call first:

```
VEuPathDB_list_record_types()  # {} — no params, this one still works
```

If a call to `VEuPathDB_search_genes_by_organism` or `VEuPathDB_get_gene_record` returns a 401, tell the user plainly that VEuPathDB now gates this endpoint and the tool has no key-passing mechanism yet — do not fabricate a gene record or organism gene list to work around it.

When/if access is restored or a key mechanism is added: `VEuPathDB_search_genes_by_organism(organism="<Genus species Strain>", project="<plasmodb|toxodb|fungidb|vectorbase|cryptodb|giardiadb|microsporidiadb|piroplasmadb|trichdb|tritrypdb|amoebadb>", limit=25)` finds genes for a named organism/strain (e.g. `organism="Plasmodium falciparum 3D7"`, `project="plasmodb"`), and `VEuPathDB_get_gene_record(gene_id="<primary_key>", project="<same project>")` retrieves one gene's attributes (product, gene type, genomic location, chromosome, transcript count) by its VEuPathDB primary key (e.g. `PF3D7_0417200` for *P. falciparum*'s DHFR-TS gene).

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
