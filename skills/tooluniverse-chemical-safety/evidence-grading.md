# Evidence Grading System

Grade every toxicity claim by evidence strength.

## Tier Definitions

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | [T1] | Direct human evidence, regulatory finding | FDA boxed warning, clinical trial toxicity, human case reports |
| **T2** | [T2] | Animal studies, validated in vitro | Nonclinical toxicology, AMES positive, animal LD50 |
| **T3** | [T3] | Computational prediction, association data | ADMET-AI prediction, CTD association, QSAR model |
| **T4** | [T4] | Database annotation, text-mined | Literature mention, database entry without validation |

## Required Evidence Grading Locations

Evidence grades MUST appear in:
1. **Executive Summary** - Key toxicity findings graded
2. **Toxicity Predictions** - Every ADMET-AI endpoint with confidence note
3. **Regulatory Safety** - FDA findings marked [T1]
4. **Chemical-Gene Interactions** - CTD data marked by curation status
5. **Risk Assessment** - Final risk classification with supporting evidence tiers

## Risk Classification Matrix

| Risk Level | Criteria |
|-----------|----------|
| **CRITICAL** | FDA boxed warning present OR multiple [T1] toxicity findings OR active DILI + active hERG |
| **HIGH** | FDA warnings present OR [T2] animal toxicity OR multiple active ADMET endpoints |
| **MEDIUM** | Some [T3] predictions positive OR CTD disease associations OR structural alerts |
| **LOW** | All ADMET endpoints negative AND no FDA/DrugBank safety flags AND no CTD concerns |
| **INSUFFICIENT DATA** | Fewer than 3 phases returned data; cannot make confident assessment |
