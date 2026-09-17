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
