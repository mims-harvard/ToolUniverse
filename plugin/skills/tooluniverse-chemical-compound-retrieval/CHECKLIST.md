# Chemical Compound Retrieval Checklist

Use this checklist to ensure complete compound profiles.

## Identity Resolution

- [ ] PubChem CID established
- [ ] ChEMBL ID cross-referenced (or "N/A" noted)
- [ ] Canonical SMILES captured
- [ ] IUPAC name recorded
- [ ] Naming collisions handled (if applicable)

## Chemical Properties

- [ ] Molecular formula
- [ ] Molecular weight
- [ ] LogP (lipophilicity)
- [ ] Hydrogen bond donors/acceptors
- [ ] Polar surface area
- [ ] Lipinski rule assessment

## Bioactivity Data

- [ ] Activity summary included (or "No data")
- [ ] Primary targets listed (or "Unknown")
- [ ] Key assays noted (if available)

## Drug Information (If Approved)

- [ ] Approval status
- [ ] Drug class
- [ ] Indications
- [ ] Safety warnings (if any)

## Report Quality

- [ ] Data quality tier assigned (●●●/●●○/●○○/○○○)
- [ ] Data sources cited with links
- [ ] Retrieval date included
- [ ] Search process NOT shown in output
- [ ] Results presented in clean report format

## Fallback Handling

- [ ] PubChem failure → ChEMBL search attempted
- [ ] Missing ChEMBL ID → noted as "N/A"
- [ ] No bioactivity → section exists with "No data available"
- [ ] API errors → noted as "(retrieval failed)"
