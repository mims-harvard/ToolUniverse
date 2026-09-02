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
import re
import sys


def options(q):
    def num(v):
        try:
            return float(str(v).strip().rstrip("%"))
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
    tail = text[-500:]
    m = re.findall(r"\*\*\s*(-?\d+(?:\.\d+)?)\s*(?:%|\*\*)", tail)
    if m:
        return float(m[-1])
    m = re.findall(r"(?:answer|value|result)\D{0,20}(-?\d+(?:\.\d+)?)", tail, re.I)
    if m:
        return float(m[-1])
    m = re.findall(r"-?\d+(?:\.\d+)?", tail)
    return float(m[-1]) if m else None


def selects_gold(value, gold, distractors, margin=0.15):
    """True when `value` is unambiguously closest to gold.

    `margin` requires the runner-up to be at least 15% further away, so an
    answer sitting midway between two options is not credited to either.
    """
    if value is None:
        return False
    dg = abs(value - gold)
    dd = min(abs(value - d) for d in distractors)
    return dg < dd and dd >= dg * (1 + margin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--margin", type=float, default=0.15)
    a = ap.parse_args()

    qs = {q["id"]: q for q in json.load(open(a.questions))}
    d = json.load(open(a.results))
    recs = (
        d if isinstance(d, list) else (d.get("with_plugin") or d.get("results") or [])
    )

    flipped, checked = [], 0
    for r in recs:
        if r.get("correct"):
            continue
        q = qs.get(r.get("id"))
        if not q:
            continue
        gold, ds = options(q)
        if gold is None:
            continue
        checked += 1
        v = committed_value(r.get("predicted"))
        if selects_gold(v, gold, ds, a.margin):
            flipped.append((q.get("short_id"), v, gold, ds, r.get("question", "")[:60]))

    print(f"numeric-MCQ items among the failures: {checked}")
    print(f"answers that unambiguously select gold: {len(flipped)}\n")
    for sid, v, gold, ds, qq in flipped:
        print(f"  {sid:8s} answered {v:<10g} gold {gold:<8g} distractors {ds}")
        print(f"           {qq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
