# Tool Finder retrieval benchmark

Reproduces the retrieval evaluation described in
[Benchmarking the Tool Finder](https://aiscientist.tools/posts/tool-finder-benchmark).

The question is narrow and mechanical: given a natural-language request from a
scientist, does the Tool Finder return the tool that answers it? Everything here
measures retrieval only. It says nothing about whether an agent then uses the tool well.

## What is being compared

Every strategy runs against the same tool catalogue, the same queries and the same
judgments. The comparisons that matter:

| Strategy | What it isolates |
|---|---|
| `toolrag` vs `base` | The same 1.5B encoder with and without fine-tuning. Nothing else differs, so the gap is the contribution of fine-tuning. |
| `keyword`, `llm` | Non-embedding search strategies shipped with ToolUniverse. |
| `openai-3-large`, `openai-3-small`, `gte-qwen2-7b`, `e5-mistral-7b` | Alternative encoders, selectable at call time through the `embedding_model` parameter. |
| `gte-large`, `s-pubmedbert` | Off-the-shelf encoders that are not built in, as external reference points. `s-pubmedbert` is a biomedical model, included because domain pretraining is the obvious alternative hypothesis to fine-tuning on tool descriptions. |

The four alternative encoders are not private research code. They are the values the
shipped tool accepts:

```python
tu.run({"name": "Tool_Finder",
        "arguments": {"description": "predict the 3D structure of a protein sequence",
                      "embedding_model": "openai-3-large"}})
```

so any number this benchmark reports for them is reachable from an ordinary call.

## Install

```bash
pip install tooluniverse sentence-transformers openai numpy
```

Credentials come from the environment, never from a file in this directory:

```bash
export OPENAI_API_KEY=...                 # public OpenAI
# or, for Azure OpenAI:
export AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
export AZURE_OPENAI_API_KEY=...
```

A GPU is strongly recommended. Measured end-to-end on a single A100-80GB, over 12,171
queries plus any documents not already cached:

| Strategy | Wall clock |
|---|---|
| `toolrag`, `base` (1.5B) | ~2 min |
| `gte-large` (434M), `s-pubmedbert` (109M) | ~3 min |
| `openai-3-large` / `-small` (hosted) | ~6 min |
| `gte-qwen2-7b`, `e5-mistral-7b` | 22-28 min, and roughly 20 GB of GPU memory |
| `keyword` | ~36 min, since it is per-query rather than batched |

Document embeddings are cached to disk, so a second run of the same encoder against the
same catalogue only re-encodes the queries.

## Pin the catalogue first, or the released judgments will not fit

The released judgments were produced against ToolUniverse at commit
[`e2520a96`](https://github.com/mims-harvard/ToolUniverse/commit/e2520a9610c9b8a54aed42837929cca7f4659590),
when the pool held 2,634 tools. The catalogue is not static. Measured against a recent
`main`, 21 tools have been added and, more importantly, **600 of the 2,634 existing tools
have had their description or schema edited**, which changes the document text those
tools are indexed by.

This matters because the judgments are pooled. A tool that no strategy retrieved back
then was never judged, so if your run surfaces it now, it scores as irrelevant whether or
not it is. Re-scoring the released judgments against a newer catalogue therefore reports
numbers that are quietly too low.

Two honest options:

```bash
# Option A -- reproduce the published run: pin the catalogue to the judged commit.
git -C /path/to/ToolUniverse checkout e2520a9610c9b8a54aed42837929cca7f4659590
export TOOLUNIVERSE_REPO=/path/to/ToolUniverse
export PYTHONPATH=/path/to/ToolUniverse/src     # see below: the checkout must be the
                                                # package that actually gets imported
unset DISGENET_API_KEY OMIM_API_KEY             # see below: these change the pool

# Option B -- measure today's catalogue: judge the new candidates before scoring.
# Costs API calls, but keeps the pool complete.
BENCH_JUDGE_INCREMENTAL=1 python build_qrels.py
```

Option A reproduces the published figures. Option B produces valid current numbers that
are not directly comparable to them.

### Two things besides the commit decide what is in the pool

**The checkout has to be the package that gets imported.** `TOOLUNIVERSE_REPO` tells the
scripts where to read git history and tool files from, but `import tooluniverse` obeys
`sys.path`, so without the `PYTHONPATH` above (or `pip install -e` on that checkout) the
catalogue comes from whatever version is installed in your environment. `build_corpus.py`
now prints the directory it actually loaded and refuses to continue when the two disagree,
because the failure is otherwise invisible: the run completes and reports numbers for a
pool the judgments never covered.

**Some tools only exist if you hold their API key.** DisGeNET and OMIM tools load only
when `DISGENET_API_KEY` / `OMIM_API_KEY` are set. The published run held neither, so its
pool was 2,634 tools; with both keys it is 2,643. Those nine extra tools were never
pooled and therefore score 0 no matter how relevant they are, which pushes every strategy
down. `build_corpus.py` warns when the pool size does not match the judged one.

With both conditions met, `build_corpus.py` reproduces the published snapshot exactly:
pool 2,634, 2,615 seed tools, 2,233 held-out tools, and byte-identical document text for
all 2,634 tools.

## Quick path: re-score the released data

Generating queries and judging them costs API calls. To skip both and go straight to
the metrics:

```bash
python download_data.py     # queries + graded judgments into ./data
python build_corpus.py      # snapshot of the catalogue you pinned above
python run_systems.py toolrag base
python compute_metrics.py
```

## Full path: rebuild everything

```bash
python build_corpus.py                                        # 1. catalogue snapshot
BENCH_N_SEEDS=0 BENCH_EXAMPLES_PER_TOOL=0 python generate_queries.py   # 2. queries
python run_systems.py                                         # 3. rankings
python build_qrels.py                                         # 4. graded judgments
python compute_metrics.py                                     # 5. metrics
```

Step 4 must follow step 3: the judgment pool is defined as the union of what the
strategies retrieved.

## How the evaluation is built

**Queries come in three difficulty levels.** Each seed tool and each of its distinct
test examples produces a triple: an L1 query that names the resource, an L2 query that
describes the intent without naming it, and an L3 query that buries the need in a
paraphrased research scenario. The three share an underlying need, which makes the
comparison across levels paired rather than a comparison of three unrelated samples.
L3 is the case that matters in practice, because an autonomous agent does not know the
name of the tool it needs.

**Judgments are pooled, multi-positive and graded.** ToolUniverse contains
interchangeable tools, so crediting only the tool a query was generated from would mark
a correct answer wrong for being the wrong synonym. Instead, following standard TREC
practice, the pool for a query is everything any strategy retrieved plus the seed tool,
and a judge grades each candidate 2 (directly answers), 1 (partially relevant, or the
same operation on a different resource) or 0. The judge is blind: it does not know which
strategy retrieved a candidate or which tool the query came from.

**The held-out split addresses memorization.** The fine-tuned encoder was trained on an
earlier, much smaller catalogue. `build_corpus.py` reads the git date at which each tool
file entered the repository and flags everything added after the fine-tuning cutoff.
`compute_metrics.py` reports the ablation separately on that split, where the fine-tuned
encoder cannot be retrieving anything it memorized. In the published run, **99% of the
judged queries (5,937 of 6,000)** targeted post-cutoff tools. Across all 13,101 generated
queries the figure is 90.7%; the two differ because judging ran on a subsample, described
below.

**Judging ran on a stratified subsample.** Pooled judging is the expensive step, so the
published run judged 6,000 queries -- exactly 2,000 per difficulty level, covering 1,454
distinct source tools -- at an average of 56.6 candidates judged per query, which is
where the 339,771 released judgments come from. `build_qrels.py` reproduces that design
by default (`BENCH_JUDGE_SUBSAMPLE=6000`); set it to 0 to judge every pooled query, which
roughly doubles both the cost and the size of the judged set.

**Two filters run over generated queries**, flagging rather than deleting: degenerate
queries (too short, or an L2/L3 query that named the tool anyway) and the top 5%
lexical-overlap tail against the tool description, which would otherwise reward string
matching over retrieval.

## Metrics

Recall@1/5/10, MRR and NDCG@10, each with a 95% bootstrap confidence interval over
queries. The difficulty breakdown is reported twice: `by_difficulty.csv` scores every
query at each level, and `by_difficulty_paired.csv` restricts to (tool, example) triples
that have a positive at all three levels, so L1, L2 and L3 score the same underlying
needs and the drop across levels is a property of the phrasing rather than of the sample.
The published difficulty figure is the paired table. NDCG@10 is the headline because it is the only one that uses the graded labels,
crediting a directly relevant tool more than a partially relevant one. The fine-tuning
ablation is tested with a paired bootstrap, which respects the fact that both strategies
answer identical queries.

## What reproduces exactly, and what does not

| Path | Reproducibility |
|---|---|
| Re-scoring the released queries and judgments, catalogue pinned to `e2520a96` | Deterministic. The encoders are fixed checkpoints and scoring is arithmetic, so you land on the published figures. Measured against the published run on an H100: identical top-10 sets on 12,171 of 12,171 queries for `toolrag` and 12,170 of 12,171 for `base`, with a handful of tied pairs ordered differently, and every metric equal to four decimal places. |
| Re-scoring against a newer catalogue | Systematically low, for the pooling reason above. |
| Regenerating queries (`generate_queries.py`) | **Not** reproducible item for item. Generation runs at temperature 0.3, so you get a different, equally valid query set and therefore different absolute numbers. |
| Re-judging (`build_qrels.py`) | Also not identical: the judge is a sampled model. Grades move on borderline candidates. |

So the full pipeline reproduces the *protocol* and the *conclusions*, not the third
decimal place. If you rebuild the data end to end, expect the ranking of strategies and
the size of the fine-tuning gap to hold, while individual metric values shift by a point
or two. Only the pinned re-scoring path is expected to land on the published numbers.

## What you should see

The published run is plotted in the
[blog post](https://aiscientist.tools/posts/tool-finder-benchmark); compare your
`results/summary.md` against those figures. The values the post states in its text are
the quickest check that you landed on the published run:

| Quantity | Published |
|---|---|
| Queries scored (`n` in `main_table.csv`) | 5,912 -- the judged 6,000 minus 88 for which the judge graded every pooled candidate 0 |
| NDCG@10, `toolrag` | 0.552 |
| NDCG@10, `base` (same model, no fine-tuning) | 0.127 |
| NDCG@10 on L3 scenario queries: `toolrag` / `keyword` / `base` (`by_difficulty_paired.csv`) | 0.431 / 0.356 / 0.070 |
| The 7B encoders, over `toolrag` | about +0.09 NDCG@10 |

The qualitative findings a correct reproduction should show:

- the fine-tuned encoder beats its identical un-fine-tuned base by a wide margin, and
  the gap survives on the held-out split;
- the un-fine-tuned base collapses on L3 scenario queries;
- keyword search is competitive on L1 named queries and falls off hardest once queries
  stop naming things;
- several larger encoders score somewhat higher than the 1.5B default, which is why they
  are selectable through `embedding_model` rather than argued away.

## One reproducibility trap

`common.st_encode` loads the encoder **without** `trust_remote_code`. This is
deliberate. The deployed Tool Finder loads it the same way, which selects the native
Qwen2 architecture rather than the custom class in the model repository. Passing
`trust_remote_code=True` for the same checkpoint yields different vectors and a
different ranking, so adding it "for compatibility" silently stops reproducing the
shipped behavior. Encoders that genuinely require it are marked `trc=True` in
`run_systems.py`.
