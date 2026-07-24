# Sequence Retrieval Examples

## Example 1: Find E. coli K-12 Genome

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Search
result = tu.tools.NCBI_search_nucleotide(
    operation="search",
    organism="Escherichia coli",
    strain="K-12",
    seq_type="complete_genome",
    limit=3
)

# Get accessions
accessions = tu.tools.NCBI_fetch_accessions(
    operation="fetch_accession",
    uids=result["data"]["uids"]
)

# Get sequence (RefSeq reference)
sequence = tu.tools.NCBI_get_sequence(
    operation="fetch_sequence",
    accession="NC_000913.3",
    format="fasta"
)

print(f"Genome size: {len(sequence['data'])} characters")
```

## Example 2: Get Human BRCA1 Gene

```python
# Search for BRCA1
result = tu.tools.NCBI_search_nucleotide(
    operation="search",
    organism="Homo sapiens",
    gene="BRCA1",
    limit=5
)

print(f"Found {result['data']['count']} BRCA1 sequences")

# Get top accessions
accessions = tu.tools.NCBI_fetch_accessions(
    operation="fetch_accession",
    uids=result["data"]["uids"]
)

# Get mRNA sequence with annotations
genbank = tu.tools.NCBI_get_sequence(
    operation="fetch_sequence",
    accession=accessions["data"][0],
    format="genbank"
)
```

## Example 3: SARS-CoV-2 Reference Genome

```python
# Search for reference genome
result = tu.tools.NCBI_search_nucleotide(
    operation="search",
    organism="SARS-CoV-2",
    keywords="reference genome Wuhan",
    limit=1
)

# Get accession (NC_045512)
accessions = tu.tools.NCBI_fetch_accessions(
    operation="fetch_accession",
    uids=result["data"]["uids"]
)

# Download complete genome
genome = tu.tools.NCBI_get_sequence(
    operation="fetch_sequence",
    accession="NC_045512.2",
    format="fasta"
)

print(genome["data"][:200])  # Preview
```

## Example 4: Compare RefSeq vs GenBank

```python
# Search returns both types
result = tu.tools.NCBI_search_nucleotide(
    operation="search",
    organism="Escherichia coli",
    strain="K-12",
    limit=5
)

accessions = tu.tools.NCBI_fetch_accessions(
    operation="fetch_accession",
    uids=result["data"]["uids"]
)

# Categorize
refseq = [a for a in accessions["data"] if a.startswith("NC_")]
genbank = [a for a in accessions["data"] if not a.startswith("NC_")]

print(f"RefSeq (NCBI only): {refseq}")
print(f"GenBank (ENA compatible): {genbank}")
```

## Example 5: Multi-Format Retrieval

```python
accession = "NC_000913.3"

# FASTA (sequence only)
fasta = tu.tools.NCBI_get_sequence(
    operation="fetch_sequence",
    accession=accession,
    format="fasta"
)

# GenBank (with annotations)
genbank = tu.tools.NCBI_get_sequence(
    operation="fetch_sequence",
    accession=accession,
    format="genbank"
)

# EMBL format
embl = tu.tools.NCBI_get_sequence(
    operation="fetch_sequence",
    accession=accession,
    format="embl"
)
```
