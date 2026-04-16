#!/usr/bin/env python3
"""Analyze benchmark results: category breakdown, failure classification, trends.

Usage:
  python analyze_results.py --results graded.json
  python analyze_results.py --results graded.json --benchmark bixbench
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def classify_failure(result: dict) -> str:
    """Classify a failure using devtu-fix-tool error taxonomy."""
    pred = result.get("predicted", "")
    if "Timeout" in pred:
        return "timeout"
    if pred.startswith("ERROR"):
        error_text = pred.lower()
        if "api key" in error_text:
            return "api_key_missing"
        if "404" in error_text or "not found" in error_text:
            return "endpoint_not_found"
        if "validation" in error_text or "schema" in error_text:
            return "schema_validation"
        return "tool_error"
    if not pred or pred.strip() == "":
        return "empty_response"
    return "wrong_answer"


def categorize_question(question: dict, benchmark: str = "") -> str:
    """Categorize a question for grouping."""
    # Lab-bench: use subtask field
    subtask = question.get("subtask", "")
    if subtask:
        return subtask.replace("-v1-public", "")

    # BixBench: categorize by question content
    q = question.get("question", "").lower()
    if "deseq2" in q and "enrichgo" in q:
        return "DESeq2+enrichGO"
    if "deseq2" in q:
        return "DESeq2"
    if "ordinal" in q or "logistic regression" in q:
        return "regression"
    if "anova" in q or "f-statistic" in q:
        return "ANOVA"
    if "pathway" in q and "enrichment" in q:
        return "pathway_enrichment"
    if "phylogen" in q or "treeness" in q:
        return "phylogenetics"
    if "variant" in q or "vcf" in q:
        return "variant_analysis"
    if "fold change" in q or "log2" in q:
        return "fold_change"
    if "how many" in q or "percentage" in q or "count" in q:
        return "data_counting"
    if "chi-square" in q:
        return "chi_square"
    return "other"


def analyze(results_path: str, benchmark: str = "") -> dict:
    """Analyze benchmark results."""
    with open(results_path) as f:
        data = json.load(f)

    # Handle nested format
    all_configs = {}
    if isinstance(data, dict):
        for config_name, results in data.items():
            if isinstance(results, list):
                all_configs[config_name] = results
    elif isinstance(data, list):
        all_configs["results"] = data

    analysis = {}
    for config_name, results in all_configs.items():
        # Overall
        correct = sum(1 for r in results if r.get("correct"))
        total = len(results)
        total_time = sum(r.get("elapsed_seconds", 0) for r in results)

        # By category
        by_category = defaultdict(lambda: {"correct": 0, "total": 0, "failures": []})
        for r in results:
            cat = categorize_question(r, benchmark)
            by_category[cat]["total"] += 1
            if r.get("correct"):
                by_category[cat]["correct"] += 1
            else:
                by_category[cat]["failures"].append(
                    {
                        "id": r.get("id", ""),
                        "type": classify_failure(r),
                        "ground_truth": str(r.get("ground_truth", ""))[:50],
                        "predicted": str(r.get("predicted", ""))[:80],
                    }
                )

        # Failure breakdown
        failure_types = defaultdict(int)
        for r in results:
            if not r.get("correct"):
                failure_types[classify_failure(r)] += 1

        analysis[config_name] = {
            "overall": {
                "correct": correct,
                "total": total,
                "accuracy": round(correct / total * 100, 1) if total else 0,
                "total_time": round(total_time),
                "avg_time": round(total_time / total, 1) if total else 0,
            },
            "by_category": {
                cat: {
                    "correct": v["correct"],
                    "total": v["total"],
                    "accuracy": round(v["correct"] / v["total"] * 100) if v["total"] else 0,
                    "failures": v["failures"],
                }
                for cat, v in sorted(by_category.items())
            },
            "failure_types": dict(failure_types),
        }

    return analysis


def print_analysis(analysis: dict):
    """Print analysis to stdout."""
    for config_name, data in analysis.items():
        overall = data["overall"]
        print(f"\n{'='*60}")
        print(f"{config_name}: {overall['correct']}/{overall['total']} ({overall['accuracy']}%)")
        print(f"Total time: {overall['total_time']}s, avg: {overall['avg_time']}s/question")
        print(f"{'='*60}")

        print(f"\nBy category:")
        for cat, v in data["by_category"].items():
            print(f"  {cat}: {v['correct']}/{v['total']} ({v['accuracy']}%)")

        if data["failure_types"]:
            print(f"\nFailure types:")
            for ftype, count in sorted(data["failure_types"].items(), key=lambda x: -x[1]):
                print(f"  {ftype}: {count}")

        # Top failures
        all_failures = []
        for cat, v in data["by_category"].items():
            for f in v["failures"]:
                all_failures.append({**f, "category": cat})
        if all_failures:
            print(f"\nTop failures:")
            for f in all_failures[:10]:
                print(f"  [{f['type']}] {f['category']}: GT={f['ground_truth']}")


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("--results", required=True, help="Path to results JSON")
    parser.add_argument("--benchmark", default="", help="Benchmark name for categorization")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    analysis = analyze(args.results, args.benchmark)

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print_analysis(analysis)


if __name__ == "__main__":
    main()
