# Drug Repurposing Report Template

## Output Format

Present results as ranked candidates:

```markdown
## Drug Repurposing Analysis: [Disease Name]

### Top 10 Repurposing Candidates

#### 1. [Drug Name] (Score: 87/100)

**Current Indications**: [list approved uses]
**Proposed Indication**: [new disease/condition]
**Repurposing Rationale**: Targets [gene/protein] with high association to disease

**Evidence Summary**:
- Target association score: 0.85
- Approval status: FDA approved (safer profile)
- Literature support: 23 papers, 4 clinical trials
- Safety profile: No black box warnings

**Mechanism**: [Brief mechanism description]

**Next Steps**:
- Phase II trial feasibility assessment
- Patient population identification
- Dosing optimization study

**Key Papers**:
1. Smith et al. 2024 - Clinical efficacy in similar condition
2. Jones et al. 2023 - Mechanism validation

---

#### 2. [Drug Name] (Score: 79/100)
[Similar structure...]

### Supporting Analysis

**Target Network**: [visualization or description]
**Pathway Overlap**: [affected pathways]
**Safety Considerations**: [major concerns]
**Development Timeline**: [estimated phases]
```

## Scoring Criteria

**Target Association (0-40 points)**:
- Strong genetic evidence: 40
- Moderate association: 25
- Pathway-level evidence: 15
- Weak/predicted: 5

**Safety Profile (0-30 points)**:
- FDA approved: 20
- Phase III: 15
- Phase II: 10
- Phase I: 5
- No black box warning: +10
- Known serious AE: -10

**Literature Evidence (0-20 points)**:
- Clinical trials: 5 points each (max 15)
- Preclinical studies: 1 point each (max 10)
- Case reports: 0.5 points each (max 5)

**Drug Properties (0-10 points)**:
- High bioavailability: 5
- Good BBB penetration (if CNS): 5
- Low toxicity predictions: 5
