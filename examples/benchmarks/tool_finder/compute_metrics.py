"""Step 5 - compute retrieval metrics, confidence intervals and significance tests.

Reads the persisted rankings and the graded judgments, and reports per strategy:
Recall@1/5/10, MRR and NDCG@10, each with a 95% bootstrap confidence interval over
queries. NDCG@10 uses the graded labels (gain 2 or 1), so a strategy is rewarded more
for a directly relevant tool than for a partially relevant one; the other metrics treat
grade >= 1 as relevant.

Three breakdowns are produced:
  * overall, across every judged query;
  * by difficulty level (L1 named, L2 intent, L3 scenario), both over all queries at
    each level and paired over complete L1/L2/L3 triples;
  * on the leakage-free held-out split, i.e. only queries whose target tool entered the
    catalogue after the fine-tuning cutoff, so the fine-tuned encoder cannot have seen
    it during training.

Significance for the fine-tuning ablation uses a paired bootstrap over per-query scores,
which respects the pairing of the two strategies on identical queries.

Outputs (in results/): main_table.csv, by_difficulty.csv, by_difficulty_paired.csv,
heldout_table.csv, significance.json, summary.md

Usage:
    python compute_metrics.py
"""

import math
from collections import defaultdict
from pathlib import Path

import numpy as np

import common as C

# Display order and labels. The first two are the ablation pair.
STRATEGY_ORDER = [
    "toolrag",
    "base",
    "openai-3-large",
    "openai-3-small",
    "gte-qwen2-7b",
    "e5-mistral-7b",
    "gte-large",
    "s-pubmedbert",
    "keyword",
    "llm",
]
LABELS = {
    "toolrag": "Tool_Finder, default encoder (ToolRAG-T1, fine-tuned)",
    "base": "Tool_Finder, un-fine-tuned base encoder (ablation)",
    "openai-3-large": "Tool_Finder, embedding_model=openai-3-large",
    "openai-3-small": "Tool_Finder, embedding_model=openai-3-small",
    "gte-qwen2-7b": "Tool_Finder, embedding_model=gte-qwen2-7b",
    "e5-mistral-7b": "Tool_Finder, embedding_model=e5-mistral-7b",
    "gte-large": "gte-large-en-v1.5",
    "s-pubmedbert": "S-PubMedBert-MS-MARCO",
    "keyword": "Tool_Finder_Keyword (BM25)",
    "llm": "Tool_Finder_LLM",
}
# Parameter count and release date, for a size- and recency-aware reading of the table.
# These are the figures published by each model's own card or announcement, not
# measurements taken here; they are metadata for the reader, and nothing in the
# scoring depends on them.
MODEL_INFO = {
    "toolrag": ("1.5B", "2024-06"),
    "base": ("1.5B", "2024-06"),
    "openai-3-large": ("undisclosed", "2024-01"),
    "openai-3-small": ("undisclosed", "2024-01"),
    "gte-qwen2-7b": ("7.6B", "2024-06"),
    "e5-mistral-7b": ("7B", "2024-01"),
    "gte-large": ("434M", "2024-04"),
    "s-pubmedbert": ("109M", "2022"),
    "keyword": ("-", "-"),
    "llm": ("-", "-"),
}

KS = (1, 5, 10)
METRICS = [f"Recall@{k}" for k in KS] + ["MRR", "NDCG@10"]
NBOOT = 1000


def load_qrels():
    path = C.DATA_DIR / "qrels.tsv"
    if not path.exists():
        raise SystemExit(
            f"No judgments at {path}. Fetch the released ones with "
            "'python download_data.py', or build your own with 'python build_qrels.py'."
        )
    qrels = defaultdict(dict)
    with open(path) as f:
        next(f)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                qrels[parts[0]][parts[1]] = int(parts[2])
    return qrels


def load_rankings():
    out = {}
    for fp in sorted(Path(C.RANK_DIR).glob("*.jsonl")):
        out[fp.stem] = {r["query_id"]: r["ranked"] for r in C.read_jsonl(fp)}
    return out


def dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def per_query_metrics(ranked, rel):
    relevant = {t for t, g in rel.items() if g >= 1}
    n_rel = len(relevant)
    out = {}
    for k in KS:
        hits = sum(1 for t in ranked[:k] if t in relevant)
        out[f"Recall@{k}"] = hits / n_rel if n_rel else 0.0
    out["MRR"] = next((1.0 / (i + 1) for i, t in enumerate(ranked) if t in relevant), 0.0)
    ideal = sorted(rel.values(), reverse=True)[:10]
    idcg = dcg(ideal)
    out["NDCG@10"] = dcg([rel.get(t, 0) for t in ranked[:10]]) / idcg if idcg > 0 else 0.0
    return out


def usable(qids, qrels, *ranking_maps):
    """Query ids that are judged, have at least one relevant tool, and are ranked by all."""
    out = []
    for qid in qids:
        if qid not in qrels or not any(g >= 1 for g in qrels[qid].values()):
            continue
        if all(qid in rm for rm in ranking_maps):
            out.append(qid)
    return out


def scores_for(ranking_map, qrels, qids):
    rows = {m: [] for m in METRICS}
    for qid in qids:
        m = per_query_metrics(ranking_map[qid], qrels[qid])
        for k in METRICS:
            rows[k].append(m[k])
    return {k: np.array(v) for k, v in rows.items()}


def boot_ci(arr, nboot=NBOOT, seed=C.SEED):
    if len(arr) == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = arr[rng.integers(0, len(arr), size=(nboot, len(arr)))].mean(axis=1)
    return float(arr.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired_boot_p(a, b, nboot=NBOOT, seed=C.SEED):
    """Two-sided paired bootstrap p-value for mean(a) - mean(b) != 0."""
    if len(a) == 0 or len(a) != len(b):
        return float("nan")
    d = a - b
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), size=(nboot, len(d)))].mean(axis=1)
    p = 2 * np.mean(bs <= 0) if d.mean() >= 0 else 2 * np.mean(bs >= 0)
    return float(min(1.0, p))


def paired_difficulty(queries, rankings, qrels, strategies):
    """NDCG@10 by level over complete L1/L2/L3 triples.

    The per-level tables above are computed on whatever queries survive at each level, so
    a level's score partly reflects which tools happen to be in it. Restricting to
    (tool, example) triples that have at least one pooled positive at all three levels
    removes that confound: every level then scores the same underlying needs, and the
    L1-to-L3 drop is a property of the phrasing rather than of the sample.
    """
    with_positive = {q for q, d in qrels.items() if any(g >= 1 for g in d.values())}
    by_triple = defaultdict(dict)
    for qid in with_positive:
        r = queries.get(qid)
        if r:
            by_triple[(r["source_tool"], r.get("example_index", 0))][r["difficulty"]] = qid
    triples = [t for t, levels in by_triple.items() if {"L1", "L2", "L3"} <= set(levels)]
    if not triples:
        return None, []
    per_level = {d: [by_triple[t][d] for t in sorted(triples)] for d in ("L1", "L2", "L3")}

    rows = []
    for st in strategies:
        cells, nd = {}, {}
        for level, qids in per_level.items():
            used = [q for q in qids if q in rankings[st]]
            scores = [per_query_metrics(rankings[st][q], qrels[q]) for q in used]
            nd[level] = sum(x["NDCG@10"] for x in scores) / len(used)
            cells[f"NDCG@10_{level}"] = nd[level]
            cells[f"Recall@10_{level}"] = sum(x["Recall@10"] for x in scores) / len(used)
        cells["NDCG@10_drop_L1_L3"] = nd["L1"] - nd["L3"]
        rows.append((st, cells))
    rows.sort(key=lambda r: -r[1]["NDCG@10_L3"])
    return len(triples), rows


def table_for(qids, rankings, qrels, strategies):
    out = {}
    for s in strategies:
        used = usable(qids, qrels, rankings[s])
        sc = scores_for(rankings[s], qrels, used)
        out[s] = {m: boot_ci(sc[m]) for m in METRICS}
        out[s]["n"] = len(used)
    return out


def write_csv(path, table, strategies):
    lines = [",".join(["strategy", "params", "release", *METRICS, "n"])]
    for s in strategies:
        if s not in table:
            continue
        params, release = MODEL_INFO.get(s, ("-", "-"))
        cells = [f"{table[s][m][0]:.4f}" for m in METRICS]
        lines.append(",".join(['"' + LABELS[s] + '"', params, release, *cells, str(table[s]["n"])]))
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    qrels = load_qrels()
    rankings = load_rankings()
    strategies = [s for s in STRATEGY_ORDER if s in rankings]
    if not strategies:
        raise SystemExit("No rankings found. Run run_systems.py first.")
    C.log(f"strategies with rankings: {strategies}")

    queries_path = C.DATA_DIR / "queries.jsonl"
    if not queries_path.exists():
        raise SystemExit(f"No queries at {queries_path}. Run 'python download_data.py' first.")
    queries = {r["query_id"]: r for r in C.read_jsonl(queries_path)}
    all_qids = list(qrels)

    main_table = table_for(all_qids, rankings, qrels, strategies)
    write_csv(C.RESULTS_DIR / "main_table.csv", main_table, strategies)

    # By difficulty level.
    lines = [",".join(["difficulty", "strategy", *METRICS, "n"])]
    for level in ("L1", "L2", "L3"):
        qids = [q for q in all_qids if queries.get(q, {}).get("difficulty") == level]
        t = table_for(qids, rankings, qrels, strategies)
        for s in strategies:
            cells = ",".join(f"{t[s][m][0]:.4f}" for m in METRICS)
            lines.append(f'{level},"{LABELS[s]}",{cells},{t[s]["n"]}')
    (C.RESULTS_DIR / "by_difficulty.csv").write_text("\n".join(lines) + "\n")

    # Paired by difficulty: same underlying needs at all three levels.
    n_triples, paired_rows = paired_difficulty(queries, rankings, qrels, strategies)
    if n_triples:
        cols = ["strategy", "NDCG@10_L1", "NDCG@10_L2", "NDCG@10_L3", "NDCG@10_drop_L1_L3",
                "Recall@10_L1", "Recall@10_L2", "Recall@10_L3", "n_triples"]
        lines = [",".join(cols)]
        for st, cells in paired_rows:
            lines.append(
                ",".join(['"' + LABELS[st] + '"']
                         + [f"{cells[c]:.4f}" for c in cols[1:-1]]
                         + [str(n_triples)])
            )
        (C.RESULTS_DIR / "by_difficulty_paired.csv").write_text("\n".join(lines) + "\n")
        C.log(f"paired triples with a positive at all three levels: {n_triples}")

    # Leakage-free held-out split.
    held_qids = [q for q in all_qids if queries.get(q, {}).get("heldout")]
    held_table = table_for(held_qids, rankings, qrels, strategies)
    write_csv(C.RESULTS_DIR / "heldout_table.csv", held_table, strategies)

    # Significance for the fine-tuning ablation, overall and held-out.
    significance = {}
    if "toolrag" in rankings and "base" in rankings:
        for label, qids in (("overall", all_qids), ("heldout", held_qids)):
            common_qids = usable(qids, qrels, rankings["toolrag"], rankings["base"])
            a = scores_for(rankings["toolrag"], qrels, common_qids)
            b = scores_for(rankings["base"], qrels, common_qids)
            significance[f"fine_tuning_ablation_{label}"] = {
                m: {
                    "mean_difference": float(a[m].mean() - b[m].mean()),
                    "p": paired_boot_p(a[m], b[m]),
                    "n": len(common_qids),
                }
                for m in ("NDCG@10", "Recall@10", "MRR")
            }
    C.save_json(C.RESULTS_DIR / "significance.json", significance)

    # Human-readable summary.
    def fmt(t):
        return f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"

    corpus = C.load_json(C.DATA_DIR / "corpus_snapshot.json")
    md = [
        "# Tool Finder retrieval benchmark",
        "",
        f"Pool: {corpus['n_tools_pool']} tools (catalogue commit {corpus['commit'][:10]}). "
        f"Judged queries: {len(all_qids)}, pooled and graded. Judge: {C.JUDGE_MODEL}.",
        "",
        "## NDCG@10 overall (95% bootstrap CI)",
        "",
    ]
    for s in strategies:
        md.append(f"- **{LABELS[s]}**: NDCG@10 {fmt(main_table[s]['NDCG@10'])}, "
                  f"Recall@10 {fmt(main_table[s]['Recall@10'])}, MRR {fmt(main_table[s]['MRR'])}")
    if "toolrag" in main_table and "base" in main_table:
        ft = main_table["toolrag"]["NDCG@10"][0]
        bs = main_table["base"]["NDCG@10"][0]
        sig = significance.get("fine_tuning_ablation_overall", {}).get("NDCG@10", {})
        md += [
            "",
            "## Fine-tuning ablation",
            "",
            f"- Overall NDCG@10: fine-tuned {ft:.3f} against the identical un-fine-tuned base "
            f"{bs:.3f}, a difference of {ft - bs:+.3f} "
            f"(paired bootstrap p={sig.get('p', float('nan')):.4f}, n={sig.get('n', 0)}).",
        ]
        if held_table.get("toolrag", {}).get("n"):
            fth = held_table["toolrag"]["NDCG@10"][0]
            bsh = held_table["base"]["NDCG@10"][0]
            sigh = significance.get("fine_tuning_ablation_heldout", {}).get("NDCG@10", {})
            md.append(
                f"- Held-out split ({held_table['toolrag']['n']} queries on tools added after the "
                f"fine-tuning cutoff): {fth:.3f} against {bsh:.3f}, {fth - bsh:+.3f} "
                f"(p={sigh.get('p', float('nan')):.4f})."
            )
    (C.RESULTS_DIR / "summary.md").write_text("\n".join(md) + "\n")

    C.log("\n=== overall ===")
    C.log(f"{'strategy':52s} " + " ".join(f"{m:>10s}" for m in METRICS) + "     n")
    for s in strategies:
        C.log(
            f"{LABELS[s]:52s} "
            + " ".join(f"{main_table[s][m][0]:10.3f}" for m in METRICS)
            + f"  {main_table[s]['n']}"
        )
    C.log(f"\nWrote {C.RESULTS_DIR}/: main_table.csv, by_difficulty.csv, "
          "by_difficulty_paired.csv, heldout_table.csv, significance.json, summary.md")


if __name__ == "__main__":
    main()
