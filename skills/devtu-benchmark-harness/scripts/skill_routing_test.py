"""Skill-routing match test for BixBench.

For each question, ask the plugin-loaded agent: "which ONE sub-skill would you
invoke first?" — without solving the question. Compare the agent's pick to the
acceptable-skill set (multiple skills may be valid for a question that spans
domains).

Usage:
    python skill_routing_test.py --gt gt_skills.json --questions questions.json \
        --out routing_results.json [--n N] [--qids bix-1-q1,bix-2-q1]
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_DIR = str(
    Path(__file__).resolve().parent.parent.parent.parent
    / "dist" / "tooluniverse-plugin"
)
DATA_DIRS = [
    Path(__file__).resolve().parent.parent.parent.parent
    / "temp_docs_and_tests" / "bixbench" / "data",
    Path(__file__).resolve().parent.parent.parent.parent
    / "temp_docs_and_tests" / "bixbench" / "bixbench" / "data",
]

PROMPT_TEMPLATE = """Data files are located at: {path}

{question}

DO NOT answer this question. DO NOT run any analysis or read any data files.

Your ONLY task: name the ONE specialized ToolUniverse plugin sub-skill you
would invoke first to handle this question. Output ONLY the skill name on a
single line, in the form `tooluniverse-<topic>` (e.g. `tooluniverse-rnaseq-deseq2`).
No explanation. No reasoning. No code. Just the skill name."""


def find_capsule(uuid: str) -> Path | None:
    for base in DATA_DIRS:
        cap = base / f"CapsuleFolder-{uuid}"
        if cap.exists():
            return cap
    return None


def extract_skill_name(text: str) -> str:
    """Find the first `tooluniverse-<topic>` token in the agent's reply."""
    if not text:
        return ""
    m = re.search(r"tooluniverse-[a-z0-9][a-z0-9-]*[a-z0-9]", text.lower())
    return m.group(0) if m else ""


def ask_agent(question: str, data_path: Path, timeout: int = 120) -> dict:
    prompt = PROMPT_TEMPLATE.format(path=data_path, question=question)
    cmd = [
        "claude",
        "--plugin-dir", PLUGIN_DIR,
        "--output-format", "json",
        "--max-turns", "8",
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "elapsed": time.time() - t0}
    elapsed = time.time() - t0
    if proc.returncode != 0:
        return {"error": (proc.stderr or "")[:300], "elapsed": elapsed}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": "non-json output", "elapsed": elapsed}
    result = data.get("result", "")
    if isinstance(result, list):
        result = "\n".join(
            b.get("text", "") for b in result
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return {"raw": result, "predicted": extract_skill_name(result), "elapsed": elapsed}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gt", required=True, help="Path to gt_skills.json")
    p.add_argument("--questions", required=True, help="Path to questions.json")
    p.add_argument("--out", required=True, help="Output JSON path")
    p.add_argument("--n", type=int, default=0, help="Limit to first N questions")
    p.add_argument("--qids", default="", help="Comma-separated qids to test")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--resume", action="store_true", help="Skip qids already in --out")
    args = p.parse_args()

    gt = json.loads(Path(args.gt).read_text())
    qs = json.loads(Path(args.questions).read_text())

    if args.qids:
        wanted = set(args.qids.split(","))
        qs = [q for q in qs if q.get("question_id") in wanted]
    elif args.n > 0:
        qs = qs[: args.n]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if args.resume and out_path.exists():
        try:
            existing = {r["qid"]: r for r in json.loads(out_path.read_text())}
        except Exception:
            existing = {}

    results = list(existing.values())
    print(f"Testing {len(qs)} questions ({len(existing)} already done)")
    for i, q in enumerate(qs, 1):
        qid = q["question_id"]
        if qid in existing:
            continue
        capsule = find_capsule(q.get("capsule_uuid", ""))
        if capsule is None:
            print(f"[{i}/{len(qs)}] {qid}: SKIP (no capsule)")
            continue
        accept = gt.get(qid, [])
        ans = ask_agent(q["question"], capsule, timeout=args.timeout)
        predicted = ans.get("predicted", "")
        match = predicted in accept
        rec = {
            "qid": qid,
            "expected": accept,
            "predicted": predicted,
            "match": match,
            "raw": (ans.get("raw") or ans.get("error", ""))[:300],
            "elapsed": round(ans.get("elapsed", 0), 1),
        }
        results.append(rec)
        flag = "OK " if match else "MISS"
        print(f"[{i}/{len(qs)}] {qid}: {flag} predicted={predicted!r} accept={accept}  ({rec['elapsed']}s)")
        # Persist after each question (interruptible)
        out_path.write_text(json.dumps(results, indent=2))

    matched = sum(1 for r in results if r.get("match"))
    print(f"\n=== {matched}/{len(results)} matched ({100*matched/len(results):.1f}%) ===" if results else "")


if __name__ == "__main__":
    main()
