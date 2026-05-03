# Sequence Retrieval Checklist

Use this checklist to ensure complete sequence profiles.

## Disambiguation

- [ ] Organism confirmed (scientific name)
- [ ] Gene symbol/name identified
- [ ] Sequence type determined (genomic/mRNA/protein)
- [ ] Strain specified (if relevant)
- [ ] Accession prefix identified → tool selection

## Accession Type Handling

- [ ] RefSeq (NC_, NM_, NP_, XM_) → NCBI tools only
- [ ] GenBank (U*, M*, CP*, etc.) → NCBI or ENA
- [ ] ENA tools NOT used with RefSeq accessions

## Per Sequence (Required)

- [ ] Accession number
- [ ] Organism (scientific name)
- [ ] Sequence type (DNA/RNA/protein)
- [ ] Length
- [ ] Curation level (●●●●/●●●○/●●○○/●○○○/○○○○)
- [ ] Database source

## Sequence Details

- [ ] Definition/title
- [ ] Molecule type (DNA/mRNA/protein)
- [ ] Topology (linear/circular)
- [ ] Sequence preview (first 100-200 bp)

## Annotations (If GenBank Format)

- [ ] CDS count and examples
- [ ] Gene count
- [ ] Other features noted

## Cross-References

- [ ] RefSeq accession (if exists)
- [ ] GenBank accession
- [ ] ENA compatibility noted
- [ ] BioProject/BioSample links

## Download Options

- [ ] FASTA format command shown
- [ ] GenBank format command shown
- [ ] Direct database links provided

## Report Quality

- [ ] Search process NOT shown in output
- [ ] Curation level tiers applied
- [ ] Alternative sequences listed
- [ ] Retrieval date included

## Error Handling

- [ ] No results → broader search suggested
- [ ] ENA 404 → recognized as RefSeq, NCBI used
- [ ] Large sequences → download link instead of preview
