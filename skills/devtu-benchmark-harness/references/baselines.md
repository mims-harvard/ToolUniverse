# Benchmark Baselines

Current scores and progression tracking. Updated after each benchmark run.

## BixBench (205 questions, v1.5)

| Date | Score | Notes |
|------|-------|-------|
| Apr 14 | 37/61 (60.7%) | Baseline on 61q subset |
| Apr 17 | 51/61 (83.6%) | Skill conventions |
| Apr 18 | 180/205 (87.8%) | Full 205q + grader + tools |
| Apr 21 | 183/205 (89.3%) | Spline endpoint + saturation fix |

### Remaining 22 failures (Apr 21)

- 10 GT issues (ground truth unreproducible)
- 6 agent computation diffs
- 3 timeouts
- 2 pipeline-dependent
- 1 ambiguous

### By skill (Apr 21)

| Skill | Accuracy |
|-------|----------|
| tooluniverse-gene-enrichment | 81% |
| tooluniverse-statistical-modeling | ~85% |
| tooluniverse-rnaseq-deseq2 | ~80% |
| tooluniverse-phylogenetics | ~85% |
| tooluniverse-variant-analysis | ~80% |

## Lab-bench (20 MCQ)

| Date | Score | Notes |
|------|-------|-------|
| Apr 14 | 17/20 (85%) | With plugin |

## Notes

- Scores include LLM grading for eval_mode=llm_verifier questions
- Unicode normalization (minus signs, superscript exponents) applied
- GT issues verified by running authoritative scripts from capsule data
