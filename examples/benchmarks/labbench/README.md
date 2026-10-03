# LAB-Bench ablation: what ToolUniverse adds to an agent

Reproduces the evaluation described in
[Adding ToolUniverse Improves Agent Performance on Biology Tasks](https://aiscientist.tools/posts/labbench-benchmark).

[LAB-Bench](https://arxiv.org/abs/2407.10362) is a benchmark of language model
capabilities for biology research. This uses two of its subtasks: **DbQA**, whose
questions require retrieving information from biological databases, and **SeqQA**, whose
questions require analyzing DNA and protein sequences.

## What is being measured

ToolUniverse is a platform, not an agent and not a model, so it has no standalone
accuracy. What can be measured is the improvement it produces in an existing agent. Each
agent is therefore run twice on identical questions, with the same base model, the same
prompts and the same code execution, and with the presence of ToolUniverse as the only
difference between the two runs. That difference is the measurement.

This matters because a comparison against another biomedical agent confounds two things:
the tools it has and the base model underneath it. Holding the model fixed and toggling
only ToolUniverse separates them.

Biomni's published accuracies (74.4% on DbQA, 81.9% on SeqQA) are on these exact items,
which makes it a same-item reference point rather than a re-implementation. It runs on
its own base model, so the gap against it still contains a model-generation difference;
the with/without ablation is the number that isolates the platform.

## Requirements

- An agent CLI: [Claude Code](https://claude.com/claude-code) or Codex.
- `pip install pandas numpy pyarrow` to build the question set.
- API keys for the tools you want available. Missing keys do not corrupt the run; the
  affected tools report an error instead of returning something wrong. They do lower the
  with-condition, so a run with few keys measures less of ToolUniverse than the published
  one did.

For the with-condition, ToolUniverse has to be attached to the agent.

**Claude Code** takes a built plugin directory. Build it from the repository root:

```bash
bash scripts/build-plugin.sh          # writes dist/tooluniverse-plugin
export TOOLUNIVERSE_PLUGIN_DIR="$PWD/dist/tooluniverse-plugin"
```

**Codex** takes an MCP server entry; copy `codex_config/with_tooluniverse.toml`, set the
`PYTHONPATH` and command to the checkout you intend to measure, and keep
`baseline.toml` identical except for the absent server.

The base models used in the published run are Opus 4.8 for Claude Code and GPT-5.5 for
Codex. Any other model measures a different system, which is legitimate but is not a
reproduction of these numbers.

## The questions are not committed here

LAB-Bench rows carry the benchmark's canary string, which exists so that the questions
can be detected in future training data. Redistributing them would defeat that. Download
Biomni's `benchmark.zip` as documented at
[snap-stanford/Biomni](https://github.com/snap-stanford/Biomni), unpack it, and build the
items locally:

```bash
python build_dataset.py --bench-dir /path/to/biomni_benchmark --out-dir data
# data/dbqa.jsonl  (60 items)
# data/seqqa.jsonl (70 items)
```

`build_dataset.py` reproduces Biomni's option shuffle exactly, seeding NumPy once with
42 and shuffling each row in parquet order. Seeding per row instead would give the
correct answer a different letter on every question, and the comparison would no longer
be same-presentation.

## Run it

Check the with-condition first. This step is not optional:

```bash
python preflight.py --agent claude --plugin-dir /path/to/tooluniverse-plugin
```

If the MCP server has not finished loading the tool catalogue when the CLI gives up
waiting, the agent runs anyway with no ToolUniverse tools attached, answers every
question, and produces a complete with-ToolUniverse result that measures the bare model.
Nothing in the output looks wrong. `preflight.py` makes a live tool call with a known
answer, which is the only reliable way to tell the difference. Asking the agent whether
it can call the tool is not: it answers from priors in a couple of seconds and is
confident either way.

Then run the ablation:

```bash
python run_ablation.py --items data/dbqa.jsonl --agent claude \
    --plugin-dir /path/to/tooluniverse-plugin --reps 3 --out results/dbqa_claude.json

python run_ablation.py --items data/seqqa.jsonl --agent codex --reps 3 \
    --codex-with codex_config/with_tooluniverse.toml \
    --codex-without codex_config/baseline.toml \
    --out results/seqqa_codex.json

python aggregate.py results/*.json
```

Use `--limit 5 --reps 1` for a smoke test before committing to a full run.

## Grading

Answers are parsed from `[ANSWER]X[/ANSWER]` and compared by letter, so grading is exact
and involves no model. Anything unparseable counts as incorrect. So does a refusal:
Opus 4.8 declines a small number of questions on safety grounds, in both conditions, and
scoring those as wrong makes the reported accuracy a lower bound rather than a number
that quietly drops its hardest cases.

## Expected results

`reference_results.json` holds the published numbers, and `aggregate.py` prints them
beside yours. Agent runs are not deterministic, so a faithful reproduction lands near
these rather than exactly on them.

| Subtask | Agent | without | with | difference |
|---|---|---|---|---|
| DbQA (60) | Claude Code, Opus 4.8 | 56.7 | 78.3 | +21.6 |
| DbQA (60) | Codex, GPT-5.5 | 81.1 | 92.8 | +11.7 |
| SeqQA (70) | Claude Code, Opus 4.8 | 94.3 | 99.5 | +5.2 |
| SeqQA (70) | Codex, GPT-5.5 | 91.4 | 96.2 | +4.8 |

The improvement appears in two agents built on unrelated model families, which is the
reason to read it as a contribution of the platform rather than a property of one model.

## If your numbers come out wrong

Check, in this order:

1. **Does the with-condition actually have the tools?** Re-run `preflight.py`. This is
   the most common cause by a wide margin, and it is invisible in the results file.
2. **Are both conditions otherwise identical?** Same model, same turn limit, same code
   execution. A baseline that has lost code execution is not the baseline.
3. **Is the option shuffle right?** If `build_dataset.py` was modified, the gold letter
   may no longer match the item.
4. **Are the tools failing on missing credentials?** Inspect `response_tail` in the
   results file; repeated tool errors depress the with-condition without any obvious
   sign in the accuracy alone.
