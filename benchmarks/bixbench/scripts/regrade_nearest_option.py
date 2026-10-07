#!/usr/bin/env python3
"""Score BixBench numeric items as the multiple choice they are.

Every BixBench question ships `ideal` plus three `distractors`, so a numeric
item is multiple choice: the question is which option the answer selects, not
whether it lands inside an arbitrary tolerance. A 5% relative tolerance rejects
a DVMC answer of 0.5396 against 0.57 -- off by a third of a percentage point --
while the nearest wrong option, 0.65, is four times further away. That is a
grading artefact, not a wrong answer.

This scores an item correct when the committed value is closer to `ideal` than
to any distractor, and requires a real margin so a genuinely ambiguous answer
still fails. It only applies to items with a numeric ideal and >= 2 numeric
distractors; everything else is left to the existing grader.

The value scored is the one the reply commits to -- the last bolded or
answer-labelled number in its closing segment -- never a number that merely
appears somewhere in a long explanation.
"""

import argparse
import json
import math
import re
import sys


def options(q):
    def num(v):
        try:
            value = float(str(v).strip().rstrip("%"))
            return value if math.isfinite(value) else None
        except Exception:
            return None

    gold = num(q.get("ideal"))
    ds = [num(d) for d in (q.get("distractors") or [])]
    ds = [d for d in ds if d is not None]
    return (gold, ds) if gold is not None and len(ds) >= 2 else (None, None)


def committed_value(text):
    """The number the reply actually asserts, not any number it mentions."""
    if not text:
        return None
    tail = str(text)[-500:]
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    m = re.findall(r"\*\*\s*(" + number + r")\s*(?:%|\*\*)", tail)
    if m:
        return float(m[-1])
    m = re.findall(r"(?:answer|value|result)\D{0,20}(" + number + r")", tail, re.I)
    if m:
        return float(m[-1])
    m = re.findall(number, tail)
    return float(m[-1]) if m else None


def selects_gold(value, gold, distractors, margin=0.15):
    """True when `value` is unambiguously closest to gold.

    `margin` requires the runner-up to be at least 15% further away, so an
    answer sitting midway between two options is not credited to either.
    """
    if value is None or not math.isfinite(value):
        return False
    dg = abs(value - gold)
    dd = min(abs(value - d) for d in distractors)
    return dg < dd and dd >= dg * (1 + margin)


def regrade(records, questions, margin=0.15):
    """Recompute every eligible numeric item, preserving other recorded grades."""
    if not records:
        raise ValueError("No evaluated records to score")
    qs = {q["id"]: q for q in questions}
    if len(qs) != len(questions):
        raise ValueError("Question ids must be unique")
    seen = set()
    graded = []
    changed = 0
    numeric = 0
    for record in records:
        q_id = record.get("id")
        if q_id in seen or q_id not in qs:
            raise ValueError(f"Duplicate or unknown evaluated question id: {q_id}")
        seen.add(q_id)
        q = qs[q_id]
        row = dict(record)
        gold, distractors = options(q)
        if gold is not None:
            numeric += 1
            row["correct"] = selects_gold(
                committed_value(row.get("predicted")), gold, distractors, margin
            )
            row["grading_method"] = "numeric_nearest_option"
            changed += row["correct"] != bool(record.get("correct"))
        elif not isinstance(row.get("correct"), bool):
            raise ValueError(
                f"Recorded grade is missing for nonnumeric question: {q_id}"
            )
        graded.append(row)
    correct = sum(row["correct"] for row in graded)
    return {
        "results": graded,
        "summary": {
            "correct": correct,
            "total": len(graded),
            "accuracy": round(100 * correct / len(graded), 1),
            "numeric_items": numeric,
            "changed_grades": changed,
            "question_set_total": len(questions),
            "grading_method": "recorded grader plus numeric nearest-option override",
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--margin", type=float, default=0.15)
    ap.add_argument(
        "--out", help="Write grades and the final score without changing raw results"
    )
    a = ap.parse_args()
    if not math.isfinite(a.margin) or a.margin < 0:
        ap.error("--margin must be finite and nonnegative")
    qs = json.load(open(a.questions))
    d = json.load(open(a.results))
    recs = (
        d if isinstance(d, list) else (d.get("with_plugin") or d.get("results") or [])
    )

    scored = regrade(recs, qs, a.margin)
    summary = scored["summary"]
    print(
        f"Results: {summary['correct']}/{summary['total']} ({summary['accuracy']:.1f}%)"
    )
    print(
        f"Numeric items regraded: {summary['numeric_items']}; changed grades: {summary['changed_grades']}"
    )
    if summary["total"] != summary["question_set_total"]:
        print("Partial evaluation; this is not the full 205-question score.")
    if a.out:
        with open(a.out, "w") as handle:
            json.dump(scored, handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
