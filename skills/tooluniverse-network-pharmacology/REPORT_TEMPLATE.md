# Network Pharmacology Report Template

Use this template when generating the final report in Phase 8.

---

```markdown
# Network Pharmacology Analysis: [Entity]

## Executive Summary
[2-3 sentence summary of key findings]

## Network Pharmacology Score: [X]/100 - [Tier]
| Component | Score | Max | Evidence |
|-----------|-------|-----|----------|
| Network Proximity | X | 35 | [summary] |
| Clinical Evidence | X | 25 | [summary] |
| Target-Disease Association | X | 20 | [summary] |
| Safety Profile | X | 10 | [summary] |
| Mechanism Plausibility | X | 10 | [summary] |
| **TOTAL** | **X** | **100** | |

## 1. Entity Profile
### Compound: [Name]
- ChEMBL ID: [ID]
- DrugBank ID: [ID]
- SMILES: [SMILES]
- Mechanism: [MOA]
- Approval status: [status]
- Current indications: [list]

### Disease: [Name]
- MONDO/EFO ID: [ID]
- Description: [brief]
- Top associated targets: [list with scores]
- Related diseases: [list]

## 2. Network Topology Summary
- **Total nodes**: X (Y compounds, Z targets, W diseases)
- **Total edges**: X (Y C-T, Z T-D, W C-D, V T-T)
- **Network density**: X
- **Hub nodes**: [list of top hub genes]
- **Modules detected**: X

### Drug Target Module
[List drug targets with degree and betweenness]

### Disease Gene Module
[List disease genes with degree and betweenness]

### Module Overlap
[Shared genes, shared pathways, overlap coefficient]

## 3. Network Proximity
- **Proximity measure**: [metric used]
- **Z-score**: [value]
- **Direct interactions**: X drug target-disease gene pairs
- **Shared PPI partners**: X genes
- **Shared pathways**: X pathways
- **Interpretation**: [strong/moderate/weak proximity]

## 4. Top Repurposing Candidates (Ranked)

### Candidate 1: [Drug Name] - Score: X/100
**ChEMBL ID**: [ID] | **Status**: [Approved/Clinical/Preclinical]
**Current indications**: [list]
**Network path**: Drug -> [target1, target2] -> [PPI] -> [disease gene1, gene2]
**Mechanism prediction**: [how drug could work for disease]
**Clinical evidence**: [trials, literature]
**Safety**: [key concerns]
**Evidence grade**: [T1-T4]

[Repeat for top 10 candidates]

## 5. Polypharmacology Profile
### Target Coverage
- Total drug targets: X
- Disease module targets hit: Y (Z%)
- Primary targets: [list with actions]
- Off-targets: [list with potential effects]

### Multi-Target Effects
[Analysis of synergistic vs antagonistic target modulation]

### Disease Module Coverage
[How well drug targets cover the disease network]

## 6. Pathway Analysis
### Drug-Affected Pathways
[Ranked list of pathways affected by drug]

### Disease-Associated Pathways
[Ranked list of pathways associated with disease]

### Overlapping Pathways (Mechanism)
[Pathways shared between drug and disease - these explain the mechanism]

## 7. Safety Considerations
### Adverse Events
[Top AEs with PRR/ROR where available]

### Target Safety Flags
[Targets with known safety liabilities]

### Off-Target Risks
[Off-targets in critical tissues]

### Drug-Drug Interaction Context
[Key DDI considerations]

## 8. Clinical Precedent
### Clinical Trials
[List of relevant trials with NCT IDs and status]

### Literature Evidence
[Key publications supporting or refuting repurposing hypothesis]
- N papers found for [drug] + [disease]
- Key findings: [summary]

### Pharmacogenomics
[Relevant PGx data]

## 9. Evidence Summary Table
| Finding | Source | Evidence Grade | Confidence |
|---------|--------|---------------|------------|
| [finding1] | [tool/database] | [T1-T4] | [High/Medium/Low] |
| ... | ... | ... | ... |

## 10. Recommendations
### Immediate Actions
1. [Action 1 - e.g., review clinical trial NCT00620191]
2. [Action 2 - e.g., validate mechanism in cell model]

### Further Investigation
1. [Investigation 1]
2. [Investigation 2]

### Risk Mitigation
1. [Risk 1 and mitigation strategy]

## Completeness Checklist
| Phase | Status | Tools Used | Key Findings |
|-------|--------|------------|--------------|
| Entity Disambiguation | Done/Partial/Failed | [tools] | [summary] |
| Compound Node ID | Done/Partial/Failed | [tools] | [summary] |
| Target Node ID | Done/Partial/Failed | [tools] | [summary] |
| Disease Node ID | Done/Partial/Failed | [tools] | [summary] |
| C-T Edges | Done/Partial/Failed | [tools] | [summary] |
| T-D Edges | Done/Partial/Failed | [tools] | [summary] |
| C-D Edges | Done/Partial/Failed | [tools] | [summary] |
| T-T Edges (PPI) | Done/Partial/Failed | [tools] | [summary] |
| Network Topology | Done/Partial/Failed | [computed] | [summary] |
| Network Proximity | Done/Partial/Failed | [computed] | [summary] |
| Pathway Enrichment | Done/Partial/Failed | [tools] | [summary] |
| Repurposing Candidates | Done/Partial/Failed | [tools] | [summary] |
| Mechanism Prediction | Done/Partial/Failed | [analysis] | [summary] |
| Polypharmacology | Done/Partial/Failed | [tools] | [summary] |
| Safety/Toxicity | Done/Partial/Failed | [tools] | [summary] |
| Clinical Precedent | Done/Partial/Failed | [tools] | [summary] |
| Literature Evidence | Done/Partial/Failed | [tools] | [summary] |
| Report Generation | Done/Partial/Failed | - | [summary] |
```
