"""Run the with/without ToolUniverse ablation on a built question set.

The measurement is a controlled ablation: the same agent, the same base model, the same
prompts and the same code execution, run twice, with the presence of ToolUniverse as the
only difference. The gap between the two conditions is what ToolUniverse contributes,
with the model held constant.

Two agents are supported out of the box:

  claude   the Claude Code CLI; ToolUniverse is attached with --plugin-dir
  codex    the Codex CLI; ToolUniverse is attached through an MCP server in the config
           file (see codex_config/), and the baseline config must be identical except
           for that server

Answers are parsed from [ANSWER]X[/ANSWER] and graded by letter, so grading is exact and
needs no model. An unparseable or refused answer counts as incorrect, which makes the
reported accuracy a lower bound rather than a number that quietly drops hard cases.

Usage:
    python run_ablation.py --items data/dbqa.jsonl --agent claude --out results/dbqa.json
    python run_ablation.py --items data/seqqa.jsonl --agent codex --reps 3 \\
        --codex-with codex_config/with_tooluniverse.toml \\
        --codex-without codex_config/baseline.toml
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ANSWER_RE = re.compile(r"\[ANSWER\]\s*([A-Z])\s*\[/ANSWER\]", re.IGNORECASE)


# --------------------------------------------------------------------------- agents
def run_claude(prompt, with_tooluniverse, args):
    cmd = [
        args.claude_bin,
        "--output-format", "json",
        "--model", args.model,
        "--max-turns", str(args.max_turns),
    ]
    if with_tooluniverse:
        if not args.plugin_dir:
            raise SystemExit("--plugin-dir is required for the with-ToolUniverse condition")
        cmd += ["--plugin-dir", args.plugin_dir]

    env = dict(os.environ)
    # The ToolUniverse MCP server loads thousands of tools and can take minutes to
    # answer tools/list. The CLI's default MCP start-up timeout is far shorter, and when
    # it expires the run still succeeds -- with no ToolUniverse tools attached at all.
    # That failure is silent and it invalidates the with-condition, so raise both.
    env.setdefault("MCP_TIMEOUT", "600000")
    env.setdefault("MCP_TOOL_TIMEOUT", "600000")

    try:
        res = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                             env=env, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return f"ERROR: timeout after {args.timeout}s"

    out = (res.stdout or "").strip()
    if out:
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            return out
        # A policy refusal exits non-zero but still returns valid JSON with the refusal
        # text in `result`. Keep it: it is a wrong answer, not a missing measurement.
        r = payload.get("result")
        if isinstance(r, str):
            return r
        if isinstance(r, list):
            return "\n".join(b.get("text", "") for b in r
                             if isinstance(b, dict) and b.get("type") == "text")
        return json.dumps(payload)[:2000]
    return f"ERROR: {(res.stderr or '')[:300]}"


def run_codex(prompt, with_tooluniverse, args):
    config = args.codex_with if with_tooluniverse else args.codex_without
    if not config:
        raise SystemExit("--codex-with and --codex-without are required for the codex agent")
    cmd = [args.codex_bin, "exec", "--config", str(Path(config).resolve()), "-"]
    try:
        res = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                             timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return f"ERROR: timeout after {args.timeout}s"
    return (res.stdout or res.stderr or "")[-4000:]


AGENTS = {"claude": run_claude, "codex": run_codex}


# --------------------------------------------------------------------------- scoring
def extract_answer(text):
    """Return the letter inside [ANSWER]...[/ANSWER], or None."""
    matches = ANSWER_RE.findall(text or "")
    return matches[-1].upper() if matches else None


def run_condition(items, with_tooluniverse, args):
    agent = AGENTS[args.agent]
    records = []
    label = "with" if with_tooluniverse else "without"
    for i, item in enumerate(items, 1):
        t0 = time.time()
        response = agent(item["prompt"], with_tooluniverse, args)
        predicted = extract_answer(response)
        records.append(
            {
                "id": item["id"],
                "subtask": item.get("subtask", ""),
                "gold": item["answer"],
                "predicted": predicted,
                "correct": predicted == item["answer"],
                "parsed": predicted is not None,
                "seconds": round(time.time() - t0, 1),
                "response_tail": (response or "")[-800:],
            }
        )
        if i % 5 == 0 or i == len(items):
            acc = sum(r["correct"] for r in records) / len(records)
            print(f"  [{label}] {i}/{len(items)}  running accuracy {acc:.3f}", flush=True)
    return records


def summarize(reps):
    """Per-repetition accuracies plus their mean."""
    accs = [sum(r["correct"] for r in rec) / len(rec) for rec in reps if rec]
    unparsed = [sum(not r["parsed"] for r in rec) for rec in reps if rec]
    return {
        "accuracy_per_rep": accs,
        "accuracy": sum(accs) / len(accs) if accs else None,
        "unparsed_per_rep": unparsed,
        "n_items": len(reps[0]) if reps else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True, help="jsonl produced by build_dataset.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--agent", choices=sorted(AGENTS), default="claude")
    ap.add_argument("--reps", type=int, default=3, help="repetitions per condition")
    ap.add_argument("--conditions", default="both", choices=["both", "with", "without"])
    ap.add_argument("--limit", type=int, default=0, help="first N items only (smoke test)")
    ap.add_argument("--timeout", type=int, default=2400)
    # claude
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    ap.add_argument("--model", default=os.environ.get("EVAL_MODEL", "claude-opus-4-8"))
    ap.add_argument("--max-turns", type=int, default=80)
    ap.add_argument("--plugin-dir", default=os.environ.get("TOOLUNIVERSE_PLUGIN_DIR"),
                    help="built ToolUniverse plugin directory")
    # codex
    ap.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    ap.add_argument("--codex-with", default=None)
    ap.add_argument("--codex-without", default=None)
    args = ap.parse_args()

    items = [json.loads(line) for line in open(args.items) if line.strip()]
    if args.limit:
        items = items[: args.limit]
    print(f"{len(items)} items from {args.items}, agent={args.agent}, reps={args.reps}")

    out = {
        "run_meta": {
            "items": args.items,
            "n_items": len(items),
            "agent": args.agent,
            "model": args.model if args.agent == "claude" else "see codex config",
            "reps": args.reps,
        }
    }

    for condition, flag in (("with_tooluniverse", True), ("without_tooluniverse", False)):
        if args.conditions != "both" and args.conditions != condition.split("_")[0]:
            continue
        reps = []
        for rep in range(args.reps):
            print(f"[{condition}] repetition {rep + 1}/{args.reps}")
            reps.append(run_condition(items, flag, args))
        out[condition] = {"reps": reps, "summary": summarize(reps)}
        print(f"[{condition}] mean accuracy {out[condition]['summary']['accuracy']:.3f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.out}")

    a = out.get("with_tooluniverse", {}).get("summary", {}).get("accuracy")
    b = out.get("without_tooluniverse", {}).get("summary", {}).get("accuracy")
    if a is not None and b is not None:
        print(f"ToolUniverse contribution: {100 * (a - b):+.1f} points "
              f"({100 * b:.1f}% -> {100 * a:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
