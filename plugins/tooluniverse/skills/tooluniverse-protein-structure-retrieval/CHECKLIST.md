# Protein Structure Retrieval Checklist

Use this checklist to ensure complete structure profiles.

## Protein Disambiguation

- [ ] Protein name/gene identified
- [ ] Organism confirmed
- [ ] UniProt accession (if available)
- [ ] Naming collisions handled (kinase, receptor, etc.)

## Per Structure (Required)

- [ ] PDB ID
- [ ] Title
- [ ] Organism
- [ ] Experimental method
- [ ] Resolution (or N/A for NMR)
- [ ] Release date
- [ ] Quality assessment

## Quality Assessment

- [ ] Resolution evaluated against tiers
- [ ] R-factor/R-free noted (if X-ray)
- [ ] Completeness assessed
- [ ] Method appropriateness considered

## Structure Composition

- [ ] Chain count and identities
- [ ] Residue count and coverage
- [ ] Ligands listed (or "None bound")
- [ ] Metals/cofactors noted
- [ ] Waters (if relevant)

## Binding Site Information

- [ ] Binding sites identified (or "None")
- [ ] Key residues listed
- [ ] Druggability assessed (for drug targets)

## AlphaFold Coverage

- [ ] AlphaFold checked if no experimental structure
- [ ] Confidence scores reported
- [ ] Appropriate use cases noted

## Download Links

- [ ] PDB format link
- [ ] mmCIF format link
- [ ] AlphaFold link (if applicable)
- [ ] Database web links

## Report Quality

- [ ] Search process NOT shown in output
- [ ] Quality tiers (●●●●/●●●○/●●○○/●○○○/○○○○) applied
- [ ] Comparison table for multiple structures
- [ ] Retrieval date included

## Error Handling

- [ ] PDB not found → format verified, obsolete status checked
- [ ] No structures → AlphaFold offered
- [ ] Download failed → alternative link provided
