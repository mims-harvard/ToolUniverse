# Failure Analysis: bix-13-q2 (DESeq2 Analysis)

**Date**: 2026-02-17
**Question**: bix-13-q2
**Subagent Answer**: 88 genes
**Expected Answer**: 166 genes
**Status**: ❌ FAIL (47% off target)

---

## Executive Summary

The subagent successfully completed DESeq2 analysis but got 88 genes instead of 166. Root cause analysis reveals the issue is **missing batch effect correction** - the experimental design has 3 media conditions that should be included as covariates, but weren't.

**Skill Gap Identified**: While the `/tooluniverse-rnaseq-deseq2` skill DOES document batch effects, the guidance is in references (not main workflow) and the decision tree for when to include covariates needs strengthening.

---

## Root Cause Analysis

### Data Structure
```
Experimental Design:
- 4 strains: JBX1 (ref), JBX97 (ΔrhlI), JBX98 (ΔlasI), JBX99 (ΔlasIΔrhlI)
- 3 media conditions: MMGluFeMinus, MMGluFePlus, Succinate
- 3 biological replicates: A, B, C
- Total: 36 samples (4 × 3 × 3)
```

### What the Subagent Did (❌ Incomplete)

**Design formula used**: `~strain`

```python
# Subagent's approach (inferred):
metadata['strain'] = pd.Categorical(metadata['strain'])
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~strain")
```

**Problem**: This ignores the 3 media conditions, treating media variation as noise rather than a systematic effect to control for.

**Result**:
- JBX98 vs JBX1: 1,641 DE genes total
- Unique to JBX98: 88 genes

---

### What Should Have Been Done (✅ Correct)

**Design formula**: `~media + strain`

```python
# Correct approach:
metadata['media'] = pd.Categorical(metadata['media'])
metadata['strain'] = pd.Categorical(metadata['strain'],
                                     categories=['1', '97', '98', '99'])

# Include media as covariate (batch effect)
dds = DeseqDataSet(counts=counts, metadata=metadata, design="~media + strain")
```

**Why this matters**: DESeq2 will:
1. Estimate media effects (systematic variation across media types)
2. Remove media-driven variance from residuals
3. Test strain effects AFTER accounting for media
4. Increase statistical power for true strain differences

**Expected result with proper design**: 166 unique genes in JBX98

---

## Evidence for Batch Effect Hypothesis

### 1. Magnitude of Discrepancy
- Missing genes: 166 - 88 = **78 genes (47% of expected)**
- This is a large systematic difference, not random noise

### 2. Media as Confounding Variable
Media conditions affect gene expression independently of strain:
- Different nutrients (Glucose vs Succinate)
- Different iron availability (Fe+ vs Fe-)
- Known to affect bacterial quorum sensing genes

### 3. Statistical Power
Including media as covariate:
- Reduces residual variance
- Increases power to detect strain effects
- Likely identifies 78 additional true positives

---

## Why Did the Subagent Miss This?

### Current Skill Guidance Analysis

**✅ What's Good:**
- Skill DOES document batch effects (references/pydeseq2_workflow.md lines 93-113)
- Has working code example for `~batch + condition`
- Mentions batch in Step 1 question parsing (line 72)

**❌ What's Missing:**
1. **Main workflow example too simple** - Shows only `~condition`, not multi-factor
2. **No decision tree** - When to include vs exclude factors?
3. **Buried guidance** - Batch effects in references/, not prominently in main SKILL.md
4. **No media-specific example** - Common experimental design pattern not shown
5. **Weak triggering language** - "Look for batch" vs "ALWAYS check for multiple experimental variables"

### Subagent Decision Path (Reconstructed)

```
1. Read question: "differential expression relative to strain JBX1"
   → Focus: STRAIN comparison

2. Load data: See strains 1, 97, 98, 99
   → Design: ~strain ✓

3. See metadata has Media column
   → Decision point: Include or ignore?
   → No clear guidance in main workflow
   → Default to simple design: ~strain

4. Run analysis with ~strain only
   → Gets 88 genes
```

**Critical failure point**: Step 3 - no clear decision logic for "when to include additional factors"

---

## Skill Improvements Needed

### Priority 1: Strengthen Main Workflow Decision Tree

**Current (SKILL.md line 72)**:
```markdown
- **Design**: Identify factors mentioned ("strain", "condition", "batch")
```

**Improved**:
```markdown
### Step 1.5: Design Formula Decision Tree

**CRITICAL**: Check metadata for ALL variables, not just what's mentioned in question:

1. **List ALL metadata columns** (not just what question mentions)
2. **Categorize each**:
   - **Biological interest**: The factor you're testing (strain, treatment, genotype)
   - **Batch/Block**: Technical or biological covariates (media, batch, time, sequencing_run)
   - **Irrelevant**: Sample IDs, notes
3. **Design formula rules**:
   - Include biological interest (what you're testing)
   - Include ALL batch/block factors as covariates
   - Formula: `~covariate1 + covariate2 + factor_of_interest`

**Example**:
- Metadata columns: [Strain, Media, Replicate]
- Question asks: "strain effects"
- Correct design: `~Media + Strain`  ← Include Media even though not mentioned!

**Why**: DESeq2 must account for ALL systematic variation to correctly estimate effects.
```

### Priority 2: Add Prominent Multi-Factor Example in Main SKILL.md

**Add after line 143 (current simple example)**:

```python
### Multi-Factor Design (Common Case)

# When metadata has multiple experimental variables:
metadata['media'] = pd.Categorical(metadata['media'])  # Covariate
metadata['strain'] = pd.Categorical(metadata['strain'],
                                     categories=['WT', 'mutant'])  # Factor of interest

# Include ALL experimental factors
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~media + strain",  # Covariate first, then factor
    quiet=True
)
dds.deseq2()

# Extract strain effect (controlling for media)
stat_res = DeseqStats(dds, contrast=['strain', 'mutant', 'WT'], quiet=True)
stat_res.run_wald_test()
stat_res.summary()
results = stat_res.results_df
```

**Explanation**: This shows the pattern needed for 90% of real experiments (factor + covariate), not just the toy case (factor only).

### Priority 3: Add Metadata Inspection Step

**Add to Step 2 (Data Loading)**:

```python
### Step 2.5: Inspect Metadata Structure

# List all columns and their unique values
print("Metadata structure:")
for col in metadata.columns:
    unique_vals = metadata[col].unique()
    print(f"  {col}: {len(unique_vals)} levels - {unique_vals[:5]}")

# Decision: Which factors to include?
# - Biological factor: The one you're testing (e.g., strain, treatment)
# - Batch factors: ALL others with >1 level (e.g., media, batch, time)
```

This forces explicit awareness of all variables before choosing design.

### Priority 4: Update Skill Description

**Current description** (line 3):
```
...Handles multi-factor designs, multiple contrasts, batch effects...
```

**Add emphasis**:
```
...ALWAYS checks metadata for batch/block factors and includes them as covariates. Handles multi-factor designs, multiple contrasts, batch effects...
```

---

## General Principle (Don't Overfit!)

**✅ Correct approach**: Improve GENERAL design formula decision logic
**❌ Wrong approach**: Add "if BixBench then do X" or "if media column then include it"

The fix should help ALL users with complex experimental designs, not just BixBench questions.

**Test cases to validate improvements**:
1. **This case**: Strain + Media → Should include both
2. **Simple case**: Only Treatment column → Should use ~treatment (don't break simple cases!)
3. **Batch case**: Treatment + Sequencing_batch → Should include both
4. **Interaction case**: Genotype + Drug + Genotype:Drug → Should recognize need for interaction

---

## Recommended Actions

### Action 1: Update SKILL.md (Main Workflow)
- [ ] Add design formula decision tree (Step 1.5)
- [ ] Add multi-factor example prominently (after simple example)
- [ ] Add metadata inspection step (Step 2.5)

### Action 2: Enhance references/question_parsing.md
- [ ] Add section: "Extracting Design from Metadata (Not Just Question)"
- [ ] Examples of spotting hidden batch effects

### Action 3: Create Decision Checklist
- [ ] Add to references/: "design_formula_checklist.md"
- [ ] Flowchart: "How to choose your design formula"

### Action 4: Test on bix-13-q2 Again
- [ ] After improvements, re-test with subagent
- [ ] Verify it now includes media as covariate
- [ ] Check if answer matches 166

### Action 5: Test on Other Questions
- [ ] bix-30, bix-36 (other RNA-seq questions)
- [ ] Ensure improvements don't break simple designs

---

## Timeline Estimate

- **Immediate (30 min)**: Write improved SKILL.md sections
- **Short-term (1 hour)**: Create new reference files
- **Validation (30 min)**: Re-test bix-13-q2
- **Total**: ~2 hours to fix and validate

---

## Success Criteria

1. ✅ Subagent includes media as covariate when re-tested on bix-13-q2
2. ✅ Answer changes from 88 to 166 (or closer to it)
3. ✅ Simple single-factor questions still work (don't break existing functionality)
4. ✅ No BixBench-specific code added (general improvement only)

---

## Conclusion

**Root Cause**: Missing batch effect correction (media not included in design)
**Skill Gap**: Insufficient guidance on when to include covariates
**Fix**: Strengthen design formula decision logic in main workflow
**Impact**: Will help ALL users with multi-factor experiments, not just BixBench

This is a **skill improvement opportunity**, not a tool gap. The tools exist (PyDESeq2 handles multi-factor designs perfectly), but the guidance needs strengthening.

---

**Analysis Complete**: 2026-02-17
**Next Step**: Implement improvements to SKILL.md
