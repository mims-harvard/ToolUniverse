---
name: tooluniverse-sequence-analysis
description: Retrieve and analyze biological sequences -- gene/protein sequences from NCBI, Ensembl, and UniProt. Search nucleotide databases, fetch by accession, find orthologs, get gene summaries. Use when users ask about DNA/RNA/protein sequences, gene lookups, ortholog searches, or sequence retrieval.
---

# Biological Sequence Analysis

Retrieve, annotate, and compare biological sequences from NCBI, Ensembl, and UniProt. Covers nucleotide search, sequence fetching, gene summaries, ortholog discovery, and protein sequence extraction.

## When to Use

- "Get the mRNA sequence for BRCA1"
- "Search NCBI for E. coli K-12 complete genome"
- "Find orthologs of TP53 across species"
- "Fetch the protein sequence for UniProt P04637"
- "Get the CDS sequence for Ensembl transcript ENST00000269305"

## Workflow

```
Input -> Phase 1: Gene ID resolution -> Phase 2: Nucleotide retrieval
      -> Phase 3: Protein sequences -> Phase 4: Orthologs -> Output
```

## Phase 1: Gene Identification and Summary

**NCBIGene_search**: `term` (string REQUIRED, format `"TP53[Symbol] AND Homo sapiens[Organism]"`), `retmax` (int, default 10). Returns `{status, data: {esearchresult: {idlist: ["7157"]}}}`.

**NCBIGene_get_summary**: `id` (string REQUIRED, e.g., "7157"). Returns `{status, data: {result: {"7157": {name, description, summary, chromosome, maplocation, genomicinfo, mim}}}}`. Result is keyed by gene ID string.

**NCBIDatasets_get_gene_by_symbol**: `symbol` (string REQUIRED, e.g., "BRCA1"), `taxon` (string, e.g., "human"). Returns gene ID, description, location, cross-references.

**NCBIDatasets_get_gene**: `gene_id` (string REQUIRED, e.g., "7157"). Returns comprehensive gene info.

## Phase 2: Nucleotide Sequence Search and Retrieval

**NCBI_search_nucleotide**: `query` (free-form), `organism` (string), `gene` (string), `strain` (string), `keywords` (string), `seq_type` ("complete_genome"/"mRNA"/"refseq"), `limit` (int, default 20). Returns `{status, data: {uids: [...], accessions: [...]}}`.

**NCBI_fetch_accessions**: `uids` (array REQUIRED, e.g., ["545778205"]). Returns `{status, data: ["U00096.3"], count: 1}`.

**NCBI_get_sequence**: `accession` (string REQUIRED, e.g., "NM_007294"), `format` ("fasta"/"gb"/"embl"). Returns `{status, data: "FASTA string...", accession, format, length}`.

**EnsemblSeq_get_region_sequence**: `region` (string REQUIRED, "chr:start-end", e.g., "17:7668421-7668520"), `species` (default "homo_sapiens"). Returns `{status, data: {sequence, sequence_length}}`.

**ensembl_get_sequence**: `id` (string REQUIRED, Ensembl ID), `type` ("genomic"/"cds"/"cdna"/"protein"), `multiple_sequences` (bool). Returns sequence data.

**Gotchas**:
- NCBI_search_nucleotide returns UIDs, not accessions. Use NCBI_fetch_accessions to convert.
- NCBI_fetch_accessions requires `uids` (NOT `accessions`).
- ensembl_get_sequence with gene ID (ENSG) + type != "genomic" requires `multiple_sequences=true`. Use transcript IDs (ENST) for specific sequences.

### Recipe: Get mRNA for a human gene
1. `NCBI_search_nucleotide(organism="Homo sapiens", gene="BRCA1", seq_type="mRNA", limit=5)`
2. `NCBI_fetch_accessions(uids=[first_uid])` -> accession
3. `NCBI_get_sequence(accession="NM_007294", format="fasta")`

## Phase 3: Protein Sequence Retrieval

**UniProt_get_sequence_by_accession**: `accession` (string REQUIRED, e.g., "P04637"). Returns `{result: "MEEPQSDP..."}`. **Note**: response key is `result`, NOT `data`.

**EnsemblSeq_get_id_sequence**: `ensembl_id` (string REQUIRED, e.g., "ENSP00000269305"), `type` ("protein"/"cdna"/"cds"). Returns `{status, data: {ensembl_id, molecule, sequence, sequence_length}}`.

**UniProt_get_entry_by_accession**: `accession` (string REQUIRED). Full protein annotation.

**Gotchas**:
- UniProt_get_sequence_by_accession returns `{result: "..."}`, not `{status, data}`.
- For Ensembl protein seqs, use ENSP IDs. For cDNA/CDS, use ENST IDs.
- To find UniProt accession from gene: use NCBIDatasets_get_gene_by_symbol (has cross-refs).

## Phase 4: Ortholog and Comparative Analysis

**NCBIDatasets_get_orthologs**: `gene_id` (string REQUIRED, NCBI Gene ID e.g., "7157"), `page_size` (int, default 20, max 100). Returns `{status, data: [{gene_id, symbol, description, taxname, common_name, chromosomes}]}`.

**NCBIProtein_get_summary**: `id` (string REQUIRED, GI number or accession). Returns protein title, organism, length.

**Gotcha**: NCBIDatasets_get_orthologs requires NCBI Gene ID (numeric string), not gene symbol or Ensembl ID. Resolve via Phase 1 first.

### Recipe: Compare orthologs
1. `NCBIGene_search(term="TP53[Symbol] AND Homo sapiens[Organism]")` -> "7157"
2. `NCBIDatasets_get_orthologs(gene_id="7157", page_size=10)` -> mouse Trp53, rat Tp53, etc.

## Phase 5: Domain Architecture and Homology

**InterPro_get_entries_for_protein**: `accession` (UniProt ID). Returns InterPro domain/family/superfamily entries with positions.

**Pfam_get_protein_annotations**: `accession` (UniProt ID). Returns Pfam domain hits with exact residue coordinates and E-values.

**BLAST_protein_search**: `sequence` (amino acid string), `database` (default "swissprot"), `limit`. Returns homologs with alignment scores, identity, E-values.

**EnsemblCompara_get_orthologues**: `gene` (gene symbol, e.g., "CFTR"), `species` (e.g., "human"). User-friendly alternative to NCBIDatasets_get_orthologs — accepts gene symbols directly.

## Phase 6: Variant and Clinical Context

**EnsemblVEP_annotate_hgvs**: `hgvs_notation` (e.g., "NM_000492.4:c.1521_1523del"). Returns consequence, protein impact, genomic coordinates.

**ClinVar_search_variants**: `gene` (gene symbol). Returns variant count and IDs for clinical significance lookup.

**PubMed_search_articles**: `query`, `limit`. Literature context for gene/variant findings.

---

## Tool Parameter Quick Reference

| Tool | Correct Param | Common Mistake |
|------|--------------|----------------|
| NCBIGene_search | `term` (with [Symbol] syntax) | `query` or `gene` |
| NCBIGene_get_summary | `id` (string) | Integer type |
| NCBI_fetch_accessions | `uids` (array) | `accessions` |
| NCBI_get_sequence | `accession` (string) | Passing UID |
| NCBIDatasets_get_orthologs | `gene_id` (string) | Gene symbol |
| EnsemblSeq_get_id_sequence | `ensembl_id` | `id` |
| ensembl_get_sequence | `id` + `multiple_sequences` | Omitting multiple_sequences for gene+CDS |
| UniProt_get_sequence_by_accession | `accession` | Response is `result` not `data` |

## Fallbacks

- Gene not found -> try NCBIDatasets_get_gene_by_symbol with explicit taxon
- No accessions from search -> broaden query (remove strain/seq_type filters)
- Ensembl error for gene+CDS -> use transcript ID (ENST) or set multiple_sequences=true
- UniProt accession unknown -> NCBIDatasets_get_gene or UniProt_search for cross-refs
- Ortholog search empty -> verify gene_id is numeric NCBI Gene ID

## Limitations

- NCBI_get_sequence returns full sequence as string; very large genomes may be slow
- ensembl_get_sequence gene IDs + non-genomic type need multiple_sequences flag
- NCBIDatasets_get_orthologs requires NCBI Gene ID (not symbol or Ensembl)
- UniProt_get_sequence_by_accession returns only the canonical isoform
- EnsemblSeq_get_region_sequence has practical size limits on regions
