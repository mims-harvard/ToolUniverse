"""Step 4 - build pooled, multi-positive, graded relevance judgments.

ToolUniverse contains interchangeable tools: several may answer the same request. A
benchmark that credits only the one tool a query was generated from would therefore
punish a correct answer for being the wrong synonym. This step uses TREC-style pooling
instead. For each query the judgment pool is the union of every strategy's top-10 plus
the tool the query was seeded from, and a judge grades each candidate:

    2 = directly answers the query
    1 = partially relevant, or the same operation on a different resource
    0 = irrelevant

The judge sees only the query and the candidate descriptions. It is not told which
strategy retrieved a candidate, nor which tool the query came from, so it cannot favor
either. Grade-0 rows are written too, which keeps "pooled but judged irrelevant"
distinguishable from "never pooled".

Run this only after run_systems.py, since the pool is defined by the rankings.

Output: data/qrels.tsv (query_id, tool_name, grade)
        data/judge_validation_sample.tsv (for measuring agreement against a human)

Environment:
    BENCH_JUDGE_WORKERS      parallel judging requests (default 8)
    BENCH_JUDGE_SUBSAMPLE    queries to judge, balanced across difficulty levels
                             (default 6000, matching the published run; 0 = all)
    BENCH_JUDGE_INCREMENTAL=1  judge only pairs missing from an existing qrels.tsv

Usage:
    python build_qrels.py
"""

import os
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import common as C

WORKERS = int(os.environ.get("BENCH_JUDGE_WORKERS", "8"))
# Judging is the expensive step. The published run judged a stratified subsample of
# 6,000 queries, 2,000 per difficulty level; set this to 0 to judge every pooled query.
SUBSAMPLE = int(os.environ.get("BENCH_JUDGE_SUBSAMPLE", "6000"))
VALIDATION_SAMPLE = int(os.environ.get("BENCH_JUDGE_VALIDATION", "400"))

JUDGE_PROMPT = """You are grading, for a tool-retrieval benchmark, how well each candidate TOOL answers a user QUERY.

Grade each candidate on this scale:
  2 = directly answers the query (this tool fully serves the user's need)
  1 = partially relevant / related (helps but is not the primary tool, OR performs the same kind of operation on a different database/resource)
  0 = irrelevant

USER QUERY:
{query}

CANDIDATE TOOLS (name -- description):
{candidates}

Judge each candidate ONLY on whether it serves the query. Output STRICT JSON mapping every candidate name to its grade:
{{"grades": {{"<exact_tool_name>": 2, "<exact_tool_name>": 1, ...}}}}
Include EVERY candidate name exactly as given."""


def load_pools():
    corpus = C.load_json(C.DATA_DIR / "corpus_snapshot.json")
    meta = corpus["meta"]
    queries = [
        r
        for r in C.read_jsonl(C.DATA_DIR / "queries.jsonl")
        if not r["dropped_degenerate"] and not r["dropped_for_overlap"]
    ]
    qmap = {r["query_id"]: r for r in queries}

    retrieved = {}
    for fp in sorted(Path(C.RANK_DIR).glob("*.jsonl")):
        for r in C.read_jsonl(fp):
            retrieved.setdefault(r["query_id"], set()).update(r["ranked"][:10])
    if not retrieved:
        raise SystemExit("No rankings found. Run run_systems.py first.")

    pools = {}
    for qid, r in qmap.items():
        pool = set(retrieved.get(qid, set()))
        pool.add(r["source_tool"])
        pools[qid] = sorted(t for t in pool if t in meta)
    return meta, qmap, pools


def judge_one(client, qid, qmap, meta, pool):
    candidates = "\n".join(
        f"- {n} -- {(meta[n]['description'] or '').replace(chr(10), ' ')[:300]}" for n in pool
    )
    raw = C.chat(
        client,
        C.JUDGE_MODEL,
        [{"role": "user", "content": JUDGE_PROMPT.format(query=qmap[qid]["query"], candidates=candidates)}],
        want_json=True,
        max_tokens=4096,
    )
    obj = C.parse_json_lenient(raw) or {}
    grades = obj.get("grades", obj) if isinstance(obj, dict) else {}
    out = {}
    for n in pool:
        try:
            g = int(grades.get(n, 0))
        except Exception:
            g = 0
        out[n] = max(0, min(2, g))
    return qid, out


def load_existing():
    judged = {}
    path = C.DATA_DIR / "qrels.tsv"
    if not path.exists():
        return judged
    with open(path) as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) == 3:
                judged.setdefault(p[0], {})[p[1]] = int(p[2])
    return judged


def write_qrels(judged):
    lines = ["query_id\ttool_name\tgrade"]
    n_relevant = 0
    for qid in sorted(judged):
        for name, grade in sorted(judged[qid].items()):
            lines.append(f"{qid}\t{name}\t{grade}")
            n_relevant += grade >= 1
    (C.DATA_DIR / "qrels.tsv").write_text("\n".join(lines) + "\n")
    C.log(f"Wrote qrels.tsv: {len(lines) - 1} judgments, {n_relevant} relevant (grade >= 1)")


def stratify(qids, qmap, n):
    """Take n query ids, balanced across difficulty levels, deterministically."""
    if n <= 0 or n >= len(qids):
        return qids
    by_level = {}
    for qid in qids:
        by_level.setdefault(qmap[qid]["difficulty"], []).append(qid)
    per = n // len(by_level)
    rng = random.Random(C.SEED)
    out = []
    for level in sorted(by_level):
        bucket = sorted(by_level[level])
        rng.shuffle(bucket)
        out.extend(bucket[:per])
    return out


def main():
    meta, qmap, pools = load_pools()
    selected = stratify(sorted(pools), qmap, SUBSAMPLE)
    if len(selected) < len(pools):
        C.log(f"Judging a stratified subsample: {len(selected)} of {len(pools)} pooled queries "
              f"(set BENCH_JUDGE_SUBSAMPLE=0 to judge all)")
    pools = {q: pools[q] for q in selected}
    incremental = os.environ.get("BENCH_JUDGE_INCREMENTAL") == "1"
    judged = load_existing() if incremental else {}

    todo = {}
    for qid, pool in pools.items():
        missing = [t for t in pool if t not in judged.get(qid, {})]
        if missing:
            todo[qid] = missing
    n_pairs = sum(len(v) for v in todo.values())
    if not n_pairs:
        C.log("Nothing to judge.")
        return
    C.log(
        f"Judging {len(todo)} queries, {n_pairs} (query, candidate) pairs "
        f"(~{n_pairs / len(todo):.1f} per query) with {C.JUDGE_MODEL}"
    )

    client = C.openai_client()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(judge_one, client, q, qmap, meta, todo[q]): q for q in todo}
        done = 0
        for fut in as_completed(futs):
            try:
                qid, grades = fut.result()
                judged.setdefault(qid, {}).update(grades)
            except Exception as e:  # noqa: BLE001
                C.log(f"  judging failed for {futs[fut]}: {str(e)[:90]}")
            done += 1
            if done % 25 == 0:
                C.log(f"  judged {done}/{len(todo)}")

    write_qrels(judged)

    # Diagnostic: how often did the judge agree that the seed tool was relevant?
    dist = Counter(judged.get(qid, {}).get(qmap[qid]["source_tool"], "missing") for qid in judged)
    C.log(f"Seed-tool grade distribution: {dict(dist)}")

    # Sample for measuring judge agreement against a human annotator.
    rng = random.Random(C.SEED + 7)
    pairs = [(qid, n, g) for qid in judged for n, g in judged[qid].items()]
    rng.shuffle(pairs)
    sample = pairs[: min(VALIDATION_SAMPLE, len(pairs))]
    lines = ["query_id\ttool_name\tquery\ttool_description\tjudge_grade\thuman_grade"]
    for qid, name, grade in sample:
        q = qmap[qid]["query"].replace("\t", " ")
        d = (meta[name]["description"] or "").replace("\t", " ").replace("\n", " ")[:200]
        lines.append(f"{qid}\t{name}\t{q}\t{d}\t{grade}\t")
    (C.DATA_DIR / "judge_validation_sample.tsv").write_text("\n".join(lines) + "\n")
    C.log(f"Wrote judge_validation_sample.tsv ({len(sample)} pairs); fill in human_grade to measure agreement")


if __name__ == "__main__":
    main()
