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

## Sequence Analysis Reasoning (CRITICAL)

**LOOK UP DON'T GUESS** -- always fetch sequences, coordinates, and domain boundaries from databases. Do not reconstruct them from memory.

### When to Use Which Tool

| Question Type | Tool Choice | Why |
|--------------|------------|-----|
| "Find similar sequences" | BLAST_protein_search | Homology search against databases; returns E-values and identity |
| "What domains does this protein have?" | InterPro_get_entries_for_protein or Pfam_get_protein_annotations | Domain architecture with exact residue coordinates |
| "Get the sequence of gene X" | NCBI_search_nucleotide -> NCBI_get_sequence | Nucleotide retrieval by gene name |
| "Compare orthologs" | NCBIDatasets_get_orthologs or EnsemblCompara_get_orthologues | Cross-species gene comparison |
| "What is the protein impact of variant X?" | EnsemblVEP_annotate_hgvs | Consequence prediction with protein coordinates |
| "Align two sequences" | BLAST (pairwise) | Quick pairwise comparison with scoring |

### Reading Frame Selection Strategy

When translating a DNA sequence to protein:
1. **Do NOT guess the reading frame** -- preferred: use `DNA_translate_reading_frames` tool; fallback: `translate_dna.py` which tries all 3 frames automatically
2. The correct frame is the one with the LONGEST open reading frame (no premature stops)
3. If the sequence starts with ATG, frame 1 is likely correct -- but verify
4. If all 3 frames have early stop codons, the sequence may be: (a) non-coding, (b) reversed, or (c) contains sequencing errors. Try reverse complement first.

### Protein Domain Interpretation

When asked about protein function or structure:
1. **Get domain architecture first**: `InterPro_get_entries_for_protein` returns all annotated domains with positions
2. **Domain families indicate function**: Kinase domain = phosphorylation activity; SH2 domain = phosphotyrosine binding; zinc finger = DNA binding
3. **Variants in conserved domains are more likely pathogenic** than those in linker regions
4. **LOOK UP** domain boundaries from the database -- do not estimate positions from memory

## Reasoning for Protein Feature Questions

When asked "how many X residues in region Y of protein Z":

1. **Identify the correct protein** — Gene names are ambiguous. GABAA has many subunits (GABRA1, GABRB2, GABRR1...). Read the question carefully for the specific subunit. Use `proteins_api_search` with gene name + "human" to find the right accession.

2. **Find the region boundaries** — Use `proteins_api_get_features` with the accession to get annotated domains (TRANSMEM, DOMAIN, REGION). Don't guess positions — get them from the database.

3. **Count residues in the region** — Fetch the sequence, extract the region, count. WRITE Python code for this — don't try to count manually.
   - **Residue Counting Strategy**: `python3 skills/tooluniverse-sequence-analysis/scripts/sequence_tools.py --type count_region --accession P24046 --start 318 --end 440 --residue C`
   - For residue counting questions, ALWAYS use the script or `sequence[start:end].count('C')`. Do NOT estimate or count from memory.

4. **Account for multimers** — READ THE QUESTION for "homomeric", "pentamer", "tetramer", "dimer". If the question asks about a homomeric receptor (e.g., "homomeric GABAAρ1"), every subunit is identical. Count the residues in ONE subunit, then multiply:
   - Homomeric pentamer (most ligand-gated ion channels like GABAA ρ1): × 5
   - Homotetramer (many ion channels): × 4
   - Homodimer: × 2
   If the question says "in the TM3-TM4 linker domains" (plural), it means across all subunits in the complex.

## Bundled Computation Scripts

**Never manually count residues, compute GC%, or write reverse-complement logic inline.** Run these scripts instead — they are tested and handle edge cases.

### biology_facts.py — Biology reference lookup

**Script**: `skills/tooluniverse-sequence-analysis/scripts/biology_facts.py`

Use this script to look up commonly-confused biology facts instead of relying on memory. It covers receptor types, ion channel stoichiometry, neurotransmitters, immune cell markers, and gene naming confusions.

```
python3 skills/tooluniverse-sequence-analysis/scripts/biology_facts.py --type receptor --name "GABAA"
python3 skills/tooluniverse-sequence-analysis/scripts/biology_facts.py --type ion_channel --name "NMDA"
python3 skills/tooluniverse-sequence-analysis/scripts/biology_facts.py --type gene_confusion --name "GABRA1"
python3 skills/tooluniverse-sequence-analysis/scripts/biology_facts.py --type receptor  # list all entries
```

Types: `receptor` (stoichiometry, pharmacology), `ion_channel` (subunit arrangement), `neurotransmitter` (synthesis, receptors), `immune_cell` (markers, lineage), `gene_confusion` (commonly mixed-up genes like GABRA1 vs GABRR1).

**Mandatory use**: any question about receptor type/stoichiometry, immune cell markers, or gene name disambiguation.

### amino_acids.py — Codon table, amino acid properties, wobble pairing

**Script**: `skills/tooluniverse-sequence-analysis/scripts/amino_acids.py`

Use this script for any question about the genetic code, codon degeneracy, amino acid chemistry, codon usage bias, or tRNA wobble pairing. All outputs are JSON.

```
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type codon_table
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --name "Cysteine"
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --code C
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid --code TRP
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type amino_acid            # list all 20
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type count_codons --sequence "ATGCCCAAATTT..."
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type wobble --anticodon "GAU"
python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type wobble --anticodon "IAU"
```

**Modes:**

| `--type` | What it returns | Key fields |
|----------|-----------------|-----------|
| `codon_table` | All 64 codons grouped by amino acid | degeneracy, codons, human codon usage %, stop codon names, degeneracy distribution (1/2/3/4/6) |
| `amino_acid` | Properties of one or all amino acids | name, one_letter, three_letter, mw_da, pKa_side_chain, polarity, charge_ph7, hydrophobicity_index (Kyte-Doolittle), backbone_pKa, codons, degeneracy, rare_codons_le15pct |
| `count_codons` | Codon frequency analysis for a DNA sequence | codon_counts with AA annotation and human usage freq, amino_acid_composition, rare_codons_present |
| `wobble` | Codons recognised by a given anticodon | recognised_codons (RNA+DNA form, AA), synonymous_only, wobble rule explanation |

**When to use (mandatory):**
- Any question about how many codons encode a given amino acid (degeneracy)
- Any question about rare vs. common codons for protein expression optimisation
- Any question about tRNA anticodon recognition / wobble base pairing
- Any question about amino acid physical-chemical properties (MW, pKa, hydrophobicity, polarity, charge)
- Any question about the names of stop codons (Amber/Ochre/Opal)
- Before manually stating codon degeneracy — verify with `codon_table`

**Wobble rules**: I pairs U/C/A (3 codons); G pairs U/C; U pairs A/G; C pairs G only; A pairs U only (rare). Use `--type wobble --anticodon "GAU"` to verify.

**Amino acid lookup**: accepts full name (`--name "Cysteine"`), 1-letter (`--code C`), or 3-letter (`--code CYS`).

### Codon-Anticodon Matching Reasoning (CRITICAL for tRNA problems)

When solving "which codons does this tRNA recognize" or "which tRNA reads this codon":

1. **Anticodon is written 3'->5'** but conventionally listed 5'->3'. The FIRST position of the anticodon (5' end) is the WOBBLE position and pairs with the THIRD position of the codon (3' end).
2. **Anticodon-codon pairing is ANTIPARALLEL**: anticodon 5'-X-Y-Z-3' pairs with codon 3'-X'-Y'-Z'-5' (i.e., codon 5'-Z'-Y'-X'-3').
3. **Wobble position rules** (anticodon 5' base -> codon 3' base it can pair with):
   - C -> G only (1 codon)
   - A -> U only (1 codon; rare in bacteria, common in mitochondria)
   - U -> A or G (2 codons)
   - G -> C or U (2 codons)
   - I (inosine, deaminated A) -> U, C, or A (3 codons)
4. **Minimum tRNA set**: Because I reads 3 bases and G/U each read 2, a 4-codon family (e.g., GCN = Ala) needs only 2 tRNAs: one with I at wobble position (reads 3 of 4 codons) and one with C or U at wobble (reads the remaining 1-2).
5. **ALWAYS use the script**: `python3 skills/tooluniverse-sequence-analysis/scripts/amino_acids.py --type wobble --anticodon "IAU"` to verify rather than reasoning from memory.

---

### translate_dna.py — DNA to protein translation

Preferred: use `DNA_translate_reading_frames` tool (via MCP/SDK) with `sequence` parameter. Fallback: run `translate_dna.py` directly.

```
python3 skills/tooluniverse-sequence-analysis/scripts/translate_dna.py "ATGCCC..."
```
Tries all 3 reading frames, picks longest ORF automatically.

### sequence_tools.py — Residue counting, GC content, reverse complement, stats

**Script**: `skills/tooluniverse-sequence-analysis/scripts/sequence_tools.py`

**Preferred**: Use ToolUniverse tools (via MCP/SDK) instead of the script:
- `Sequence_count_residues` tool -- Count residues in a sequence or region. Fallback: `sequence_tools.py --type count_residues` or `--type count_region`
- `Sequence_gc_content` tool -- GC% of DNA. Fallback: `sequence_tools.py --type gc_content`
- `Sequence_reverse_complement` tool -- DNA reverse complement. Fallback: `sequence_tools.py --type reverse_complement`
- `Sequence_stats` tool -- Auto-detect type, length, MW. Fallback: `sequence_tools.py --type stats`

**Fallback script modes** (use `--type`):
- `count_residues`: Count residue in full sequence. `--sequence "ACDE..." --residue C`
- `count_region`: Count in region (1-based inclusive). `--sequence "MAC..." --start 5 --end 20 --residue C` OR `--accession P24046 --start 318 --end 440 --residue C` (fetches from UniProt live)
- `gc_content`: GC% of DNA. `--sequence "ATGCGATCG"`
- `reverse_complement`: DNA reverse complement. `--sequence "ATGCGATCG"`
- `stats`: Auto-detect DNA/RNA/Protein, compute length, MW for protein. `--sequence "ATGCG..."`

ALWAYS use `count_region --accession` when the user gives a UniProt accession + region -- do not count manually.

---

## Interpretation Framework

### Sequence Quality Assessment

| Indicator | High Quality | Acceptable | Caution |
|-----------|-------------|-----------|---------|
| **RefSeq status** | NM_/NP_ (curated) | XM_/XP_ (predicted) | No RefSeq (GenBank only) |
| **Sequence version** | Latest version (.N) | Previous version | Removed/replaced |
| **Annotation** | Reviewed (UniProt Swiss-Prot) | Unreviewed (TrEMBL) | No annotation |
| **Gene symbol** | HGNC approved | Alias/synonym | Locus tag only |

### Synthesis Questions

1. **Is this the correct sequence?** (verify organism, gene symbol, isoform)
2. **Is it the canonical isoform?** (RefSeq MANE Select or UniProt canonical)
3. **How well-annotated is it?** (SwissProt > TrEMBL > GenBank predicted)
4. **Are there known variants?** (ClinVar pathogenic variants in this sequence)

---

## Answer Formatting (CRITICAL)

**TRIM YOUR ANSWER**: If the question asks "what protein", answer with JUST the protein name. Do not add parenthetical abbreviations, descriptions, or qualifications. Example: answer "Glucose-6-phosphate 1-dehydrogenase", NOT "Glucose-6-phosphate 1-dehydrogenase (G6PD, EC 1.1.1.49)". When identifying a protein from a sequence, use BLAST/UniProt and report the top hit name exactly as it appears in the database — no embellishment.

## Peptide & Foldamer Structure

- **Alpha-peptide helices**: alpha-helix (3.6 res/turn, i->i+4 H-bonds), 3_10-helix (3 res/turn, i->i+3), pi-helix (4.4 res/turn, i->i+5).
- **Beta-peptide helices**: named by H-bond ring size. 14-helix (i->i+2, 14-membered rings), 12-helix, 10-helix, 8-helix.
- **Beta-amino acid ring size determines helix type**: 4-membered cyclic constraint -> 10-helix; 5-membered (e.g., ACPC) -> 12-helix; 6-membered (e.g., ACHC) -> 14-helix. Acyclic beta3-residues default to 14-helix.
- **Mixed alpha/beta foldamers (1:1 alternation)**: form 11-helix (i->i+3, 11-atom rings) or 14/15-helix (i->i+4, alternating 14- and 15-atom rings). Longer sequences prefer the 14/15-helix.
- **Key rule**: the number in the helix name = number of atoms in the hydrogen-bonded ring.
- **Cyclic beta-amino acids** (ACPC, ACHC) constrain backbone torsion angles, favoring specific helix types over acyclic residues.

## Limitations

- ensembl_get_sequence gene IDs + non-genomic type need `multiple_sequences=true`
- NCBIDatasets_get_orthologs requires NCBI Gene ID (not symbol); UniProt returns canonical isoform only
