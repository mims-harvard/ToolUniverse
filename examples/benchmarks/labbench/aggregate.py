"""Render a comparison table from one or more run_ablation.py result files.

Prints the measured with/without accuracies next to the published values in
reference_results.json, so a reproduction can be checked at a glance.

Usage:
    python aggregate.py results/dbqa.json results/seqqa.json
    python aggregate.py results/*.json --agent codex
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def subtask_of(path, meta):
    name = (meta.get("items", "") + " " + Path(path).stem).lower()
    if "seqqa" in name:
        return "SeqQA"
    if "dbqa" in name:
        return "DbQA"
    return Path(path).stem


def pct(x):
    return f"{100 * x:.1f}" if isinstance(x, (int, float)) else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+")
    ap.add_argument("--agent", choices=["claude_code", "codex"], default=None,
                    help="which published column to compare against (default: infer)")
    args = ap.parse_args()

    reference = json.loads((HERE / "reference_results.json").read_text())["subtasks"]

    print("| Subtask | N | with TU | without TU | difference | published (with/without) | Biomni |")
    print("|---|---|---|---|---|---|---|")
    for path in args.results:
        d = json.loads(Path(path).read_text())
        meta = d.get("run_meta", {})
        subtask = subtask_of(path, meta)
        agent = args.agent or ("codex" if meta.get("agent") == "codex" else "claude_code")

        with_acc = d.get("with_tooluniverse", {}).get("summary", {}).get("accuracy")
        without_acc = d.get("without_tooluniverse", {}).get("summary", {}).get("accuracy")
        delta = (f"{100 * (with_acc - without_acc):+.1f}"
                 if isinstance(with_acc, (int, float)) and isinstance(without_acc, (int, float))
                 else "-")

        ref = reference.get(subtask, {})
        ref_agent = ref.get(agent, {})
        published = (f"{ref_agent.get('with_tooluniverse', '-')}/{ref_agent.get('without_tooluniverse', '-')}"
                     if ref_agent else "-")

        print(f"| {subtask} | {meta.get('n_items', '-')} | {pct(with_acc)} | {pct(without_acc)} "
              f"| {delta} | {published} | {ref.get('biomni_published', '-')} |")

    print("\nPublished values are from https://aiscientist.tools/posts/labbench-benchmark "
          "(3 repetitions). Agent runs are not deterministic, so a faithful reproduction "
          "lands near these numbers rather than exactly on them.")


if __name__ == "__main__":
    main()
