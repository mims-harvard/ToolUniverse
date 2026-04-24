---
name: devtu-benchmark-harness
description: "Continuous improvement system for ToolUniverse tools, skills, and plugin. Run benchmarks, diagnose failures, route fixes to devtu skills, retest. Use after skill optimization, tool additions, or as regression check."
---

# Benchmark Harness — Continuous Improvement System

A 5-step feedback loop for improving ToolUniverse tools, skills, and plugin quality.

**Note**: This skill is dataset-agnostic. Per-benchmark score history, known-failing question IDs, and dataset-specific investigations belong in `temp_docs_and_tests/benchmark_tracking/` (gitignored workfolder), NOT in this skill directory.

## The Feedback Loop

```
1. RUN benchmark → 2. ANALYZE results → 3. DIAGNOSE failures → 4. FIX via devtu skill → 5. RETEST → repeat
```

## Orchestrated runner (preferred)

One command does steps 0 (memorization audit), 1 (build), 2 (run), 3 (analyze), 4 (diagnose + extract failures):

```bash
bash skills/devtu-benchmark-harness/scripts/run_harness_loop.sh --benchmark bixbench --n 20 --seed 42
# After reviewing diagnose.log and applying devtu skill fixes:
bash skills/devtu-benchmark-harness/scripts/run_harness_loop.sh --retest /path/to/failures.json
```

The script creates `temp_docs_and_tests/benchmark_tracking/run_<TS>/` with results.json, analysis.log, diagnose.log, failures.json. Diagnose output lists each failure with the exact devtu skill to invoke — do NOT fix manually.

## Anti-memorization guard

Before accepting any skill edit (from `devtu-optimize-skills` or manual), run:

```bash
python3 skills/devtu-benchmark-harness/scripts/check_memorization.py --all
```

Fails if any skill contains benchmark names, capsule UUIDs, `bix-N` question IDs, or known-to-be-GT specific numeric answers. This prevents overfitting the plugin to a single benchmark's answer key. Run in `--strict` mode to also flag specific gene names and dataset filenames (softer signal).

## Step 1: RUN — Execute Benchmark

```bash
bash scripts/build-plugin.sh   # rebuild plugin with latest skills

python skills/devtu-benchmark-harness/scripts/run_eval.py \
  --benchmark bixbench \        # bixbench | lab-bench | custom
  --mode plugin-only \          # plugin-only | baseline-only | comparison
  --n 205 \                     # number of questions
  --timeout 1800 \              # seconds per question
  --max-turns 30                # agent turns per question
```

Options: `--category DESeq2` (filter), `--resume results.json` (skip done), `--guidance path.md` (inject custom).

### Reliability mode: APPEND_CONVENTIONS env var
Skill auto-matching in interactive mode is variable — sometimes Claude reads the skill description but starts writing code before loading the skill body. To force the router's critical conventions into every request's system prompt (more reliable, measures the plugin's conventions as-designed rather than skill-routing-as-implemented):

```bash
APPEND_CONVENTIONS=1 python skills/evals/run_benchmark.py --benchmark bixbench --plugin-only
```

Use this mode when measuring the CORRECTNESS of the conventions (are they the right rules?). Use default mode when measuring the RELIABILITY of skill routing (does Claude actually invoke the skill?). The gap between these two numbers is the routing-reliability problem.

### Benchmark setup (first time only)
```bash
Rscript skills/evals/install_r_packages.R                  # R packages
python3 skills/evals/bixbench/download_capsules.py         # BixBench data (~5 GB)
```

### Available benchmarks

| Benchmark | Questions | Tests | Data |
|-----------|----------|-------|------|
| lab-bench | 20 MCQ | Database lookup accuracy | `skills/evals/lab-bench/questions.json` |
| bixbench | 205 computational | Data analysis + statistics | `skills/evals/bixbench/questions.json` + capsule data |
| custom | User-defined | Any | Custom JSON file |

## Step 2: ANALYZE — Map Failures to Skills

```bash
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json \
  --questions skills/evals/bixbench/questions.json \
  --benchmark bixbench
```

Output:
- **By skill**: which skills have lowest accuracy (fix those first)
- **By category**: DESeq2, ANOVA, phylogenetics, variant_analysis, etc.
- **Failure types**: timeout, wrong_answer, tool_error, api_key_missing

### Category → Skill mapping

| Category | Skill |
|----------|-------|
| DESeq2, fold_change | tooluniverse-rnaseq-deseq2 |
| ANOVA, regression, chi_square, spline_fitting | tooluniverse-statistical-modeling |
| pathway_enrichment, DESeq2+enrichGO | tooluniverse-gene-enrichment |
| phylogenetics | tooluniverse-phylogenetics |
| variant_analysis, epigenomics | tooluniverse-variant-analysis |
| crispr_screen, functional_genomics | tooluniverse-crispr-screen-analysis |
| single_cell | tooluniverse-single-cell |

## Step 3: DIAGNOSE — Get Improvement Recommendations

```bash
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json \
  --questions skills/evals/bixbench/questions.json \
  --diagnose
```

Each recommendation includes the failing category, responsible skill, failure type, and which devtu skill to invoke for the fix.

### Root cause investigation

For each failure, verify whether it's an agent error or a GT (ground truth) issue:
1. Find the capsule data: `temp_docs_and_tests/bixbench/bixbench/data/CapsuleFolder-{uuid}/`
2. Look for authoritative scripts: `*.py`, `*.R`, `analysis.R`, `run_*.py`
3. Run the script yourself — does it reproduce the GT value?
4. If your computation matches the agent (not the GT), it's a **GT issue**, not an agent error

## Step 4: FIX — Route to the Right devtu Skill

**Do not fix manually** — use devtu skills so fixes follow established patterns and include tests.

| Diagnosis | What to do | Invoke |
|-----------|-----------|--------|
| Tool returns wrong data | Fix tool code + JSON config | `Skill('devtu-fix-tool')` |
| No tool exists for this computation | Create new ToolUniverse tool | `Skill('devtu-create-tool')` |
| Skill gives wrong guidance | Update SKILL.md conventions | `Skill('devtu-optimize-skills')` |
| Agent needs bundled script | Add script to skill's scripts/ dir | `Skill('devtu-optimize-skills')` Pattern 15 |
| Grader false negative | Fix `grade_answers.py` | Direct code fix |
| Multiple coordinated changes | Full cycle | `Skill('devtu-self-evolve')` |

### Fix workflow

```
1. analyze_results.py --diagnose → get recommendations
2. For each recommendation → invoke the appropriate devtu skill
3. bash scripts/build-plugin.sh → rebuild dist
4. run_eval.py --retest failures.json → verify fix
```

### Example

```
Diagnosis: "ANOVA wrong_answer → tooluniverse-statistical-modeling"
  → Invoke: Skill('devtu-optimize-skills')
  → Tell it: "statistical-modeling skill produces wrong F-statistics for
     per-gene expression ANOVA. Agent aggregates at sample level instead
     of gene level."
  → The skill handles: read SKILL.md, add convention, verify no
     memorization, rebuild, suggest retest.
```

## Step 5: RETEST — Verify Fixes

```bash
# Extract failed question IDs
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json --extract-failures /tmp/failures.json

# Retest only failures
python skills/devtu-benchmark-harness/scripts/run_eval.py \
  --benchmark bixbench --mode plugin-only --retest /tmp/failures.json
```

Compare: how many flipped from wrong to correct? Update baseline if improved.

## Grader

`grade_answers.py` applies 7 strategies in order:

1. **Exact match** — GT substring in prediction
2. **MC match** — letter answer detection (A/B/C/D)
3. **Range match** — numeric value within (low, high) with rounding tolerance
4. **Normalized match** — strip punctuation, bidirectional substring + bold-segment extraction
5. **Numeric proximity** — within 5% tolerance
6. **Synonym match** — scientific term equivalences
7. **LLM verifier** — Claude judges semantic correctness (for eval_mode=llm_verifier)

Unicode normalization: minus signs (U+2212), superscript exponents (10⁻²⁶ → e-26).

```bash
# Re-grade with LLM
python skills/devtu-benchmark-harness/scripts/grade_answers.py \
  --results results.json --output graded.json --llm
```

## Plugin Architecture

The ToolUniverse plugin uses **router-only** skill matching:

```
1 auto-matchable skill: "tooluniverse" (router, ~300 chars)
  └── Routing table → 113 sub-skills (all disable-model-invocation: true)
```

Why: Claude Code has a character budget for skill descriptions (~1% of context). 114 skills × 500 chars = 57K exceeds budget → descriptions get dropped. With 1 router, the agent always sees it and routes correctly.

In `-p` mode, skills don't auto-match. The benchmark runner simulates interactive behavior via `full_skill_injection` mode: programmatically detects matching skill, injects its full SKILL.md content.

## Integration with devtu-self-evolve

Insert as **Phase 3.5** between Testing and Fix:
```
Phase 3 (Test) → Phase 3.5 (Benchmark) → Phase 4 (Fix via devtu) → Phase 5 (Retest)
```

## Known Failure Patterns

The `--diagnose` flag references these patterns:

| Pattern | Root cause | Fix action |
|---------|-----------|------------|
| DESeq2 wrong_answer | pydeseq2 vs R disagreement, wrong set operations | `devtu-optimize-skills` on rnaseq-deseq2 |
| ANOVA wrong_answer | F-stat vs p-value confusion, wrong aggregation | `devtu-optimize-skills` on statistical-modeling |
| spline wrong_answer | R ns() ≠ Python patsy; endpoint inclusion varies | `devtu-optimize-skills` on statistical-modeling |
| phylogenetics wrong_answer | PhyKIT output column selection, file pairing | `devtu-fix-tool` on phykit_batch_analysis |
| variant wrong_answer | Multi-row Excel headers, coding-variant denominator | `devtu-optimize-skills` on variant-analysis |
| enrichGO wrong_answer | R clusterProfiler version sensitivity | `devtu-fix-tool` on run_deseq2_analysis |
| timeout | Pipeline >30 min (Trimmomatic, GATK) | `devtu-create-tool` to wrap pipeline |
| GT issue | Ground truth unreproducible with current tools | Document in results, exclude from score |

### Skill convention rules

When adding conventions to skills from benchmark findings:
- **General knowledge only** — no dataset-specific values, no memorized answers
- **Principles over examples** — "per-gene ANOVA not per-sample" rather than "F=0.77 on this dataset"
- **Tool preferences** — "use R DESeq2 for dispersion" rather than "R gives 4, pydeseq2 gives 2"
- **Verify no contamination** — grep for dataset names, specific numeric answers in the convention text
