# Testing Plan for New ToolUniverse Skills

**Date**: 2026-02-09
**Skills to Test**: 5 new life science skills

---

## Skills Created

1. ✅ **CRISPR Screen Analysis** - Complete
2. ✅ **Drug-Drug Interaction** - Complete
3. 🔄 **Structural Variant Analysis** - Finalizing
4. 🔄 **Antibody Engineering** - Finalizing
5. 🔄 **Clinical Trial Design** - Finalizing

---

## Testing Strategy

### Phase 1: Smoke Tests (Quick validation - 5 min per skill)
Verify basic functionality without full tool execution:
- [ ] All required files exist (SKILL.md, EXAMPLES.md, README.md)
- [ ] Files are non-empty (>50 lines each)
- [ ] Skill name in metadata matches directory name
- [ ] Description is clear and actionable
- [ ] No template placeholders remaining ([FILL], [TODO], etc.)

### Phase 2: Content Quality Review (10 min per skill)
Review documentation quality:
- [ ] Report-first approach documented
- [ ] Evidence grading system present
- [ ] Tool chains documented
- [ ] Examples are realistic (not placeholders)
- [ ] Success criteria checklist included
- [ ] Citations/sources mentioned

### Phase 3: Live Tool Testing (15 min per skill)
Execute with real ToolUniverse:
- [ ] Skill can be loaded by AI agent
- [ ] Example queries produce expected workflow
- [ ] Tool chains execute without errors
- [ ] Fallback chains work when primary fails
- [ ] Report is generated progressively
- [ ] Evidence grading is applied

### Phase 4: Cross-Validation (10 min)
Check consistency across skills:
- [ ] Common patterns followed
- [ ] Evidence grading consistent
- [ ] Quality checklists similar structure
- [ ] No contradictions between skills
- [ ] Proper cross-references where applicable

---

## Test Cases Per Skill

### 1. CRISPR Screen Analysis

**Test Case 1**: Gene list from user
```
Input: ["KRAS", "EGFR", "TP53", "MYC", "CDK2"]
Expected: Essentiality scores, pathway enrichment, druggability assessment
Success Criteria: All 5 genes analyzed, top 3 prioritized, validation recommendations
```

**Test Case 2**: Cancer type query
```
Input: "pancreatic cancer"
Expected: Top 20 essential genes for pancreatic cancer
Success Criteria: KRAS appears as top hit, selective dependencies identified
```

**Test Case 3**: Single gene validation
```
Input: "WEE1"
Expected: Target validation report with TP53 synthetic lethality
Success Criteria: Essentiality score, druggability (Tchem), clinical compounds mentioned
```

---

### 2. Drug-Drug Interaction

**Test Case 1**: Simple drug pair
```
Input: "warfarin" + "amoxicillin"
Expected: CYP interaction + gut flora effects identified
Success Criteria: Risk score calculated, monitoring parameters defined
```

**Test Case 2**: Major contraindicated DDI
```
Input: "simvastatin" + "ketoconazole"
Expected: Major DDI (Score >80), contraindication, alternatives suggested
Success Criteria: Alternative statins recommended, dose adjustments documented
```

**Test Case 3**: Polypharmacy (5+ drugs)
```
Input: ["metformin", "atorvastatin", "lisinopril", "metoprolol", "aspirin"]
Expected: Pairwise DDI matrix, cumulative risk score
Success Criteria: All pairs analyzed, priority ranking, monitoring schedule
```

---

### 3. Structural Variant Analysis

**Test Case 1**: Deletion disrupting tumor suppressor
```
Input: DEL chr17:7,571,720-7,590,868 (TP53)
Expected: Pathogenic classification, loss of function
Success Criteria: ACMG criteria applied, disease association identified
```

**Test Case 2**: Duplication of dosage-sensitive gene
```
Input: DUP chr15:22,746,681-28,399,672 (PMP22)
Expected: Pathogenic, Charcot-Marie-Tooth disease
Success Criteria: Dosage sensitivity documented, clinical recommendations
```

**Test Case 3**: Common benign CNV
```
Input: DEL chr1:143,394,552-146,410,677 (benign)
Expected: Benign classification, high population frequency
Success Criteria: gnomAD frequency cited, no disease association
```

---

### 4. Antibody Engineering

**Test Case 1**: Mouse antibody humanization
```
Input: Mouse anti-HER2 antibody sequence (VH + VL)
Expected: Humanization strategy, CDR grafting recommendations
Success Criteria: Framework regions identified, human germlines suggested
```

**Test Case 2**: Affinity maturation
```
Input: Antibody with 100 nM affinity, target <10 nM
Expected: CDR mutation suggestions, affinity prediction
Success Criteria: Hot spot residues identified, mutation library designed
```

**Test Case 3**: Developability assessment
```
Input: Antibody sequence with aggregation-prone regions
Expected: Developability flags, aggregation risk scores
Success Criteria: PTM sites identified, sequence liabilities documented
```

---

### 5. Clinical Trial Design

**Test Case 1**: Biomarker-selected oncology trial
```
Input: EGFR inhibitor for EGFR-mutant NSCLC, Phase 2
Expected: Patient population size, biomarker prevalence, comparator selection
Success Criteria: Enrollment feasibility calculated, endpoints recommended
```

**Test Case 2**: Rare disease trial
```
Input: Novel therapy for disease with 1:100,000 prevalence
Expected: Global patient population, orphan drug pathway
Success Criteria: Regulatory recommendations, natural history endpoints
```

**Test Case 3**: Non-inferiority trial
```
Input: Biosimilar vs reference biologic
Expected: Non-inferiority margin selection, sample size considerations
Success Criteria: Regulatory precedents cited, endpoint selection justified
```

---

## Success Criteria

### Per-Skill Requirements
- [ ] All 3 test cases pass (or 2/3 with documented limitations)
- [ ] Report generated within 5 minutes
- [ ] All mandatory sections populated
- [ ] Evidence grading applied correctly
- [ ] Sources cited for all claims
- [ ] No unhandled errors

### Overall Project Requirements
- [ ] 5/5 skills have basic functionality
- [ ] 4/5 skills pass all test cases (80% success rate acceptable)
- [ ] Skills are clinically/scientifically useful
- [ ] Documentation is clear and comprehensive
- [ ] Skills integrate well with existing ToolUniverse

---

## Testing Timeline

| Phase | Duration | Activities |
|-------|----------|------------|
| **Phase 1** | 25 min | Smoke tests for all 5 skills |
| **Phase 2** | 50 min | Content quality review (10 min × 5) |
| **Phase 3** | 75 min | Live tool testing (15 min × 5) |
| **Phase 4** | 10 min | Cross-validation |
| **Total** | ~2.5 hours | Complete testing workflow |

---

## Issue Tracking

### Identified Issues

| Skill | Issue | Severity | Status |
|-------|-------|----------|--------|
| DDI | SKILL.md only 73 lines (should be 400-500) | Medium | Framework complete, needs expansion |
| - | - | - | - |

### Improvement Opportunities

| Skill | Opportunity | Priority |
|-------|-------------|----------|
| CRISPR | Add visualization (network plots) | Low |
| DDI | Add drug-food interactions | Medium |
| All | Add cost estimates for validation | Low |

---

## Multi-Round Improvement Plan

### Round 1: Bug Fixes (if any identified)
- Fix any broken tool chains
- Correct parameter mismatches
- Fix evidence grading inconsistencies

### Round 2: Content Enhancement
- Expand truncated SKILL.md files
- Add more examples where needed
- Improve clarity of instructions

### Round 3: User Experience
- Add quick-start examples to README
- Create flowcharts/diagrams
- Add troubleshooting sections

### Round 4: Integration
- Ensure skills work together (e.g., CRISPR → Target Research)
- Add cross-references
- Create master skill index

---

## Notes for Testing

**Tools Required**:
- ToolUniverse installed with all dependencies
- API keys for: (list will be generated during testing)
- Realistic test data (gene lists, drug names, variant coordinates)

**Expected Execution Time**:
- Short queries (single gene/drug): 30-60 seconds
- Medium queries (gene list 10-20): 2-3 minutes
- Complex queries (polypharmacy, multi-omics): 5-10 minutes

**Common Issues to Watch For**:
- API rate limits (especially for PubMed, Enrichr)
- Missing API keys (tool failures)
- Parameter type mismatches (string vs int)
- Empty results (no data found scenarios)

