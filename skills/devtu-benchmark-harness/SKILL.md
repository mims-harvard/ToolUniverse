---
name: devtu-benchmark-harness
description: Run benchmarks to measure ToolUniverse plugin performance on lab-bench (bio MCQ), BixBench (computational bioinformatics), and custom research questions. Produces structured reports with per-category accuracy, failure analysis, and improvement recommendations. Use after skill optimization, tool additions, or as regression check. Integrates with devtu-self-evolve Phase 3.5.
---

# Benchmark Harness for ToolUniverse Plugin

Measure plugin performance, identify failures, and feed results back into the self-evolve cycle.

## When to Use

- After adding or fixing tools — verify no regression
- After optimizing skills — quantify improvement
- As Phase 3.5 of devtu-self-evolve — systematic quality gate
- When comparing plugin vs baseline performance

## Workflow

### Phase 1: Select Benchmark

| Benchmark | Questions | Tests | Data |
|-----------|----------|-------|------|
| lab-bench | 20 MCQ | Database lookup accuracy | `skills/evals/lab-bench/questions.json` |
| bixbench | 61 computational | Data analysis + statistics | `skills/evals/bixbench/questions.json` + capsule data |
| custom | User-defined | Research synthesis quality | Custom JSON file |

### Phase 2: Run Evaluation

```bash
python skills/devtu-benchmark-harness/scripts/run_eval.py \
  --benchmark lab-bench \
  --mode comparison \
  --n 20 \
  --timeout 300 \
  --max-turns 20
```

Options:
- `--mode plugin-only|baseline-only|comparison` — what to run
- `--category DESeq2` — filter BixBench by category
- `--guidance path/to/guidance.md` — custom guidance to inject
- `--resume results.json` — skip already-answered questions

### Phase 3: Grade Results

```bash
python skills/devtu-benchmark-harness/scripts/grade_answers.py \
  --results results.json \
  --output graded.json
```

Grading strategies (applied in order):
1. **Exact match** — ground truth substring in answer
2. **MC match** — letter answer detection (A/B/C/D)
3. **Range match** — numeric value within (low, high) range
4. **Normalized match** — strip punctuation/spaces, compare
5. **Numeric proximity** — within 5% tolerance
6. **LLM verifier** — for complex answers, asks Claude to grade

### Phase 4: Analyze

```bash
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results graded.json
```

Produces:
- Per-category accuracy breakdown
- Failure classification (timeout / error / wrong answer / grading issue)
- Per-question delta (plugin vs baseline)
- Error taxonomy (reuses devtu-fix-tool's 10 categories)

### Phase 5: Report

```bash
python skills/devtu-benchmark-harness/scripts/generate_report.py \
  --results graded.json \
  --output BENCHMARK_REPORT.md
```

## Integration with devtu-self-evolve

Insert as **Phase 3.5** between Testing and Fix:

```
Phase 3 (Testing) → Phase 3.5 (Benchmark) → Phase 4 (Fix)
```

If any category regresses vs previous round, prioritize fixing that skill/tool in Phase 4.

## Interpreting Results

Use devtu-optimize-skills usefulness rubric for research questions:
- **7-9**: Actionable answer with real data and interpretation
- **4-6**: Data returned but not synthesized
- **1-3**: Error, timeout, or hallucinated answer

Use devtu-fix-tool error classification for failures:
- API key missing → document in sources_failed, not a bug
- Schema validation → fix tool JSON config
- Endpoint changed → fix tool Python code
- Transient failure → retry, don't fix

## Current Baselines

| Benchmark | Knowledge-only | Baseline (Bash) | Plugin Best |
|-----------|---------------|-----------------|-------------|
| lab-bench | 6/20 (30%) | 10-13/20 (50-65%) | 17/20 (85%) |
| bixbench | — | — | 8-12/21 (38-57%) |

### Lab-bench progression: 55% → 65% → 75% → 85%
Key improvements: core rules (always answer, fail-fast), MSigDB tool, 300s timeout.

### BixBench hard limits
7/21 questions are unfixable (bix-10 methodology mismatch, bix-1 R dependency).
Remaining 14 score 8-12 depending on stochastic model behavior. Phylogenetics: 100%.
