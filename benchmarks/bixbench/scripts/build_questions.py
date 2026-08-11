#!/usr/bin/env python3
"""Rebuild BixBench's 205-question set from the public HuggingFace dataset.

The question file used by the campaign was derived, not authored: every field
comes from `futurehouse/BixBench`. It is regenerated here rather than committed
because the rows carry the benchmark's canary GUID, which must not be copied
into a repository.

    python3 bixbench_build_questions.py --out questions.json

Each row keeps `id`, `question`, `ideal`, `distractors`, `capsule_uuid` and
`eval_mode`. `eval_mode` decides how the answer is checked and is not
interchangeable:

    str_verifier    (61)  exact / normalised string match
    range_verifier  (61)  `ideal` is an interval such as "(1.50,1.54)"
    llm_verifier    (83)  free text or a loose number -- needs a model judge

Note the graders: batch grading in `grade_answers.py` defaults to
`use_llm=False`, so `llm_verifier` rows are scored by string and numeric rules
the mode exists precisely to avoid. Pass `use_llm=True` for an honest
`llm_verifier` number, and score numeric items against the offered options
rather than a bare tolerance -- a DVMC answer of 0.5396 fails a 5% tolerance
against 0.57 by a third of a percent while the nearest wrong option is four
times further away.
"""

import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="questions.json")
    ap.add_argument("--split", default="train")
    a = ap.parse_args()

    from datasets import load_dataset  # noqa: PLC0415

    ds = load_dataset("futurehouse/BixBench", split=a.split)
    rows = []
    for r in ds:
        for q in (
            json.loads(r["questions"])
            if isinstance(r.get("questions"), str)
            else (r.get("questions") or [])
        ):
            rows.append(
                {
                    "id": q.get("id"),
                    "question": q.get("question"),
                    "ideal": q.get("ideal"),
                    "distractors": q.get("distractors"),
                    "capsule_uuid": r.get("uuid"),
                    "short_id": r.get("short_id"),
                    "eval_mode": q.get("eval_mode") or r.get("eval_mode"),
                    "categories": r.get("categories"),
                    "data_folder": r.get("data_folder"),
                }
            )
    with open(a.out, "w") as fh:
        json.dump(rows, fh, indent=1)
    print(f"wrote {a.out}: {len(rows)} questions")


if __name__ == "__main__":
    main()
