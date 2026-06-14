---
name: tooluniverse-microbial-genome-characterization
description: Genome-ASSEMBLY discovery, QC, and replicon mapping for any organism (bacteria, archaea, fungi, and beyond) using NCBI Datasets. Resolves an organism name or taxid to assemblies, picks the reference/representative or best-quality assembly, pulls assembly QC metrics (total length, contig/scaffold N50, contig count, GC%, assembly level, RefSeq category), enumerates chromosomes and plasmids via per-replicon sequence reports, and compares candidate assemblies on quality. Use for "what genomes are available for [organism]", "assembly stats / N50 / GC content for [GCF_/GCA_ accession]", "how many plasmids does [strain] have", "compare assemblies for [species]", "find the reference genome for [taxon]", "is this assembly Complete Genome or just contigs". NOT for gene-level orthology/synteny (use tooluniverse-comparative-genomics), plant gene structure (use tooluniverse-plant-genomics), de novo assembly from raw reads (no tool exists), or taxonomy-only name/lineage lookups.
disable-model-invocation: true
---

# Microbial Genome Assembly Characterization & QC

Discover, quality-control, and structurally map genome ASSEMBLIES for any organism using the keyless NCBI Datasets genome tools. Organism/taxon in → assembly inventory, QC metrics, and chromosome/plasmid map out.

## LOOK UP, DON'T GUESS
When uncertain about an accession, assembly level, replicon count, or N50, CALL the tool. Never report assembly statistics from memory — accessions and metrics change with each RefSeq release. A live NCBI Datasets answer is always more reliable than a guess.

## COMPUTE, DON'T DESCRIBE
When comparing multiple assemblies or ranking by quality, retrieve each via the tools, then write and run Python (pandas) over the returned JSON to sort, score, and tabulate. Don't describe what you would compute — execute it and report actual numbers.

## When to Use This Skill

**Triggers**:
- "What genomes are available for [organism]?" / "Find the reference genome for [taxon]"
- "Assembly stats for GCF_000005845.2" / "What's the N50 / GC content of [accession]?"
- "How many plasmids does [strain] have?" / "List the replicons in [accession]"
- "Compare the assemblies for [species] — which is best quality?"
- "Is [accession] a complete genome or draft?"

**Use Cases**:
1. **Assembly discovery**: enumerate available assemblies for a taxon, optionally only reference-grade
2. **Assembly QC**: pull length, N50, contig count, GC%, level, RefSeq category for an accession
3. **Replicon mapping**: list chromosomes and plasmids with their RefSeq/GenBank accessions and lengths
4. **Assembly comparison**: rank candidate assemblies of one species by completeness and contiguity
5. **Reference selection**: identify the designated reference/representative genome for a taxon

**NOT this skill** (point elsewhere):
- Gene-level orthology, synteny, conservation → `tooluniverse-comparative-genomics`
- Plant gene structure / annotation → `tooluniverse-plant-genomics`
- De novo assembly from sequencing reads → no ToolUniverse tool exists; say so
- Pure taxonomy name → lineage lookups with no genome question → use NCBI taxonomy tools directly

---

## Tools (all keyless, verified live)

| Tool | Key params | Returns |
|------|-----------|---------|
| `NCBIDatasets_suggest_taxonomy` | `query` (organism name string) | candidate matches: `scientific_name`, `tax_id`, `rank`, `group_name` |
| `NCBIDatasets_get_taxonomy` | `tax_id` (string/int) | `organism_name`, `rank`, `lineage`, `children` |
| `NCBIDatasets_list_genomes_by_taxon` | `taxon` (name OR taxid), `limit`, `reference_only` (bool) | assembly list (accession, assembly_level, refseq_category, total_sequence_length, contig_n50, gc_percent, number_of_chromosomes, number_of_contigs); `metadata.total_available` = full count |
| `NCBIDatasets_get_genome_assembly` | `accession` (GCF_/GCA_) | full QC: total_sequence_length, number_of_chromosomes, number_of_contigs, contig_n50, scaffold_n50, gc_percent, assembly_level, assembly_status, refseq_category, release_date, submitter, annotation_provider |
| `NCBIDatasets_get_sequence_reports` | `accession` (GCF_/GCA_) | per-replicon list: chr_name, role, refseq_accession, genbank_accession, length, gc_percent |

> Param note: `get_taxonomy` requires `tax_id` (NOT `taxon`). `list_genomes_by_taxon` accepts either a name or a taxid in its `taxon` field. Always pass an accession to the assembly/sequence-report tools.

---

## Workflow

### Phase 0 — Resolve the organism (skip if you already have an accession)
If the user gives an organism name, resolve it to a tax id first:

```
NCBIDatasets_suggest_taxonomy {"query": "Escherichia coli"}
```

Pick the candidate whose `scientific_name`/`rank` matches the user's intent (species vs. a specific strain). Optionally confirm lineage/children with `NCBIDatasets_get_taxonomy {"tax_id": "562"}`.

If the user already gave a GCF_/GCA_ accession, skip to Phase 2.

### Phase 1 — Inventory the assemblies
List what exists for the taxon. Start `reference_only: true` to surface the curated reference/representative genome(s); set it to `false` to see the full set.

```
NCBIDatasets_list_genomes_by_taxon {"taxon": "562", "limit": 5, "reference_only": true}
```

Read `metadata.total_available` for the true count (large taxa return thousands — the `data` array is only the first `limit` rows). Note each candidate's `assembly_level`, `refseq_category`, `contig_n50`, and `number_of_contigs`.

### Phase 2 — Select the assembly
Prefer, in order:
1. `refseq_category == "reference genome"` (NCBI's single designated reference)
2. `refseq_category == "representative genome"`
3. Highest `assembly_level` (Complete Genome > Chromosome > Scaffold > Contig)
4. Highest `contig_n50` and lowest `number_of_contigs` among same-level candidates
5. A GCF_ (RefSeq) accession over its paired GCA_ (GenBank) when both exist — RefSeq is the curated copy

### Phase 3 — Pull assembly QC metrics
```
NCBIDatasets_get_genome_assembly {"accession": "GCF_000005845.2"}
```
Report: total length, # chromosomes, # contigs, contig N50, scaffold N50, GC%, assembly level, RefSeq category, release date, annotation provider.

### Phase 4 — Map the replicons (chromosomes + plasmids)
```
NCBIDatasets_get_sequence_reports {"accession": "GCF_000005845.2"}
```
Each row is one replicon. Distinguish chromosomes from plasmids by `chr_name` / `role`: a row named like `pO157`, `pOSAK1`, or with a plasmid-style name is a plasmid; `chromosome` rows are chromosomes. To answer "how many plasmids", count the non-chromosome assembled-molecule rows.

### Phase 5 — Compare candidates (optional)
When the user wants the best of several assemblies, fetch each accession, build a pandas table, and sort by (assembly_level rank, then contig_n50 desc, then number_of_contigs asc). Report the winner with the metrics that decided it.

---

## Interpretation Table

**Assembly level** (contiguity, best → worst):

| Level | Meaning |
|-------|---------|
| Complete Genome | Every replicon (each chromosome + each plasmid) fully resolved as one gapless sequence. Gold standard. |
| Chromosome | Chromosome(s) assembled to near-complete, but may contain gaps; plasmids/organelles may be incomplete. |
| Scaffold | Contigs ordered/oriented into scaffolds using gap-spanning evidence; gaps remain. Draft. |
| Contig | Only contiguous stretches; no scaffolding. Most fragmented draft. |

**Contiguity metrics** (a typical bacterial genome is 2–6 Mb):

- **Contig N50**: the contig length at which 50% of the assembly is in contigs ≥ that size. Higher = better. A Complete Genome's contig N50 equals its largest replicon length (e.g., 4.64 Mb for E. coli K-12 — the whole chromosome is one contig). A good draft bacterium often has N50 in the hundreds-of-kb; N50 of a few kb signals a fragmented assembly.
- **Number of contigs**: low is better. A Complete Genome has one contig per replicon (so 1 for a single-chromosome no-plasmid genome). Hundreds–thousands of contigs indicates a fragmented draft.
- **Scaffold N50 ≥ contig N50** always; a large gap between them means scaffolding bridged many contigs across gaps.

**RefSeq category**:

| Value | Meaning |
|-------|---------|
| reference genome | NCBI's single, most-curated assembly for the taxon — the default to cite. |
| representative genome | A high-quality assembly chosen to represent the species when no formal reference is designated. |
| (null / none) | An ordinary submitted assembly, not specially designated. |

**GCF_ vs GCA_**: GCF_ = RefSeq (NCBI-curated, consistent annotation). GCA_ = GenBank (as submitted by the author). They share the numeric core (e.g., GCF_000005845.2 / GCA_000005845.2); prefer GCF_ when both exist.

---

## Worked Example 1 — Reference genome of *E. coli* (single chromosome, no plasmid)

1. `NCBIDatasets_suggest_taxonomy {"query":"Escherichia coli"}` → species tax id **562**.
2. `NCBIDatasets_list_genomes_by_taxon {"taxon":"562","limit":5,"reference_only":true}` → top hit **GCF_000005845.2** (*E. coli* str. K-12 substr. MG1655), assembly_level **Complete Genome**, refseq_category **reference genome**, total 4,641,652 bp, contig_n50 4,641,652, GC 51%. `metadata.total_available` = 2 reference-grade.
3. `NCBIDatasets_get_genome_assembly {"accession":"GCF_000005845.2"}` → **4.64 Mb**, **1 chromosome**, **1 contig**, contig N50 = scaffold N50 = 4,641,652 (the entire genome is one gapless contig), GC **51%**, Complete Genome, released 2013-09-26, annotated by NCBI RefSeq.
4. `NCBIDatasets_get_sequence_reports {"accession":"GCF_000005845.2"}` → **one replicon**: `chromosome`, RefSeq **NC_000913.3** (GenBank U00096.3), 4,641,652 bp, GC 51%. **Zero plasmids.**

Answer: The E. coli K-12 reference genome is GCF_000005845.2 — a 4.64 Mb Complete Genome with a single chromosome (NC_000913.3), no plasmids, GC 51%.

## Worked Example 2 — "How many plasmids does *E. coli* O157:H7 Sakai have?"

1. From the same taxon listing, the Sakai reference assembly is **GCF_000008865.2** (Complete Genome, 5.59 Mb, 3 chromosomes-field).
2. `NCBIDatasets_get_sequence_reports {"accession":"GCF_000008865.2"}` → **three replicons**:
   - `chromosome` — NC_002695.2 — 5,498,578 bp
   - `pOSAK1` (plasmid) — NC_002127.1 — 3,306 bp
   - `pO157` (plasmid) — NC_002128.1 — 92,721 bp

Answer: 1 chromosome + **2 plasmids** (pOSAK1 ~3.3 kb, pO157 ~92.7 kb). Note: the assembly's `number_of_chromosomes` field reports 3 (it counts all assembled molecules); the sequence report is authoritative for telling chromosomes from plasmids by name/role.

## Worked Example 3 — Inventory scale (large taxon)

`NCBIDatasets_list_genomes_by_taxon {"taxon":"Mycobacterium tuberculosis","limit":3,"reference_only":false}` → `metadata.total_available` = **16,311** assemblies; first rows include GCA_000195955.2 and its RefSeq pair GCF_000195955.2 (both Complete Genome, reference genome, contig N50 4,411,532, 1 contig). Use `reference_only:true` to cut 16k assemblies down to the curated reference; never page through all of them.

---

## Limitations

- **No de novo assembly**: this skill characterizes *existing* NCBI assemblies. It cannot assemble a genome from FASTQ/raw reads — no ToolUniverse tool does that. Say so and stop.
- **RefSeq vs GenBank**: only assemblies ingested into NCBI Datasets appear. A brand-new GenBank-only submission may lack a GCF_ pair until RefSeq curation runs.
- **`number_of_chromosomes` counts assembled molecules**, not strictly chromosomes — for some bacteria it includes plasmids. Always use `get_sequence_reports` to separate chromosomes from plasmids by replicon name/role.
- **Large taxa paginate**: `list_genomes_by_taxon` returns only `limit` rows; trust `metadata.total_available` for the count and refine with `reference_only:true` rather than fetching thousands.
- **No completeness/contamination scores**: NCBI Datasets does not return BUSCO/CheckM here. Assembly *level* and N50 are proxies for quality; this skill does not compute genome completeness from marker genes.
- **Annotation depth not assessed**: these tools report whether an assembly is annotated and by whom, not gene-by-gene content. For gene-level analysis route to a gene-centric skill.

---

## Completeness Checklist

Before answering, confirm you have:
- [ ] Resolved the organism to a tax id (or were given an accession) — no guessed taxids
- [ ] Stated `metadata.total_available` when reporting "how many genomes exist"
- [ ] Justified the selected accession (reference > representative > level > N50/contigs)
- [ ] Reported assembly level, length, N50, contig count, and GC% from a live `get_genome_assembly` call
- [ ] Used `get_sequence_reports` (not `number_of_chromosomes`) to count chromosomes vs plasmids
- [ ] Preferred the GCF_ accession over its GCA_ pair when both exist
- [ ] Pointed elsewhere if the request was orthology, plant gene structure, de novo assembly, or taxonomy-only
