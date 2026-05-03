"""Skill-routing match test (v2): observe actual Skill() invocations.

Improved over v1 (skill_routing_test.py):
- Sends a natural user-style prompt (data path + question), no "DO NOT answer"
  guard. This is what a real user would type.
- Uses stream-json output and parses tool_use events for `Skill` invocations.
- Records the agent's FIRST sub-skill load (i.e., first `Skill(skill="tooluniverse-XXX")`)
  as the routing decision. Skips the router skill itself (`tooluniverse`).
- Eliminates hallucinated names: the agent must pick a real, loadable skill;
  Skill() with a non-existent name would error.

Usage:
    python skill_routing_test_v2.py --gt gt_skills.json --questions questions.json \\
        --out routing_results_v2.json [--n N] [--qids bix-1-q1,bix-2-q1] [--timeout 90]
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

{question}"""


def find_capsule(uuid: str) -> Path | None:
    for base in DATA_DIRS:
        cap = base / f"CapsuleFolder-{uuid}"
        if cap.exists():
            return cap
    return None


def normalize_skill(name: str) -> str:
    """Strip an optional `tooluniverse:` namespace prefix."""
    if not name:
        return ""
    return name.split(":", 1)[1] if name.startswith("tooluniverse:") else name


def ask_agent(question: str, data_path: Path, timeout: int = 120) -> dict:
    """Run the agent on a natural prompt and capture tool invocations.

    Returns dict with keys:
      - skill_calls: list of all Skill(skill=...) invocations observed (in order)
      - predicted: the first sub-skill load (skill name starting with `tooluniverse-`)
      - first_tool: name of the first tool the agent called (for debugging)
      - elapsed: wall time in seconds
      - error: present iff an error occurred
    """
    prompt = PROMPT_TEMPLATE.format(path=data_path, question=question)
    cmd = [
        "claude",
        "--plugin-dir", PLUGIN_DIR,
        "--output-format", "stream-json",
        "--verbose",
        "--max-turns", "5",
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "elapsed": time.time() - t0,
                "skill_calls": [], "predicted": "", "first_tool": ""}
    elapsed = time.time() - t0
    if proc.returncode != 0:
        return {"error": (proc.stderr or "")[:300], "elapsed": elapsed,
                "skill_calls": [], "predicted": "", "first_tool": ""}

    skill_calls: list[str] = []
    first_tool = ""
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        msg = event.get("message", {})
        for c in msg.get("content", []):
            if c.get("type") != "tool_use":
                continue
            tool_name = c.get("name", "")
            if not first_tool:
                first_tool = tool_name
            if tool_name == "Skill":
                skill_arg = c.get("input", {}).get("skill", "")
                skill_calls.append(skill_arg)

    # First sub-skill load (skip the router itself)
    predicted = ""
    for s in skill_calls:
        norm = normalize_skill(s)
        if norm.startswith("tooluniverse-"):
            predicted = norm
            break

    return {
        "skill_calls": skill_calls,
        "predicted": predicted,
        "first_tool": first_tool,
        "elapsed": elapsed,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gt", required=True, help="Path to gt_skills.json")
    p.add_argument("--questions", required=True, help="Path to questions.json")
    p.add_argument("--out", required=True, help="Output JSON path")
    p.add_argument("--n", type=int, default=0, help="Limit to first N questions")
    p.add_argument("--qids", default="", help="Comma-separated qids to test")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--resume", action="store_true",
                   help="Skip qids already in --out")
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
            "skill_calls": ans.get("skill_calls", []),
            "first_tool": ans.get("first_tool", ""),
            "error": ans.get("error", ""),
            "elapsed": round(ans.get("elapsed", 0), 1),
        }
        results.append(rec)
        flag = "OK " if match else "MISS"
        print(f"[{i}/{len(qs)}] {qid}: {flag} predicted={predicted!r} accept={accept}  ({rec['elapsed']}s)")
        out_path.write_text(json.dumps(results, indent=2))

    matched = sum(1 for r in results if r.get("match"))
    no_route = sum(1 for r in results if not r.get("predicted"))
    if results:
        print(f"\n=== {matched}/{len(results)} matched ({100*matched/len(results):.1f}%) "
              f"| {no_route} no-routing ===")


if __name__ == "__main__":
    main()
