---
name: tooluniverse-sequence-retrieval
description: "Retrieve DNA/RNA/protein sequences from NCBI and ENA with disambiguation. Quality hierarchy: RefSeq (NM_/NP_) > RefSeq predicted (XM_/XP_) > GenBank submissions. Use for fetching specific sequences by accession, gene-symbol-to-sequence lookup, transcript-isoform retrieval, and curated-vs-raw-submission preference."
disable-model-invocation: true
---

# Biological Sequence Retrieval

Retrieve DNA, RNA, and protein sequences with proper disambiguation and cross-database handling.

**IMPORTANT**: Always use English terms in tool calls. Only try original-language terms as fallback. Respond in the user's language.

**LOOK UP DON'T GUESS**: Never assume accession numbers or sequence versions. Always retrieve and verify from NCBI or ENA.

## Domain Reasoning

Sequence quality hierarchy: RefSeq (NM_/NP_ = curated) > RefSeq predicted (XM_/XP_) > GenBank (submitted). Prefer the MANE Select transcript for human canonical isoforms. Check version numbers -- annotations improve across versions.

## Workflow

```
Phase 0: Clarify (if needed) → Phase 1: Disambiguate Gene/Organism → Phase 2: Search & Retrieve → Phase 3: Report
```

---

## Phase 0: Clarification (When Needed)

Ask ONLY if: gene exists in multiple organisms, sequence type unclear, or strain matters.
Skip for: specific accessions, clear organism+gene combos, complete genome requests with organism.

---

## Phase 1: Gene/Organism Disambiguation

### Accession Type Decision Tree

| Prefix | Type | Use With |
|--------|------|----------|
| NC_/NM_/NR_/NP_/XM_ | RefSeq | NCBI only |
| U*/M*/K*/X*/CP*/NZ_ | GenBank | NCBI or ENA |
| EMBL format | EMBL | ENA preferred |

**CRITICAL**: Never try ENA tools with RefSeq accessions -- they return 404.

### Identity Checklist
- Organism confirmed (scientific name)
- Gene symbol/name identified
- Sequence type determined (genomic/mRNA/protein)
- Accession prefix identified for tool selection

---

## Phase 2: Data Retrieval (Internal)

Retrieve silently. Do NOT narrate the search process.

```python
# Search NCBI Nucleotide
result = tu.tools.NCBI_search_nucleotide(
    operation="search", organism=organism, gene=gene,
    strain=strain, keywords=keywords, seq_type=seq_type, limit=10
)

# Get accessions from UIDs
accessions = tu.tools.NCBI_fetch_accessions(operation="fetch_accession", uids=result["data"]["uids"])

# Retrieve sequence (FASTA or GenBank format)
sequence = tu.tools.NCBI_get_sequence(operation="fetch_sequence", accession=accession, format="fasta")

# ENA alternative (non-RefSeq accessions only)
entry = tu.tools.ena_get_entry(accession=accession)
fasta = tu.tools.ena_get_sequence_fasta(accession=accession)
```

### Fallback Chains

| Primary | Fallback | Notes |
|---------|----------|-------|
| NCBI_get_sequence | ENA (if GenBank format) | NCBI unavailable |
| ena_get_entry | NCBI_get_sequence | ENA doesn't have RefSeq |
| NCBI_search_nucleotide | Try broader keywords | No results |
| NCBI_get_sequence / ena_get_sequence_fasta | dbfetch_fetch_entry (db="refseqn"/"ena_sequence") | Both NCBI and ENA-specific tools unavailable; dbfetch mirrors the same underlying records |

---

## Phase 3: Report Sequence Profile

Present as a **Sequence Profile Report**. Hide search process. Include:

1. **Search Summary**: query, database, result count
2. **Primary Sequence**: accession, type (RefSeq/GenBank), organism, strain, length, molecule, topology, curation level
3. **Sequence Preview**: first lines of FASTA (truncated)
4. **Annotations Summary**: CDS/tRNA/rRNA/regulatory feature counts (from GenBank format)
5. **Alternative Sequences**: ranked by relevance and curation, with ENA compatibility
6. **Cross-Database References**: RefSeq, GenBank, ENA/EMBL, BioProject, BioSample
7. **Download Options**: FASTA (for BLAST/alignment), GenBank (for annotation)

### Curation Level Tiers

| Tier | Prefix | Description |
|------|--------|-------------|
| RefSeq Reference (best) | NC_, NM_, NP_ | NCBI-curated, gold standard |
| RefSeq Predicted | XM_, XP_, XR_ | Computationally predicted |
| GenBank Validated | Various | Submitted, some curation |
| GenBank Direct | Various | Direct submission |
| Third Party | TPA_ | Third-party annotation |

---

## Reasoning Framework

**Sequence quality**: Prefer RefSeq over GenBank. Check version numbers. Sequences with "PREDICTED" in definition are not experimentally validated.

**Accession guidance**: RefSeq = NCBI-only. GenBank = mirrored in ENA/EMBL. Default to RefSeq mRNA (NM_) for human/model organisms; most complete genome assembly for microbial queries.

**Cross-database reconciliation**: Same sequence may have different accessions (e.g., GenBank U00096 = RefSeq NC_000913 for E. coli K-12). Always report both when available. Discrepancies between GenBank/RefSeq typically indicate RefSeq curation corrected submission errors.

### Synthesis Questions
1. What is the highest-quality accession available?
2. Are there alternative accessions in other databases?
3. What is the annotation completeness?
4. Is the sequence from the expected organism/strain?
5. What download format suits the user's downstream analysis?

---

## Error Handling

| Error | Response |
|-------|----------|
| "No search criteria provided" | Add organism, gene, or keywords |
| "ENA 404 error" | Likely RefSeq -- use NCBI only |
| "No results found" | Broaden search, check spelling, try synonyms |
| "Sequence too large" | Note size, provide download link instead |

---

## Tool Reference

**NCBI Tools**: `NCBI_search_nucleotide` (search), `NCBI_fetch_accessions` (UID→accession), `NCBI_get_sequence` (retrieve)
**ENA Tools (GenBank/EMBL only)**: `ena_get_entry` (metadata), `ena_get_sequence_fasta` (FASTA), `ena_get_entry_summary` (summary)

---

## Search Parameters Reference

**NCBI_search_nucleotide**: `operation`="search", `organism` (scientific name), `gene` (symbol), `strain`, `keywords`, `seq_type` (complete_genome/mrna/refseq), `limit`

**NCBI_get_sequence**: `operation`="fetch_sequence", `accession`, `format` (fasta/genbank)

---

## Whole-Organism Reference Proteomes (UniProt)

A different granularity from Phases 1-3 above: `src/tooluniverse/data/uniprot_ref_tools.json`'s
`UniProtRef_search_proteomes`/`UniProtRef_get_proteome` (no API key
required) return organism-LEVEL proteome metadata — total protein count,
chromosome/component breakdown, genome accession — not one sequence.
Reach for these when the question is "what is species X's reference
proteome and how big is it" (e.g. before a proteome-wide analysis, or to
find the right genome-assembly accession to hand to Phase 2 above), not
for fetching an individual gene/transcript sequence.

| Tool | Resolves | Key output |
|---|---|---|
| `UniProtRef_search_proteomes` | organism name/taxon ID -> matching proteome ID(s) | `id` (`UPXXXXXXXXX`), `organism`, `taxon_id`, `proteome_type` (Reference/Non Reference), `protein_count` |
| `UniProtRef_get_proteome` | one proteome ID -> full organism/assembly detail | `organism.scientific_name`/`taxon_id`, `components[]` (`name`, `protein_count`, `genome_accession`), `total_protein_count` |

Real example chain (verified live): `UniProtRef_search_proteomes {"query":
"SARS-CoV-2"}` -> 3 results, including `UP000464024` (`proteome_type:
"Reference proteome"`, 17 proteins) alongside two `"Non Reference
proteome"` entries for the same organism (5 and 10 proteins) — always
check `proteome_type` and prefer `"Reference proteome"` rather than
assuming the first hit is canonical. Feeding `UP000464024` into
`UniProtRef_get_proteome` confirms `components: [{"name": "Segment",
"protein_count": 17, "genome_accession": "MN908947"}]` (the real SARS-CoV-2
reference genome accession) and `total_protein_count: 17`. For human
(`UP000005640`) and E. coli K-12 (`UP000000625`), `get_proteome` returns
per-chromosome/plasmid component breakdowns the same way.

**Registry duplication, verified live:** `UniProt_search_proteomes` (in
`src/tooluniverse/data/uniprot_proteomes_tools.json`, hitting
`rest.uniprot.org/proteomes/search` directly) does the SAME search as
`UniProtRef_search_proteomes` above, but is a separate, older tool
implementation. Its advantage: one call returns the full rich record
(BUSCO completeness, genome assembly, per-component protein counts, full
citation list) that `UniProtRef_search_proteomes` requires a *second*
`UniProtRef_get_proteome` call to obtain — verified live on `organism_name:
human`, `organism_name:escherichia coli`, `organism_name:mouse`, all 3
returning the full nested object in one shot. If you only need the ID or
`proteomeType` for triage, either tool works; if you need full detail
immediately, prefer `UniProt_search_proteomes` and skip the follow-up call.

## Sequence Archive and Clustering (UniParc, UniRef)

A different question again from Phases 1-3 and the proteome tools above:
"has this exact sequence been seen before, and under how many accessions,"
and "what other sequences are near-identical to this one."

| Tool | Answers | Key params |
|---|---|---|
| `UniParc_search` | Find all UPI archive entries for a gene/organism/keyword | `query` (UniProt query syntax, e.g. `"gene:EGFR AND organism_id:9606"`), `size` |
| `UniParc_get_entry` | Full sequence + every UniProt accession that ever pointed to this exact sequence, across every database load | `upi` |
| `UniRef_search_clusters` | Find sequence-similarity clusters for a gene/organism/keyword | `query`, `cluster_type` (UniRef100/90/50), `size` |
| `UniRef_get_cluster` | Cluster detail: member count, representative sequence, common taxon | `cluster_id` (e.g. `UniRef90_P00533`) |

Real example (verified live, EGFR/human): `UniParc_search {"query": "gene:EGFR
AND organism_id:9606", "size": 3}` -> 3 distinct UPI entries, each with a
different set of UniProt accessions (`Q8NDU8.1`, `Q9BZS2.1`, `Q9UMG5.1`) and
different `oldest_created` dates — UniParc treats each unique amino-acid
string as one entry regardless of which UniProt accession(s) submitted it,
so isoforms/fragments with distinct sequences get distinct UPIs even
though they share a gene name. `UniRef_get_cluster {"cluster_id":
"UniRef90_P00533"}` -> a real 119-member cluster spanning `Boreoeutheria`
(the common ancestor taxon), with a `representative_member` (`EGFR_HUMAN`,
1210 aa) that carries 9+ merged UniProtKB accessions (`P00533`, `O00688`,
...) — note the `seed_id` (`UPI0005F3CCCC`, a UniParc ID) and
`representative_member` are not always the same sequence.

Use UniParc when the question is "which UniProt accessions actually share
this exact sequence" (deduplication); use UniRef when the question is
"what else looks like this sequence at X% identity" (finding related
proteins across species for MSA/phylogenetics input, or reducing
redundancy before a proteome-wide analysis).

## Subcellular Location Vocabulary (UniProt Locations)

`UniProtLocations_search`/`UniProtLocations_get_location` resolve UniProt's
controlled subcellular-location vocabulary (organelles, membranes,
topology, orientation) by ID (`SL-XXXX`) or free-text search.

**Real gotcha, verified live:** the common term "plasma membrane" does
NOT surface UniProt's actual term for it — UniProt's controlled vocabulary
calls this location **"Cell membrane"** (`SL-0039`), not "Plasma membrane."
Searching `"plasma membrane"` or `"Plasma membrane"` returns only
tangentially related hits (e.g. `SL-0552` "Rhabdomere membrane," whose
*definition* happens to mention "plasma membrane," not the term itself).
Search a broader, UniProt-native term (`"membrane"`, `"cell"`) and scan the
results rather than assuming your everyday biology term matches UniProt's
naming — this is a real vocabulary mismatch, not a search bug.

## Sample Metadata (EBI BioSamples)

`BioSamples_search`/`BioSamples_search_by_filter`/`BioSamples_get_sample`/
`BioSamples_get_relationships`/`BioSamples_get_facets` query EBI's 60M+
sample-metadata archive (organism, tissue, disease, experimental context)
for samples that back sequencing/omics submissions — a different layer
from the sequence itself, useful for "what samples exist for condition X"
before going to ENA/SRA for the actual data.

**Real gotcha, verified live:** `BioSamples_search` with a multi-word
phrase (`"EGFR lung adenocarcinoma"`) returned **zero** results, while the
single term `"EGFR"` returned real hits immediately — the search does not
implicitly AND multiple free-text words the way a search engine would.
Use one keyword at a time, or use `BioSamples_search_by_filter` (structured
`attribute`/`value` pairs, e.g. `attribute="organism", value="Homo
sapiens"`) when you need to combine multiple real constraints. `get_facets`
is useful up front to discover which attribute values actually exist
before filtering on one (verified live: returns real facet counts, e.g.
432,302 samples for a broad text query).

## Organism Taxonomy (EBI Taxonomy)

`EBITaxonomy_get_by_id`/`get_by_scientific_name`/`search_by_name`/`suggest`
resolve organism names/IDs (NCBI Taxonomy, mirrored by EBI) — lineage,
rank, division, genetic code. Use `search_by_name` for common names
("mouse," "fruit fly") and `suggest` for type-ahead partial matching;
`get_by_scientific_name`/`get_by_id` for an exact, already-known name/ID.
Verified live: `Homo sapiens` -> `tax_id: "9606"`, full lineage string
`"Eukaryota; Metazoa; Chordata; ... Hominidae; Homo;"`.

## Cross-Domain Quick Lookup (BioThings Gateway)

`BioThings_list_apis`/`BioThings_query`/`BioThings_get_entity`/
`BioThings_get_metadata` reach ~50 BioThings-hosted APIs (drug-drug
interactions, gene-disease text-mining, PubMed-mined predications, and
more) through one Elasticsearch-style query interface — useful as a fast
first check for whether ToolUniverse has DEDICATED coverage of a resource
before reaching for this generic gateway (`BioThings_list_apis`'s
`preferred_tooluniverse_tool` field tells you when a richer dedicated tool
already exists; prefer that instead). Call `BioThings_get_metadata` before
writing a fielded `BioThings_query` so field names are correct. Verified
live: `BioThings_get_entity {"api": "mondo", "entity_id": "MONDO:0010329"}`
returns a real MONDO disease-ontology record with ancestor terms; querying
the `ddinter` API returns real drug-drug-interaction pairs with severity.
This complements `tooluniverse-data-integration-analysis`'s multi-database
evidence-gathering workflow as a fast single-call option when a dedicated
tool doesn't already exist for the resource you need.

## Cross-Database ID Resolution (Bioregistry, Identifiers.org, TogoID)

Three overlapping registries for "I have an ID in system A, what's the equivalent in system B" — verified live with a shared example (human TP53): NCBI Gene `7157` -> `TogoID_convert {"ids": "7157", "source": "ncbigene", "target": "ensembl_gene"}` -> real `ENSG00000141510`; that Ensembl gene's HGNC ID `11998` resolves via both `Bioregistry_resolve_reference {"prefix": "hgnc", "identifier": "11998"}` and `IdentifiersOrg_resolve {"namespace": "hgnc", "local_id": "11998"}` to the same genenames.org record, confirming the two registries agree.

- **Bioregistry** (`Bioregistry_resolve_reference`/`get_registry`/`get_prefix_mappings`/`search_registries`) — 2600+ prefixes, returns multiple provider URLs per identifier (bioregistry.io, identifiers.org, n2t.net, bio2rdf, and resource-specific links like GenCC/INDRA when relevant) plus prefix metadata (ID regex pattern, homepage). Use `search_registries` first when you don't know the exact prefix for a database.
- **Identifiers.org** (`IdentifiersOrg_resolve`/`get_namespace`/`search_namespaces`/`list_namespaces`) — the original MIRIAM registry; `resolve` returns full institutional/provider metadata (which organization hosts the resolver, recommended vs. alternate providers) that Bioregistry's `default` link doesn't surface. Prefer this when you need to know WHO operates the canonical resolver for a namespace, not just a URL.
- **TogoID** (`TogoID_convert`/`list_datasets`) — the only one of the three that actually CONVERTS an ID between 117 dataset types (not just gives you a URL for the ID you already have) — e.g. NCBI Gene -> Ensembl Gene -> UniProt -> PDB in one call each. Call `list_datasets` first to get valid `source`/`target` dataset-type strings.

Reach for this cluster when a workflow needs to hop between ID systems that this skill's dedicated tools (UniProt/UniParc/UniRef/EBI Taxonomy above) don't directly connect — e.g. converting a variant-analysis skill's Ensembl gene ID into the NCBI Gene ID a different tool expects.

## EBI dbfetch (One Interface, Many Databases)

`dbfetch_fetch_entry` (`db`, `id`, `format`) / `dbfetch_fetch_batch` (`db`, `ids` comma-separated, `format`) / `dbfetch_list_databases` / `dbfetch_list_formats` — fetches raw records by accession from any of 16 EBI-hosted databases (`uniprotkb`, `pdb`, `embl`, `ena_sequence`, `refseqp`, `refseqn`, `ensemblgene`, `ensembltranscript`, `interpro`, `medline`, `taxonomy`, `uniprot`, `chembl`, `afdb`, `imgtligm`, `hgnc`) through one uniform call, and can fetch several accessions from the same database in a single request via `fetch_batch`. No API key required. Verified live: `dbfetch_fetch_entry {"db": "uniprotkb", "id": "P04637", "format": "fasta"}` returns the real human p53 (P53_HUMAN) FASTA sequence; `dbfetch_fetch_batch {"db": "uniprotkb", "ids": "P04637,P01308", "format": "fasta"}` returns both p53 and insulin in one response.

**When to use this instead of the dedicated tools above**: reach for dbfetch when you need one-off or batch fetches across DIFFERENT database types without juggling per-database tools/clients (e.g. grabbing a UniProt entry and a PDB entry and an EMBL entry in a short session), or specifically need `fetch_batch`'s multi-accession-in-one-call convenience. Prefer the dedicated tools above (UniProt/UniParc/ENA/NCBI) when you need their richer structured fields (cross-references, feature annotations, curation-level metadata) — dbfetch returns the database's native flat/FASTA/XML text, not a parsed structured object.
