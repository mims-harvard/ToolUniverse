# Benchmark reproductions

Code to reproduce the published ToolUniverse benchmark results. Each folder is
self-contained and has its own README with the exact commands.

| Folder | What it measures | Write-up |
|---|---|---|
| [`tool_finder/`](tool_finder/) | Retrieval: does the Tool Finder return the tool that answers a request? Compares the fine-tuned default encoder against its un-fine-tuned base, the keyword and LLM strategies, and the alternative encoders selectable through `embedding_model`. | [Tool Finder benchmark](https://aiscientist.tools/posts/tool-finder-benchmark) |
| [`labbench/`](labbench/) | End to end: how much does adding ToolUniverse improve an agent's accuracy on LAB-Bench DbQA and SeqQA, with the base model held constant? | [LAB-Bench benchmark](https://aiscientist.tools/posts/labbench-benchmark) |

## What is not committed here

Neither folder ships its evaluation data, for different reasons.

- **LAB-Bench questions** carry the benchmark's canary string, which exists so the
  questions can be detected in training data. `labbench/build_dataset.py` rebuilds them
  from the publicly released archive instead.
- **Tool Finder queries and judgments** are far larger than belongs in a git history, so
  they are published as a release asset. `tool_finder/download_data.py` fetches them, and
  the generation and judging steps regenerate them from scratch if you would rather not
  take them on trust.

Credentials are read from environment variables in both folders. Do not add a key file
to these directories.

## Two things worth knowing before you run either

**Verify by calling, not by asking.** The most expensive failure in this kind of
evaluation is silent: a run that completes, produces plausible numbers, and measured
something other than what you intended, because the tools were never attached or the
code under test was not the code that loaded. `labbench/preflight.py` exists for exactly
this and should be run before every session.

**Know which parts are exact.** The LAB-Bench ablation is never bit-reproducible: agent
runs are sampled, so the numbers land near the published ones rather than on them, and
the with-condition also depends on which tool API keys you hold. The retrieval benchmark
*is* deterministic, but only along one path: re-scoring the released judgments against
the catalogue commit they were judged on. Regenerating its queries or re-judging them
uses sampled models and produces a different, equally valid dataset. Both folders spell
out which of their steps reproduce exactly and which reproduce only in conclusion.

**The catalogue is a moving part, not a constant.** Tool descriptions get edited: 600 of
the 2,634 tools in the judged snapshot have changed text since. `tool_finder/README.md`
explains how to pin it, and why re-scoring old judgments against a new catalogue reports
numbers that are too low.
