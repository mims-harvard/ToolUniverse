"""Build the evaluation items from Biomni's released test split.

The comparison in the blog post is same-item: ToolUniverse is evaluated on exactly the
questions Biomni published its numbers on, presented exactly the way Biomni presented
them. That requires reproducing two things faithfully.

1. The option order. Biomni seeds NumPy once with 42, then shuffles
   ``distractors + [ideal] + ["Insufficient information..."]`` for each row in parquet
   order. Seeding per row, or iterating in a different order, produces a different
   letter for the correct answer on every question.
2. The prompt template, reproduced verbatim below, including the ``[ANSWER]`` tags the
   automatic parser reads.

The LAB-Bench questions themselves are not distributed here. They carry the benchmark's
canary string, and redistributing them would contaminate future training sets. Download
Biomni's ``benchmark.zip`` as documented at https://github.com/snap-stanford/Biomni,
unpack it, and point ``--bench-dir`` at the result.

Usage:
    python build_dataset.py --bench-dir /path/to/biomni_benchmark --out-dir data
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

INSUFFICIENT = "Insufficient information to answer the question."
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Verbatim from Biomni's LAB-Bench task definition.
PROMPT = """The following is a multiple choice question about biology.
Please answer by responding with the letter of the correct answer.

Question: {question}
Options:
{options}

You MUST include the letter of the correct answer within the following tags:
[ANSWER] and [/ANSWER]. For example, '[ANSWER]<answer>[/ANSWER]',
where <answer> is the correct letter. Always answer in exactly this format
of a single letter between the two tags, even if you are unsure.
We require this because we use automatic parsing."""


def build(parquet_path, out_path):
    df = pd.read_parquet(parquet_path)
    np.random.seed(42)  # seeded once, then each row shuffled in parquet order
    built = []
    for _, x in df.iterrows():
        options = list(x["distractors"]) + [x["ideal"]] + [INSUFFICIENT]
        np.random.shuffle(options)
        answer = LETTERS[options.index(x["ideal"])]
        options_block = "\n".join(f"{LETTERS[i]}.{item}" for i, item in enumerate(options))
        built.append(
            {
                "id": str(x["id"]),
                "subtask": x.get("subtask", ""),
                "options": options,
                "answer": answer,
                "ideal": x["ideal"],
                "prompt": PROMPT.format(question=x["question"], options=options_block),
            }
        )

    # The canary must never reach a file we write, as a field name or as text.
    blob = json.dumps(built).lower()
    assert "canary" not in blob, "canary leaked into the built items"
    assert "benchmark data should never appear" not in blob, "canary text leaked"

    with open(out_path, "w") as fh:
        for b in built:
            fh.write(json.dumps(b) + "\n")
    print(f"{os.path.basename(parquet_path)}: {len(built)} items -> {out_path}")
    return built


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-dir", default="data/biomni_benchmark",
                    help="unpacked benchmark.zip from the Biomni repository")
    ap.add_argument("--out-dir", default="data")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    build(f"{args.bench_dir}/DbQA/train-00000-of-00001_test.parquet",
          f"{args.out_dir}/dbqa.jsonl")
    build(f"{args.bench_dir}/SeqQA/train-00000-of-00001_test.parquet",
          f"{args.out_dir}/seqqa.jsonl")


if __name__ == "__main__":
    main()
