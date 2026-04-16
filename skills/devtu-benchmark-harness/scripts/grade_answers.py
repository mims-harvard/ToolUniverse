#!/usr/bin/env python3
"""Multi-strategy answer grading for ToolUniverse benchmarks.

Strategies (applied in order):
  1. Exact match — ground truth substring in prediction
  2. MC match — letter answer detection (A/B/C/D)
  3. Range match — numeric value within (low, high)
  4. Normalized match — strip punctuation, compare
  5. Numeric proximity — within configurable tolerance
  6. LLM verifier — Claude judges correctness (for complex answers)

Usage:
  python grade_answers.py --results results.json --output graded.json
  python grade_answers.py --results results.json --numeric-tolerance 0.10
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def grade_answer(
    predicted: str,
    ground_truth: str,
    eval_mode: str = "",
    numeric_tolerance: float = 0.05,
    use_llm: bool = False,
    question: str = "",
) -> dict:
    """Grade a predicted answer against ground truth using multiple strategies."""
    ground_truth = str(ground_truth)
    gt_lower = ground_truth.strip().lower()
    pred_lower = predicted.lower()

    # 1. Exact match
    exact_match = gt_lower in pred_lower

    # 2. MC match (single letter answers)
    mc_match = False
    if len(gt_lower) <= 3:
        patterns = [
            rf"\b{re.escape(gt_lower)}\b",
            rf"answer[:\s]+{re.escape(gt_lower)}",
            rf"\({re.escape(gt_lower)}\)",
        ]
        mc_match = any(re.search(p, pred_lower) for p in patterns)

    # 3. Range match
    range_match = False
    if eval_mode == "range_verifier" or (
        gt_lower.startswith("(") and "," in gt_lower
    ):
        try:
            low, high = gt_lower.strip("()").split(",")
            low, high = float(low), float(high)
            if low > high:
                low, high = high, low
            for n in re.findall(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", predicted):
                if low <= float(n) <= high:
                    range_match = True
                    break
        except (ValueError, IndexError):
            pass

    # 4. Normalized match
    gt_norm = re.sub(r"[^a-z0-9]", "", gt_lower)
    pred_norm = re.sub(r"[^a-z0-9]", "", pred_lower)
    normalized_match = len(gt_norm) >= 4 and gt_norm in pred_norm
    # Also try stem match (drop last 3 chars)
    stem_match = len(gt_norm) >= 6 and gt_norm[:-3] in pred_norm

    # 5. Numeric proximity
    numeric_match = False
    gt_num_str = gt_lower.replace("%", "").replace(",", "").strip()
    try:
        gt_num = float(gt_num_str)
        for n in re.findall(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", predicted):
            pred_num = float(n)
            if gt_num == 0:
                numeric_match = pred_num == 0
            elif abs(pred_num - gt_num) / abs(gt_num) < numeric_tolerance:
                numeric_match = True
                break
    except ValueError:
        pass

    # 6. LLM verifier (optional, for complex answers)
    llm_match = False
    if (
        use_llm
        and eval_mode == "llm_verifier"
        and not any([exact_match, mc_match, range_match, normalized_match, numeric_match])
    ):
        llm_match = _llm_grade(predicted, ground_truth, question)

    correct = any(
        [exact_match, mc_match, range_match, normalized_match, stem_match, numeric_match, llm_match]
    )

    return {
        "correct": correct,
        "strategies": {
            "exact_match": exact_match,
            "mc_match": mc_match,
            "range_match": range_match,
            "normalized_match": normalized_match,
            "stem_match": stem_match,
            "numeric_match": numeric_match,
            "llm_match": llm_match,
        },
        "ground_truth": ground_truth,
        "predicted_excerpt": predicted[:500],
    }


def _llm_grade(predicted: str, ground_truth: str, question: str) -> bool:
    """Use Claude to grade a complex answer."""
    prompt = (
        f"Grade this answer. Question: {question[:200]}\n"
        f"Expected answer: {ground_truth}\n"
        f"Predicted answer: {predicted[:500]}\n\n"
        f"Is the predicted answer correct or essentially equivalent to the expected answer? "
        f"Reply with just YES or NO."
    )
    try:
        r = subprocess.run(
            ["claude", "-p", prompt, "--max-turns", "1", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            result = data.get("result", "")
            if isinstance(result, list):
                text = " ".join(
                    b.get("text", "") for b in result if b.get("type") == "text"
                )
            else:
                text = str(result)
            return "yes" in text.lower()[:10]
    except Exception:
        pass
    return False


def grade_results_file(
    results_path: str,
    output_path: str = None,
    numeric_tolerance: float = 0.05,
    use_llm: bool = False,
) -> dict:
    """Grade all answers in a results file."""
    with open(results_path) as f:
        data = json.load(f)

    # Handle nested format {with_plugin: [...], baseline: [...]}
    all_results = {}
    if isinstance(data, dict):
        for config_name, results in data.items():
            if isinstance(results, list):
                all_results[config_name] = results
    elif isinstance(data, list):
        all_results["results"] = data

    graded = {}
    for config_name, results in all_results.items():
        graded_list = []
        for r in results:
            gt = str(r.get("ground_truth", r.get("ideal", r.get("answer", ""))))
            pred = r.get("predicted", "")
            eval_mode = r.get("eval_mode", "")
            question = r.get("question", "")

            grade = grade_answer(
                pred, gt, eval_mode, numeric_tolerance, use_llm, question
            )
            graded_list.append({**r, **grade})
        graded[config_name] = graded_list

    if output_path:
        with open(output_path, "w") as f:
            json.dump(graded, f, indent=2)

    # Summary
    summary = {}
    for config_name, results in graded.items():
        correct = sum(1 for r in results if r["correct"])
        total = len(results)
        summary[config_name] = {
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total * 100, 1) if total else 0,
        }

    return {"graded": graded, "summary": summary}


def main():
    parser = argparse.ArgumentParser(description="Grade benchmark answers")
    parser.add_argument("--results", required=True, help="Path to results JSON")
    parser.add_argument("--output", help="Path to save graded results")
    parser.add_argument(
        "--numeric-tolerance", type=float, default=0.05, help="Numeric tolerance (default 0.05)"
    )
    parser.add_argument("--llm", action="store_true", help="Use LLM for complex grading")
    args = parser.parse_args()

    result = grade_results_file(args.results, args.output, args.numeric_tolerance, args.llm)

    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
