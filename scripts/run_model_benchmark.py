#!/usr/bin/env python3
"""Rank the unified-interface model backends against a public dataset.

Deliberately a script rather than a ToolUniverse tool. Benchmarking is a
maintainer's operation: a run takes minutes, issues hundreds of API calls, and
against a paid provider costs real money. Exposing that to an agent as a flag
on a tool that normally answers in two seconds is a footgun, and an agent
solving a scientific task does not need it -- it needs a prediction. The tools
in ``data/unified_model_tools.json`` are for tasks; this is for deciding which
backend to trust, and for checking that a newly added backend actually works.

Usage
-----
    # what datasets exist, with citations and leakage risk
    python scripts/run_model_benchmark.py --list-datasets

    # variant effect against experimental deep-mutational-scanning data
    python scripts/run_model_benchmark.py variant_effect \
        --dataset proteingym_dms --limit 40

    # one TDC ADMET endpoint
    python scripts/run_model_benchmark.py molecular_property \
        --dataset tdc_admet --property bbb_martins --limit 24

    # your own labelled file
    python scripts/run_model_benchmark.py variant_effect \
        --dataset file --path my_variants.jsonl

Read ``coverage`` before any other metric: a model that scored 40% of a set can
post a flattering AUROC on the easy remainder.
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "task",
        nargs="?",
        choices=[
            "variant_effect",
            "structure_prediction",
            "molecular_property",
            "binding_affinity",
        ],
    )
    parser.add_argument(
        "--dataset", help="proteingym_dms | clinvar_missense | tdc_admet | file"
    )
    parser.add_argument("--list-datasets", action="store_true")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--assay", help="proteingym_dms: UniProt entry name, DMS id or protein name"
    )
    parser.add_argument(
        "--property", help="tdc_admet: TDC dataset name, e.g. bbb_martins"
    )
    parser.add_argument("--gene", help="clinvar_missense: restrict to one gene")
    parser.add_argument("--path", help="dataset=file: local CSV/TSV/JSONL")
    parser.add_argument("--label-field", default="label")
    parser.add_argument("--backends", help="comma-separated ids; default all")
    parser.add_argument("--metrics", help="comma-separated; first is used for ranking")
    parser.add_argument("--item-workers", type=int, default=3)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument(
        "--per-item", action="store_true", help="include every item's scores"
    )
    parser.add_argument("--json", action="store_true", help="dump the raw report")
    args = parser.parse_args()

    from tooluniverse.unified_model_tool import UnifiedModelBenchmarkTool

    task = args.task or "variant_effect"
    tool = UnifiedModelBenchmarkTool({"name": "benchmark", "fields": {"task": task}})

    if args.list_datasets:
        print(json.dumps(tool.run({"list_datasets": True})["datasets"], indent=2))
        return 0

    if not args.task or not args.dataset:
        parser.error("a task and --dataset are required (or use --list-datasets)")

    payload = {
        "dataset": args.dataset,
        "limit": args.limit,
        "seed": args.seed,
        "item_workers": args.item_workers,
        "max_workers": args.max_workers,
        "include_per_item": args.per_item,
        "label_field": args.label_field,
    }
    for key in ("assay", "property", "gene", "path"):
        if getattr(args, key):
            payload[key] = getattr(args, key)
    for key in ("backends", "metrics"):
        value = getattr(args, key)
        if value:
            payload[key] = [v.strip() for v in value.split(",") if v.strip()]

    report = tool.run(payload)
    if report.get("status") != "success":
        print(f"error: {report.get('error')}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    dataset = report["dataset"]
    print(
        f"\n{dataset['name']}  n={dataset['n_items']}  labels={dataset['label_type']}"
    )
    print(f"source: {dataset['source']}")
    print(f"cite:   {dataset['citation']}\n")

    metric = report["ranked_by"]
    cols = [metric, "auprc", "spearman", "accuracy", "mcc", "coverage"]
    header = f"{'model':22s} " + " ".join(f"{c[:8]:>8s}" for c in cols)
    print(header)
    print("-" * len(header))
    for row in report["leaderboard"]:
        cells = []
        for c in cols:
            v = row.get(c)
            cells.append(f"{v:8.3f}" if isinstance(v, (int, float)) else f"{'-':>8s}")
        print(f"{row['model'][:22]:22s} " + " ".join(cells))

    if report.get("leakage_warning"):
        print(f"\nLEAKAGE: {report['leakage_warning']}")
    if report.get("model_correlation"):
        print("\nbetween-model agreement (Spearman, direction-corrected):")
        for left, inner in report["model_correlation"].items():
            for right, rho in inner.items():
                print(f"  {left:20s} vs {right:20s} {rho:+.3f}")
    print("\ncaveats:")
    for c in report["caveats"]:
        print(f"  - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
