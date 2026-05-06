#!/usr/bin/env python3
"""Failure analysis for a BixBench results JSON.

Classifies each wrong answer into a root-cause category and attributes
it to a skill (via the gt_skills.json question→skill mapping).

Outputs:
  - Per-failure record with category, evidence snippet, attributed skills
  - Per-skill heatmap (fail count, total used, fail rate) sorted by fail rate
  - Optional markdown report

Usage:
  python analyze_failures.py --results results.json [--out failure_analysis.json] \\
      [--report failure_report.md]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
QUESTIONS_FILE = REPO / "skills" / "evals" / "bixbench" / "questions.json"
GT_SKILLS_FILE = (
    REPO / "temp_docs_and_tests" / "benchmark_tracking"
    / "skill_routing_test" / "gt_skills.json"
)


# Failure classification heuristics
TIMEOUT_PATTERNS = [
    r"timeout after",
    r"\bERROR:\s*$",  # bare "ERROR:" with empty body = max_turns hit
    r"max_turns",
]
TOOL_ERROR_PATTERNS = [
    r"MCP error",
    r"tool error",
    r"Traceback \(most recent call last\)",
    r"\bexception\b",
    r"command not found",
]
NO_DATA_PATTERNS = [
    r"can'?t find",
    r"no .* (data|files?) (in|found|located)",
    r"directory .* (doesn'?t exist|does not exist|empty)",
]


def classify_failure(predicted: str, ground_truth: str) -> tuple[str, str]:
    """Return (category, evidence_snippet)."""
    pred_lower = predicted.lower()

    # Compute incomplete (timeout, max_turns, empty)
    if not predicted.strip() or predicted.strip() == "ERROR:":
        return "compute_incomplete", "(empty result — likely max_turns)"
    for pat in TIMEOUT_PATTERNS:
        m = re.search(pat, predicted, re.IGNORECASE)
        if m:
            return "compute_incomplete", f"(matches /{pat}/)"

    # Tool error (crash, traceback)
    for pat in TOOL_ERROR_PATTERNS:
        m = re.search(pat, predicted, re.IGNORECASE)
        if m:
            return "tool_error", predicted[max(0, m.start()-20):m.end()+60]

    # Couldn't find data (signal that workspace path / file lookup broke)
    for pat in NO_DATA_PATTERNS:
        m = re.search(pat, predicted, re.IGNORECASE)
        if m:
            return "no_data_found", predicted[max(0, m.start()-20):m.end()+60]

    # Numeric-vs-numeric within an order of magnitude → semantic mismatch
    pred_nums = re.findall(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", predicted)
    gt_nums = re.findall(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", ground_truth)
    if pred_nums and gt_nums:
        try:
            p = float(pred_nums[-1])  # last number in prediction is usually the answer
            g = float(gt_nums[0])
            if g != 0 and abs((p - g) / g) < 100:  # within 100x
                return "semantic_mismatch", f"predicted={p}, gt={g}"
        except (ValueError, ZeroDivisionError):
            pass

    # Default: wrong answer with no specific signal
    return "wrong_answer", predicted[:120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="results JSON from run_eval.py")
    ap.add_argument("--out", help="Write per-failure JSON")
    ap.add_argument("--report", help="Write markdown report")
    args = ap.parse_args()

    raw = json.loads(Path(args.results).read_text())
    runs = raw.get("with_plugin", raw if isinstance(raw, list) else [])
    if not runs:
        print(f"ERROR: no runs found in {args.results}", file=sys.stderr)
        sys.exit(1)

    questions = json.loads(QUESTIONS_FILE.read_text())
    qs_by_uuid = {q["id"]: q for q in questions}

    gt_skills = {}
    if GT_SKILLS_FILE.exists():
        gt_skills = json.loads(GT_SKILLS_FILE.read_text())

    failures = []
    skill_total = defaultdict(int)
    skill_fail = defaultdict(int)
    cat_count = defaultdict(int)

    for r in runs:
        uuid = r.get("id", "")
        q = qs_by_uuid.get(uuid, {})
        qid = q.get("question_id", "?")
        is_correct = r.get("correct", False)

        skills_for_q = gt_skills.get(qid, [])
        for s in skills_for_q:
            skill_total[s] += 1

        if is_correct:
            continue

        category, evidence = classify_failure(r.get("predicted", ""), str(r.get("ground_truth", "")))
        cat_count[category] += 1
        for s in skills_for_q:
            skill_fail[s] += 1

        failures.append({
            "qid": qid,
            "uuid": uuid,
            "category": category,
            "evidence": evidence[:200],
            "ground_truth": str(r.get("ground_truth", ""))[:80],
            "predicted_tail": r.get("predicted", "")[-160:],
            "elapsed_seconds": r.get("elapsed_seconds", 0),
            "skills": skills_for_q,
            "categories": q.get("categories", []),
        })

    total = len(runs)
    correct = sum(1 for r in runs if r.get("correct"))
    print(f"\nResults: {correct}/{total} correct ({100*correct/total:.1f}%)\n")

    print("Failure categories:")
    for cat, n in sorted(cat_count.items(), key=lambda x: -x[1]):
        print(f"  {cat:25s}  {n:3d}  ({100*n/total:.1f}%)")

    print("\nPer-skill heatmap (sorted by fail rate, min 3 uses):")
    print(f"  {'skill':40s} fails  total  rate")
    rows = []
    for s, used in skill_total.items():
        if used < 3:
            continue
        f = skill_fail.get(s, 0)
        rows.append((s, f, used, f / used if used else 0))
    rows.sort(key=lambda x: -x[3])
    for s, f, used, rate in rows:
        print(f"  {s:40s}  {f:3d}    {used:3d}   {100*rate:5.1f}%")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "summary": {
                "total": total, "correct": correct,
                "score": correct / total,
            },
            "failure_categories": dict(cat_count),
            "skill_heatmap": [
                {"skill": s, "fails": f, "total": used, "rate": rate}
                for s, f, used, rate in rows
            ],
            "failures": failures,
        }, indent=2))
        print(f"\nWrote per-failure JSON to {args.out}")

    if args.report:
        lines = [
            "# Failure Analysis Report",
            "",
            f"**Score:** {correct}/{total} ({100*correct/total:.1f}%)",
            "",
            "## Failure Categories",
            "",
            "| Category | Count | % |",
            "|---|---|---|",
        ]
        for cat, n in sorted(cat_count.items(), key=lambda x: -x[1]):
            lines.append(f"| {cat} | {n} | {100*n/total:.1f}% |")
        lines += ["", "## Per-Skill Heatmap", "",
                  "| Skill | Fails | Total Used | Fail Rate |",
                  "|---|---|---|---|"]
        for s, f, used, rate in rows:
            lines.append(f"| {s} | {f} | {used} | {100*rate:.1f}% |")
        lines += ["", "## Failures (by category, then skill)", ""]
        for cat in sorted(cat_count, key=lambda c: -cat_count[c]):
            lines.append(f"### {cat} ({cat_count[cat]})")
            lines.append("")
            for f in failures:
                if f["category"] == cat:
                    lines.append(f"- **{f['qid']}** [{', '.join(f['skills'])}]")
                    lines.append(f"  - GT: `{f['ground_truth']}`")
                    lines.append(f"  - evidence: `{f['evidence']}`")
            lines.append("")
        Path(args.report).write_text("\n".join(lines))
        print(f"Wrote markdown report to {args.report}")


if __name__ == "__main__":
    main()
