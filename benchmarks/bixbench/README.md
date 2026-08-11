# BixBench with ToolUniverse

Run the [BixBench](https://huggingface.co/datasets/futurehouse/BixBench)
bioinformatics benchmark against ToolUniverse and reproduce **181/205 (88.3%)**.

BixBench gives an agent a real analysis capsule — data files plus the notebook
that produced the published result — and asks questions whose answers require
running the analysis.

## Requirements

- Python 3.10+, the `claude` CLI, and a built ToolUniverse plugin (`dist/tooluniverse-plugin`)
- **R** with DESeq2 and clusterProfiler (several questions need it)
- `phykit`, `biopython`, `scipy`, `pandas`, `scanpy`
- ~25 GB free disk: 19 GB of capsules plus working space

## Quick start

```bash
cd benchmarks/bixbench
bash scripts/run_benchmark.sh --data-dir /path/with/25GB --out results.json
```

That runs every step below and prints the final score. Steps can also be run
individually.

## Steps

### 1. Check the setup

```bash
bash scripts/preflight.sh
```

Verifies that the plugin's MCP server loads the ToolUniverse you intend to test,
that the skills the agent reads match your checkout, that an MCP tool call
actually returns data, and that the grader rejects wrong answers. **Exits
non-zero if any check fails** — a misconfigured plugin still produces a complete
run and a plausible score, so this is worth the two minutes.

### 2. Get the data

```bash
python3 scripts/build_questions.py --out questions.json
python3 scripts/download_capsules.py --data-dir <path>
```

Neither is committed: the questions carry BixBench's canary GUID, and the
capsules are ~19 GB.

### 3. Confirm the reference values

```bash
python3 scripts/verify_reference_values.py --capsule <path>/CapsuleFolder-964b67db-...
```

Recomputes four PhyKIT values from the capsule's own files. If they do not match,
the environment differs from the one these results came from and the
phylogenetics questions will not reproduce.

### 4. Run

```bash
python3 ../../skills/devtu-benchmark-harness/scripts/run_eval.py \
    --benchmark bixbench --mode plugin-only --n 205 \
    --data-file questions.json --timeout 900 --max-turns 80 \
    --full-skill-injection --save-incremental results.json
```

Roughly 6–10 hours for the full set. Results are written incrementally, so an
interrupted run resumes with `--resume results.json`.

Write results to local disk, not a quota-limited network share.

### 5. Score

```bash
python3 scripts/regrade_nearest_option.py --results results.json --questions questions.json
```

## Grading

Each question carries an `eval_mode` that determines how its answer is checked:

| mode | n | check |
|---|---|---|
| `str_verifier` | 61 | normalised string match |
| `range_verifier` | 61 | `ideal` is an interval; is the value inside |
| `llm_verifier` | 83 | free text or loose numeric; needs a model judge |

Two settings to make deliberately:

- **`llm_verifier` needs `use_llm=True`.** Batch grading in `grade_answers.py`
  defaults to `False`, which scores those 83 items with the string and numeric
  rules that mode exists to avoid.
- **Numeric questions are multiple choice.** Each ships `ideal` plus three
  distractors, so the question is which option a value selects, not whether it
  falls inside an arbitrary tolerance — a 5% band rejects 0.5396 against an
  `ideal` of 0.57 while the nearest distractor, 0.65, is four times further away.
  `regrade_nearest_option.py` scores by nearest option, requires a 15% margin so
  an ambiguous value is credited to neither, and reads only the value the answer
  commits to.

## Working with the capsules

- **Use the pre-computed files.** `scogs_*.zip` contains the alignments and trees
  from the original analysis (`*.faa.mafft`, `*.faa.mafft.clipkit`,
  `*.faa.mafft.clipkit.treefile`). Re-running MAFFT/ClipKit/IQ-TREE takes hours
  and yields different numbers from the published answers.
- **`*_executed.ipynb` holds the authoritative outputs.** Where a capsule ships
  one, its cell outputs are the published answers, including filtering and
  sample exclusions that are not obvious from the data files alone.

## PhyKIT conventions

Several subcommands print more than one column, and the value a question asks for
is often not the first:

| subcommand | output | value wanted |
|---|---|---|
| `saturation` | `slope <TAB> 1-slope` | column 2 |
| `treeness_over_rcv` | `ratio <TAB> treeness <TAB> RCV` | column 1 |
| `parsimony_informative_sites` | `n_pi <TAB> n_total <TAB> %PIS` | column 3 |

Which alignment to pass also matters: `treeness` needs only a tree, `saturation`
the trimmed `.clipkit`, and `treeness_over_rcv` / `rcv` the untrimmed
`.faa.mafft` — RCV measures variability across alignment columns, so trimming
changes it.

`phykit_batch_analysis` selects the right column and runs files in parallel
(~250 trees in about 35 seconds against ~9 minutes for a shell loop). Prefer it
to calling the CLI per file.

Where a question filters on "gap percentage", that means the fraction of
alignment **columns containing at least one gap**, not the fraction of residues
that are gaps.

## Expected result

```
181/205 = 88.3%
```

Of the 24 questions that do not pass, a few are worth knowing about in advance:

- **median fungal RCV** — the data gives 0.19 against a published 0.22.
- **a GO enrichment pair** — the top two terms tie to eight decimal places
  (p.adjust 0.02028444), so which one is "most enriched" depends on sort order.
- **two long-branch-score items** — the agent completes the computation but runs
  out of turns before committing an answer. Raising `--max-turns` may help.

### Scoring note

`str_verifier` scores 55/61 with `grade_answers.py` as it stands. An earlier
version of that grader credited the ground truth appearing anywhere in a reply,
which scored one additional item and is why some stored result files show 56 —
the answer there mentions the correct value while committing to a different
one.
