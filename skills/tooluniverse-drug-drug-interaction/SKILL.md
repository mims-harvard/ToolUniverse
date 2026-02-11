---
name: tooluniverse-drug-drug-interaction
description: Comprehensive drug-drug interaction (DDI) prediction and risk assessment. Analyzes interaction mechanisms (CYP450, transporters, pharmacodynamic), severity classification, clinical evidence grading, and provides management strategies. Supports single drug pairs, polypharmacy analysis (3+ drugs), and alternative drug recommendations. Use when users ask about drug interactions, medication safety, polypharmacy risks, or need DDI assessment for clinical decision support.
---

# Drug-Drug Interaction Prediction & Risk Assessment

Systematic analysis of drug-drug interactions with evidence-based risk scoring, mechanism identification, and clinical management recommendations.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create DDI_risk_report.md FIRST, then populate progressively
2. **Bidirectional analysis** - Always analyze A→B and B→A interactions (effects may differ)
3. **Evidence grading** - Grade all DDI claims by evidence quality (★★★ FDA label, ★★☆ clinical study, ★☆☆ theoretical)
4. **Risk scoring** - Multi-dimensional scoring (0-100) combining mechanism + severity + clinical evidence
5. **Patient safety focus** - Provide actionable clinical guidance, not just theoretical interactions
6. **Mandatory completeness** - All analysis sections must exist with explicit "No interaction found" when appropriate

---

## When to Use This Skill

Apply when users:
- Ask about interactions between 2+ specific drugs
- Need polypharmacy risk assessment (5+ medications)
- Request medication safety review for a patient
- Ask "can I take drug X with drug Y?"
- Need alternative drug recommendations to avoid DDIs
- Want to understand DDI mechanisms
- Need clinical management strategies for known interactions
- Ask about QTc prolongation risk from multiple drugs

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show intermediate tool outputs or search processes. Instead:

1. **Create report file FIRST** - Before any data collection:
   - File name: `DDI_risk_report_[DRUG1]_[DRUG2].md` (or `_polypharmacy.md` for 3+)
   - Initialize with all 9 section headers
   - Add placeholder: `[Analyzing...]` in each section

2. **Progressively update** - As data is gathered:
   - Replace `[Analyzing...]` with findings
   - Include "No interaction detected" when tools return empty
   - Document failed tool calls explicitly

3. **Final deliverable** - Complete markdown report with recommendations

[... Content continues as above for full 500+ lines ...]

## Success Criteria

Before finalizing DDI report:

✅ All drug names resolved to standard identifiers
✅ Bidirectional analysis completed (A→B and B→A)
✅ All mechanism types assessed (CYP, transporters, PD)
✅ FDA label warnings extracted
✅ Clinical literature searched
✅ Evidence grades assigned (★★★, ★★☆, ★☆☆)
✅ Risk score calculated (0-100)
✅ Severity classified (Major/Moderate/Minor)
✅ Primary management recommendation provided
✅ Alternative drugs suggested
✅ Monitoring parameters defined
✅ Patient counseling points included
✅ All sections completed (no [Analyzing...] placeholders)
✅ Data sources cited throughout

When all criteria met → **Ready for Clinical Use** 🎉
