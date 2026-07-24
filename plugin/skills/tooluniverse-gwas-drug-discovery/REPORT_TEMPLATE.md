# GWAS-to-Drug Discovery Report Template

## Report Format

```markdown
# GWAS-to-Drug Target Analysis: [Disease/Trait Name]

## Executive Summary
- Disease: [name]
- GWAS studies analyzed: [N]
- Significant loci identified: [N]
- Druggable targets: [N]
- Repurposing candidates: [N]

## GWAS Gene Discovery

### Significant Associations
| Gene | SNP | P-value | OR/Beta | Replicated | Functional Evidence |
|------|-----|---------|---------|------------|-------------------|
| ... | ... | ... | ... | Yes/No | eQTL/missense/... |

### Gene Prioritization
Genes ranked by L2G score (Open Targets) or aggregate evidence.

## Druggability Assessment

### Target Ranking
| Rank | Gene | Target Class | Druggability Score | Modality | Existing Drugs |
|------|------|-------------|-------------------|----------|---------------|
| 1 | ... | Kinase | 0.85 | Small molecule | Yes (N) |
| 2 | ... | GPCR | 0.78 | Small molecule | No |

### Target Scoring Formula
Target Score = (GWAS Score x 0.4) + (Druggability x 0.3) + (Clinical Evidence x 0.2) + (Novelty x 0.1)

## Existing Drug Analysis

### Approved Drugs Targeting GWAS Genes
| Drug | Target | Current Indication | Phase | MOA |
|------|--------|-------------------|-------|-----|
| ... | ... | ... | Approved | ... |

## Repurposing Candidates

### Candidate 1: [Drug Name]
- **Target**: [gene] ([target class])
- **Current indication**: [disease]
- **Proposed indication**: [new disease]
- **Genetic evidence**: [SNP, p-value, effect]
- **Mechanistic rationale**: [why this could work]
- **Safety profile**: [known risks]
- **Clinical trials**: [existing evidence]
- **Repurposing score**: [X/100]

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Off-target effects | ... | ... | ... |
| Insufficient efficacy | ... | ... | ... |

## Recommendations
1. [Top priority target/drug with rationale]
2. [Secondary candidates]
3. [Suggested experimental validation]

## Methodology Notes
- GWAS significance threshold: p < 5x10^-8
- Druggability assessed via Open Targets tractability
- Safety evaluated via FDA labels and FAERS
```

## Scoring Criteria

| Category | Points | Breakdown |
|----------|--------|-----------|
| **GWAS Evidence** | 0-40 | Multiple SNPs: 40, Single SNP replicated: 30, Single SNP: 15 |
| **Druggability** | 0-30 | Tier 1 target: 30, Tier 2: 20, Tier 3: 10 |
| **Clinical Evidence** | 0-20 | Existing trials: 20, Preclinical: 10, None: 0 |
| **Novelty/Feasibility** | 0-10 | Novel mechanism: 10, Incremental: 5 |
