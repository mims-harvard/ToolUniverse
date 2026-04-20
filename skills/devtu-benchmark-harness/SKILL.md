---
name: devtu-benchmark-harness
description: Run benchmarks to measure ToolUniverse plugin performance on lab-bench (bio MCQ), BixBench (computational bioinformatics), and custom research questions. Produces structured reports with per-category accuracy, failure-to-skill mapping, and improvement recommendations. Use after skill optimization, tool additions, or as regression check. Integrates with devtu-self-evolve Phase 3.5.
---

# Benchmark Harness for ToolUniverse Plugin

Measure plugin performance, diagnose failures, map them to specific skills/tools, and generate targeted improvement recommendations.

## The Feedback Loop

```
1. RUN benchmark → 2. ANALYZE results → 3. DIAGNOSE failures → 4. FIX skill/tool → 5. RETEST failures → repeat
```

This is NOT a one-shot eval. The harness exists to continuously improve the system by identifying exactly which skill or tool is responsible for each failure.

## Quick Start: Full Cycle

```bash
# 1. Rebuild plugin dist with latest skills
bash scripts/build-plugin.sh

# 2. Run benchmark (BixBench, all 61 questions, plugin-only)
python skills/devtu-benchmark-harness/scripts/run_eval.py \
  --benchmark bixbench --mode plugin-only --n 61 --timeout 600

# 3. Analyze + diagnose
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results skills/evals/bixbench/results_XXXXXXXX_XXXXXX.json \
  --benchmark bixbench --diagnose

# 4. Extract failed question IDs for retesting
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results skills/evals/bixbench/results_XXXXXXXX_XXXXXX.json \
  --extract-failures /tmp/failures.json

# 5. After fixing the skill/tool, retest ONLY the failures
python skills/devtu-benchmark-harness/scripts/run_eval.py \
  --benchmark bixbench --mode plugin-only \
  --retest /tmp/failures.json --timeout 600
```

## Benchmarks

| Benchmark | Questions | Tests | Data |
|-----------|----------|-------|------|
| lab-bench | 20 MCQ | Database lookup accuracy | `skills/evals/lab-bench/questions.json` |
| bixbench | 205 computational | Data analysis + statistics | `skills/evals/bixbench/questions.json` + capsule data |
| custom | User-defined | Research synthesis quality | Custom JSON file |

### BixBench setup
```bash
# 1. Install R packages (DESeq2, clusterProfiler, org.Hs.eg.db, etc.)
Rscript skills/evals/install_r_packages.R

# 2. Download capsule data (~5 GB) — only needed once
python3 skills/evals/bixbench/download_capsules.py
```

## Scripts

### `run_eval.py` — Run evaluation

```bash
python skills/devtu-benchmark-harness/scripts/run_eval.py \
  --benchmark bixbench \
  --mode plugin-only \       # plugin-only | baseline-only | comparison
  --n 61 \                   # number of questions
  --timeout 600 \            # seconds per question
  --max-turns 20 \           # agent turns per question
  --category DESeq2 \        # filter questions by category keyword
  --guidance path/to/x.md \  # custom guidance to inject
  --resume results.json      # skip already-answered questions
```

### `grade_answers.py` — Grade answers

```bash
python skills/devtu-benchmark-harness/scripts/grade_answers.py \
  --results results.json --output graded.json
```

Strategies (applied in order): exact match, MC letter, range (lo,hi), normalized, numeric 5%, LLM verifier.

### `analyze_results.py` — Analyze + diagnose

```bash
# Basic analysis
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json --benchmark bixbench

# With improvement recommendations
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json --benchmark bixbench --diagnose

# Extract failures for retesting
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json --extract-failures failures.json

# JSON output (pipe to jq or other tools)
python skills/devtu-benchmark-harness/scripts/analyze_results.py \
  --results results.json --json --diagnose
```

Output includes:
- **By skill**: Which skills have the lowest accuracy (fix those first)
- **By category**: DESeq2, ANOVA, spline_fitting, phylogenetics, etc.
- **Failure types**: timeout, wrong_answer, tool_error, api_key_missing
- **Recommendations**: For each (category, failure_type) pair, what to fix and where

### `generate_report.py` — Markdown report

```bash
python skills/devtu-benchmark-harness/scripts/generate_report.py \
  --results results.json --output BENCHMARK_REPORT.md
```

## Category → Skill Mapping

The analyzer maps each question category to the skill responsible for handling it:

| Category | Skill | Notes |
|----------|-------|-------|
| DESeq2 | tooluniverse-rnaseq-deseq2 | Differential expression |
| DESeq2+enrichGO | tooluniverse-gene-enrichment | GO enrichment after DEG |
| ANOVA | tooluniverse-statistical-modeling | F-test, group comparison |
| regression | tooluniverse-statistical-modeling | Logistic, ordinal, linear |
| chi_square | tooluniverse-statistical-modeling | Contingency tables |
| spline_fitting | tooluniverse-statistical-modeling | ns(), cubic, polynomial |
| imaging | tooluniverse-statistical-modeling | Cohen's d, NeuN counts |
| data_counting | tooluniverse-statistical-modeling | Percentages, counts |
| fold_change | tooluniverse-rnaseq-deseq2 | log2FC per gene |
| phylogenetics | tooluniverse-phylogenetics | Trees, parsimony sites |
| variant_analysis | tooluniverse-variant-analysis | VCF, VAF, coding variant |
| crispr_screen | tooluniverse-crispr-screen-analysis | MAGeCK, sgRNA |
| single_cell | tooluniverse-single-cell | scanpy, h5ad |
| pathway_enrichment | tooluniverse-gene-enrichment | GSEA, Reactome |

## Current Baselines (2026-04-17)

| Benchmark | Baseline (Bash) | Plugin (Apr 14) | Plugin (Apr 18) | Target |
|-----------|-----------------|-----------------|-----------------|--------|
| lab-bench (20 MCQ) | 50% | 85% | 85% | 90% |
| bixbench (205 comp) | ~50% | 60.7% (37/61) | **87.8% (180/205)** | 85% ✅ |

### BixBench by skill (Apr 18, full 205q, decontaminated skills):
| Skill | Questions | Accuracy |
|-------|-----------|----------|
| tooluniverse-single-cell | 3 | 67% |
| tooluniverse-crispr-screen-analysis | 3 | 67% |
| tooluniverse-variant-analysis | 27 | 74% |
| tooluniverse-rnaseq-deseq2 | 59 | 78% |
| tooluniverse-phylogenetics | 51 | 80% |
| tooluniverse-statistical-modeling | 46 | 80% |
| tooluniverse-gene-enrichment | 16 | 81% |

### Failure breakdown (44/205):
- 40 wrong answers, 4 timeouts
- Weakest categories: spline_fitting (57%), epigenomics (60%), single_cell/functional_genomics (67%)

## Step 4: FIX — Route to the Right devtu Skill

After `--diagnose` identifies the failing skill and failure type, invoke the appropriate devtu skill to fix it. **Do not fix manually** — use the devtu skills so fixes follow established patterns and include tests.

### Fix routing table

| Diagnosis | What to do | Invoke |
|-----------|-----------|--------|
| Tool returns wrong data (schema, endpoint, params) | Fix tool Python code + JSON config | `Skill('devtu-fix-tool')` with the tool name and error |
| No tool exists for this computation | Create a new ToolUniverse tool | `Skill('devtu-create-tool')` with the API/computation spec |
| Skill gives wrong guidance (wrong convention) | Update SKILL.md BixBench conventions | `Skill('devtu-optimize-skills')` with the skill name + failure details |
| Agent doesn't follow skill guidance | Strengthen wording, add code examples, add bundled script | `Skill('devtu-optimize-skills')` Pattern 15 (computational procedures) |
| Grader false negative (correct answer marked wrong) | Fix grader in `grade_answers.py` | Direct code fix (no devtu skill needed) |
| Multiple skills/tools need coordinated changes | Full self-evolve cycle | `Skill('devtu-self-evolve')` |

### Fix workflow

```
1. Run: python analyze_results.py --results X.json --questions questions.json --diagnose
2. For each recommendation:
   a. Identify fix type from the routing table above
   b. Invoke the appropriate devtu skill:
      - Skill('devtu-fix-tool') — pass tool name + error message
      - Skill('devtu-create-tool') — pass computation description
      - Skill('devtu-optimize-skills') — pass skill name + failing question details
   c. The devtu skill handles: diagnosis, implementation, testing, validation
3. Rebuild dist: bash scripts/build-plugin.sh
4. Retest: python run_eval.py --retest failures.json
```

### Example fix flow

```
Diagnosis: "bix-36-q1 ANOVA wrong_answer → tooluniverse-statistical-modeling"
  → Invoke: Skill('devtu-optimize-skills')
  → Tell it: "The statistical-modeling skill's ANOVA guidance produces wrong F-statistics
     for per-gene expression ANOVA. The agent aggregates at sample level instead of gene
     level. Add a BixBench convention with the correct aggregation pattern."
  → The skill handles: read current SKILL.md, identify gap, add convention, verify no
     memorization, rebuild dist, suggest retest.

Diagnosis: "bix-4-q1 timeout → tooluniverse-phylogenetics, needs PhyKIT DVMC"
  → Invoke: Skill('devtu-create-tool')
  → Tell it: "Create a ToolUniverse tool wrapping PhyKIT's DVMC function for batch
     processing on directories of tree files."
  → The skill handles: tool class, JSON config, register, test, validate.
```

## Integration with devtu-self-evolve

Insert as **Phase 3.5** between Testing and Fix:
```
Phase 3 (Testing) → Phase 3.5 (Benchmark) → Phase 4 (Fix via devtu skills) → Phase 5 (Retest)
```
If any category regresses vs previous round, prioritize fixing that skill/tool in Phase 4 using the routing table above.

## Known Failure Patterns

These patterns were identified from benchmark debugging. The `--diagnose` flag references them:

- **DESeq2 wrong_answer**: pydeseq2 vs R DESeq2 disagreement, wrong strain mapping, inclusive vs exclusive set ops → `devtu-optimize-skills` on rnaseq-deseq2 or `devtu-create-tool` for R DESeq2 tool
- **ANOVA wrong_answer**: F-statistic vs p-value confusion, wrong grouping variable → `devtu-optimize-skills` on statistical-modeling
- **spline_fitting wrong_answer**: Python patsy.cr() ≠ R ns(); endpoint inclusion depends on model type → `devtu-optimize-skills` on statistical-modeling
- **regression timeout**: Agent loops trying different model specs → `devtu-optimize-skills` (add "commit to first approach" rule)
- **variant_analysis wrong_answer**: Multi-row Excel headers, coding vs all denominator → `devtu-optimize-skills` on variant-analysis
- **fold_change wrong_answer**: Wrong contrast direction, gene symbol mapping → `devtu-optimize-skills` on rnaseq-deseq2
- **phylogenetics wrong_answer**: PhyKIT batch computation errors → `devtu-fix-tool` on phykit_batch_analysis or `devtu-optimize-skills` on phylogenetics
- **enrichGO wrong_answer**: R clusterProfiler version sensitivity → `devtu-fix-tool` on run_deseq2_analysis enrichgo operation
