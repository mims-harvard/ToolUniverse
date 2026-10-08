---

name: tooluniverse-comparative-genomics
description: "Cross-species gene comparison and ortholog analysis. Integrates Ensembl Compara orthologs, NCBI Gene, UniProt, OLS, Monarch, and OpenTargets to identify orthologs, paralogs, sequence conservation, functional conservation across species, and lineage-specific gene gains/losses. Use for phylogenetic gene tracing, model-organism mapping, and evolutionary-genomics queries."
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

**Computing dN/dS.** The data path: `ensembl_get_homology(...)` → the 1:1 ortholog IDs → `EnsemblSeq_get_id_sequence(id=..., type="cds")` for each → codon-align the two CDS (orthologous CDS are usually directly alignable; for divergent pairs align the protein and back-translate) → compute dN/dS. Prefer the **`Sequence_dn_ds`** tool — one call returns structured `dN`, `dS`, `dN_dS`, per-site counts, and an interpretation:

```
Sequence_dn_ds(seq1="ATG...", seq2="ATG...")        # inline codon-aligned CDS
Sequence_dn_ds(fasta1_path="human.fa", fasta2_path="mouse.fa")
```

It implements the Nei-Gojobori (1986) estimator with Jukes-Cantor correction (the bundled `scripts/dnds.py` is the identical CLI form, validated against Biopython NG86). `dN_dS` is `null` when dS is 0 or uncorrectable (too few/too many substitutions) — do not over-interpret a single high-divergence pair without enough synonymous sites.

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

For a species outside Ensembl's well-annotated set (most non-model organisms), check `GoaT_get_species(taxon=...)` first to confirm a reference genome assembly actually exists (and its status: draft/chromosome-level/annotated) before assuming gene-level lookups will work at all.

---

## Phase 2: Ortholog Discovery

`EnsemblCompara_get_orthologues` is the primary tool. It takes `gene` (symbol or Ensembl ID), `species` (source species, default "human"), and optionally `target_species` (e.g., "mouse", "zebrafish") or `target_taxon` (NCBI taxon ID). Omit `target_species` to get all orthologs across the tree; filter client-side for specific species. It returns homology type (one2one, one2many, many2many) and the taxonomy divergence level for each ortholog.

`ensembl_get_homology` is the alternative when you need sequence-level data alongside the ortholog mapping. Use `sequence="protein"` and `aligned=true` for aligned sequence comparison across species.

`OpenTargets_get_target_homologues_by_ensemblID` (takes `ensemblId`) provides supplementary ortholog data from OpenTargets, which can add druggability context and cross-reference with model organism phenotype data.

**Reasoning**: Prioritize 1:1 orthologs as high-confidence functional equivalents. For 1:many cases, report all copies and flag the need for paralog-specific functional analysis. If no Ensembl Compara entry exists, try OMA (below) before BLAST — OMA's 2,600+ genome set covers far more invertebrates, fungi, and microbes than Ensembl Compara.

Key model organisms to check: mouse (taxon 10090), rat (10116), zebrafish (7955), fruit fly (7227), C. elegans (6239), S. cerevisiae (4932).

### OMA as a complementary/broader ortholog source

Ensembl Compara is vertebrate-centric (see Limitations). **OMA (Orthologous MAtrix)** covers 2,600+ genomes spanning vertebrates, invertebrates, plants, fungi, and microbes, and additionally provides two things Ensembl Compara does not: **Hierarchical Orthologous Groups (HOGs)** — the full duplication/speciation history of a gene family across a taxonomic range, not just pairwise calls — and **OMA Groups**, the strictest possible orthology definition (each species contributes at most one gene). Use OMA when: the species of interest is outside Ensembl's well-annotated set, you need the duplication history of a gene family (not just a pairwise ortholog list), or you want the most conservative possible 1:1 ortholog set for a downstream analysis that can't tolerate false positives.

**Entry point — resolving a gene symbol to an OMA identifier:**
`OMA_get_protein` only accepts a UniProt accession (e.g. `P04637`) or an OMA ID (e.g. `HUMAN31534`) — it does not take a gene symbol. If you already resolved a UniProt accession in Phase 1/4, use it directly here; it is more reliable than the alternative below.

If you only have a gene symbol, `OMA_resolve_xref(search=...)` can look it up, but **it does substring/fuzzy matching across all cross-reference databases (STRING, RefSeq, UniProt, etc.), not an exact gene-symbol match** — verified live: searching `search="TP53"` returns entries like `1109443.G4TP53` (a STRING ID for an unrelated fungal protein) and `29760.D7TP53` (*Vitis vinifera*) purely because "TP53" is a substring of the cross-reference string, not because they are TP53 orthologs. **Always filter the results**: keep only entries with `seq_match: "exact"` AND `source` starting with `UniProtKB` AND a `species_name` matching what you expect, before trusting an `oma_id`/`entry_nr` from this tool. For a well-known human gene, it is faster and safer to resolve the UniProt accession first (`tooluniverse-sequence-retrieval` / `UniProt_search`) and skip `OMA_resolve_xref` entirely.

**Core OMA workflow once you have a UniProt accession or OMA ID:**

```
OMA_get_protein(protein_id="P04637")
  -> oma_id (e.g. HUMAN31534), oma_group, oma_hog_id (e.g. HOG:F0782425.2c.7a),
     roothog_id, chromosome/locus — the hub record for everything below

OMA_get_orthologs(protein_id="P04637", rel_type="1:1"|"1:n"|"n:1"|"n:m"|omit, per_page=...)
  -> pairwise orthologs with rel_type, evolutionary distance, alignment score.
     OMA does not paginate internally — it fetches the whole set and ToolUniverse
     slices it client-side — so metadata.total_count is the TRUE ortholog count
     (e.g. 130 for human TP53) even when metadata.count (page size) is much
     smaller; never report metadata.count as "the number of orthologs".

OMA_get_hog(hog_id="HOG:F0782425")
  -> full duplication/speciation tree: level (taxonomic rank of this HOG node,
     e.g. "Euteleostomi"), children_hogs (lineage-specific sub-duplications,
     each with its own hog_id and alternative_levels), completeness_score.
     Use this — not OMA_get_orthologs — when the question is about *when and
     where* a gene family duplicated, not just which species have a copy.
     HOG IDs are reassigned between OMA releases; always get the current one
     from OMA_get_protein's oma_hog_id, don't hardcode one from an old query.

OMA_get_group(group_id="1458663")  # from OMA_get_protein's oma_group field
  -> the strict 1:1-only cross-species group. Use the oma_group value FROM
     THE PROTEIN RESPONSE, not from unrelated examples — group numbering is
     dense and a group ID a few hundred thousand off from the right one
     returns a completely unrelated gene family's group with no error
     (verified live: group 1388790 returns "THO complex subunit 5 homolog",
     not p53 — always confirm the group_nr in the response matches what you
     expect, don't assume a group ID you were told is correct actually is).

OMA_get_protein_go(protein_id="HUMAN31534", aspect="biological_process"|...)
  -> GO annotations with per-term information_content (higher = more specific/
     rarer term) and evidence code. This is OMA's own GO layer — use it
     alongside (not instead of) the UniProt/OLS GO retrieval in Phase 4;
     the two databases' annotation sets do not always match exactly.

OMA_get_genome_pair_orthologs(genome1="HUMAN", genome2="MOUSE", per_page=..., page=...)
  -> the FULL proteome-vs-proteome ortholog table between two species (not one
     query protein) — the right tool for building a species-pair ortholog
     table or synteny/dN-dS panel across many genes at once, rather than
     calling OMA_get_orthologs one protein at a time. Species arguments accept
     either a UniProt species code ("HUMAN", "MOUSE", "PANTR") or an NCBI
     taxon ID.
```

**Reasoning**: Cross-check an Ensembl Compara 1:1 call against OMA's `OMA_get_orthologs(rel_type="1:1")` result for the same protein when the finding is load-bearing (e.g. selecting a model organism for a disease study) — the two databases use different orthology-inference algorithms (Compara: gene trees; OMA: pairwise + graph-based) and largely agree for well-conserved genes, but a disagreement is itself informative (it usually means the relationship is genuinely ambiguous, e.g. a recent duplication).

### OrthoDB as a second group-based ortholog source

**OrthoDB** is a third orthology database, distinct from both Ensembl Compara (gene-tree-based) and OMA (pairwise + strict-group-based): it defines orthologous groups **per taxonomic level** — the same gene family gets a *different* `group_id` at Eukaryota, Metazoa, Vertebrata, Primates, etc., each capturing the members and duplication pattern visible at that evolutionary depth. This is a genuinely different lens from OMA's HOG tree (one object encoding the whole duplication history) — OrthoDB instead gives you one flat member-list snapshot per level, plus (when populated) GO/KEGG/InterPro functional annotations attached directly to the group and, uniquely among the three, direct FASTA sequence retrieval for every member of a group in one call.

**Entry point — searching by gene name is unreliable, verified live.** `OrthoDB_search_groups(query="TP53", species=9606, limit=20)` does NOT return the actual p53 gene group anywhere in its top 20 (of 100 total) results — it returns "TP53-target gene 3 protein", "TP53-binding protein 1", and unrelated groups like "phosphoglycerate mutase", because the search matches loosely against group consensus names/text, not an exact gene-symbol index. The actual group only surfaced when searching the group's real OrthoDB consensus name instead: `OrthoDB_search_groups(query="cellular tumor antigen p53")` → `"tumor protein p53"` at `group_id="4289813at2759"` (Eukaryota level). This is the same class of failure mode as `OMA_resolve_xref`'s substring matching (see above) — **never trust the first search hit as "the gene's group" without confirming the returned `name` and, via `OrthoDB_get_orthologs`, that it actually contains the expected species/gene_id.**

**Core OrthoDB workflow (verified live on the same TP53 example as the OMA section above, for direct comparison):**

```
OrthoDB_search_groups(query=..., species=9606, level=..., limit=...)
  -> candidate group_ids. Prefer a descriptive/consensus-name query over a bare
     gene symbol (see above). `level` narrows to one taxonomic depth (7742 =
     Vertebrata, 33208 = Metazoa, 2759 = Eukaryota) if you already know which
     scope you want; omit it to see the gene's group at every level OrthoDB
     tracks separately.

OrthoDB_get_group_details(group_id="4289813at2759")
  -> name, level_name, tax_id, plus go_terms/kegg_pathways/interpro_domains
     WHEN POPULATED. Verified live: this TP53 (Eukaryota-level) group returned
     `go_terms: null, kegg_pathways: null, interpro_domains: null` -- these
     enrichment fields are not populated for every group, do not assume their
     absence means "no known function," just that OrthoDB hasn't attached
     that layer at this particular group/level.

OrthoDB_get_orthologs(group_id="4289813at2759", species="9606,10090")
  -> per-organism member list. Verified live: returned 2 entries EACH for
     human and mouse (gene_id "TP53"/"7157" for human, "Trp53"/"22059" for
     mouse) -- OrthoDB can list more than one record per organism per group
     (alternate gene-model annotations for the same locus), so
     `total_orthologs` is a record count, not a species count; group by
     `organism_name` (or use `organisms_summary`) to get the actual per-species
     tally.

OrthoDB_get_group_fasta(group_id="4289813at2759", species="9606", limit=...)
  -> the one thing OMA and Ensembl Compara tool calls in this skill don't give
     you directly: real amino-acid sequences for every member of a group in
     one call, with `pub_gene_id`/`organism_name` parsed out of each header.
     Verified live: returned 2 human sequences (410 aa and 393 aa -- different
     isoform-level records, not an error) ready for MSA/phylogenetic input
     without a separate NCBI/Ensembl sequence-retrieval round-trip.
```

**Reasoning**: Use OrthoDB alongside OMA (not instead of it) when you specifically need (a) per-taxonomic-level group snapshots rather than one merged duplication tree, (b) group-level GO/KEGG/InterPro enrichment when populated, or (c) direct FASTA sequences for an entire orthogroup in one call for downstream alignment. For raw ortholog-count and 1:1/1:n relationship-type queries, OMA's `OMA_get_orthologs` is more directly comparable across the same result you'd get from Ensembl Compara; treat OrthoDB as a complementary data layer, not a replacement decision point.

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

**Genome-assembly context for a comparison species**: When a species' ortholog calls look incomplete or you need the underlying reference assembly, use `NCBIDatasets_list_genomes_by_taxon` (params `taxon` as tax_id, `limit`, `reference_only`) to find the reference genome, `NCBIDatasets_get_genome_assembly` (param `accession`) for assembly metrics (contiguity/N50/completeness — a fragmented assembly can cause spurious "missing ortholog" calls), and `NCBIDatasets_get_sequence_reports` (param `accession`) for the chromosome/scaffold replicon map. For a full assembly-QC workflow on microbial genomes, see the `tooluniverse-microbial-genome-characterization` skill.

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

- **Ortholog not found in Ensembl Compara**: Try `ensembl_get_homology`, then `OpenTargets_get_target_homologues_by_ensemblID`, then **`OMA_get_orthologs`** (broader taxonomic coverage, especially invertebrates/fungi/microbes — see the OMA section in Phase 2), then BLAST as last resort. If a species is absent from Compara AND from OMA, confirm a reference assembly exists via `NCBIDatasets_list_genomes_by_taxon` and check its contiguity with `NCBIDatasets_get_genome_assembly` before concluding the gene is truly absent
- **Need duplication/speciation history, not just a pairwise ortholog list**: `OMA_get_hog` gives the full HOG tree; Ensembl Compara's gene tree (`EnsemblCompara_get_gene_tree`) gives a comparable view — cross-check both if the duplication timing is load-bearing for the conclusion
- **Sequence retrieval fails**: Use `ensembl_get_homology` with `sequence="cdna"` as alternative to NCBI
- **UniProt returns empty with reviewed:true**: Try without that filter; organism may have only TrEMBL entries
- **Monarch returns no data**: Use `MonarchV3_get_associations` with `category="biolink:GeneToPhenotypicFeatureAssociation"` as alternative
- **Gene symbol ambiguous across species**: Use Ensembl IDs throughout to avoid symbol confusion (e.g., "p53" vs "tp53" in zebrafish)

---

## Limitations

- **Ensembl Compara**: Best for vertebrates; invertebrate and plant coverage is limited for some gene families. **OMA** covers 2,600+ genomes including many more invertebrates/fungi/microbes, but has its own gaps (no plant-specific gene-tree curation like Ensembl Plants) — treat the two as complementary, not one strictly superseding the other
- **OMA_resolve_xref**: Does substring/fuzzy matching, not exact gene-symbol resolution — a bare gene symbol (e.g. "TP53") returns unrelated cross-references that merely contain the string. Always filter for `seq_match: "exact"` and the expected `species_name`/source, or resolve a UniProt accession first and skip this tool
- **OMA group/HOG IDs**: Numbering is dense with no bounds-checking — an incorrect ID a few hundred thousand off from the right one silently returns a different, unrelated gene family with no error. Always take the ID from a live `OMA_get_protein` response, never assume one from memory or an old query is still correct
- **OrthoDB_search_groups**: Matches loosely against group consensus names, not gene symbols — searching a bare gene symbol like "TP53" can fail to surface the actual gene's group anywhere in the top 20+ results (verified live), returning similarly-named but unrelated groups instead ("TP53-target gene 3 protein", "TP53-binding protein 1"). Confirm the returned group's members via `OrthoDB_get_orthologs` before trusting it, or search a descriptive name (e.g. "cellular tumor antigen p53") instead of the bare symbol
- **OrthoDB group/level split**: The same gene has a different `group_id` at every taxonomic level OrthoDB tracks (Eukaryota, Metazoa, Vertebrata, ...) — there is no single canonical group ID for a gene the way OMA has one `oma_group`. Also, `OrthoDB_get_group_details`'s GO/KEGG/InterPro fields are `null` for many groups (verified live) — absence there is a data-population gap, not evidence the gene lacks that annotation elsewhere
- **BLAST_protein_search**: Very slow (5-30 min); use only as last resort for ortholog discovery
- **Monarch**: Phenotype coverage varies by organism; mouse and zebrafish are best covered; fly and worm data are sparser
- **UniProt GO annotations**: Bias toward well-studied organisms; absence of annotation does not mean absence of function
- **NCBI_search_nucleotide**: May return many isoforms; filter for RefSeq (NM_*) for canonical transcripts
- **Conservation does not equal essentiality**: Some highly conserved genes are dispensable in specific organisms
