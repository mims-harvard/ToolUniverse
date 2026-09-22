#!/usr/bin/env python3
"""Merge sharded health-check logs into a summary and a durable history row.

Two problems this closes.

**A lost runner used to cost everything.** `test_all_tools.py` writes its report
only after the last category, and an evicted runner never reaches the upload
step, so nothing survives -- 10 of 12 consecutive weekly runs ended that way, one
after 636 of 638 categories. The sweep is sharded now, so this reads whatever
shards did finish and says plainly how many categories were never reached.
Missing is reported as missing, never folded into passing.

**Nothing outlived the artifacts.** Run logs and artifacts expire, so decay over
more than a quarter was not measurable at all. One line per run is appended to a
history file that lives in the repository.

Usage:
    python scripts/summarize_health_sweep.py --logs 'shard-*/sweep_output*.log' \\
        --baseline .github/known_failing_categories.txt \\
        --history .github/tool-health-history.jsonl \\
        --summary "$GITHUB_STEP_SUMMARY" --run-id 123 --sha abc123
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

#: What `scripts/test_all_tools.py` prints per category, e.g.
#: `[1/86] cellrank: FAILED: 1 test failure(s)`, `[2/86] brenda: PASSED: 3 test(s)`,
#: `[58/86] pdbe_compound: SCHEMA ERROR: 1 invalid result(s)`.
#:
#: An older emoji form (`✅ 7 tests passed`, `❌ 1 failures`, `🔥 ERROR: Timeout`)
#: is still accepted so historical logs keep parsing.
PROGRESS = re.compile(
    r"\[(?P<index>\d+)/(?P<total>\d+)\]\s+(?P<category>[A-Za-z0-9_.-]+):\s*"
    r"(?:(?P<mark>✅|❌|🔥)\s*(?P<emoji_count>\d+)?"
    r"|(?P<status>PASSED|FAILED|SCHEMA ERROR|TIMEOUT|ERROR|NO TESTS)"
    r"(?:[^0-9\n]*(?P<count>\d+))?)"
)
FAILING = frozenset({"❌", "🔥"})
#: NO TESTS is neither a pass nor a failure: the category ships no executable
#: example, so it carries no signal either way and must not be counted as
#: passing, or a category losing its examples would look like a recovery.
FAILING_STATUS = frozenset({"FAILED", "SCHEMA ERROR", "TIMEOUT", "ERROR"})
PASSING_STATUS = frozenset({"PASSED"})
TIMEOUT_STATUS = frozenset({"TIMEOUT"})


def parse_logs(patterns: list) -> tuple[dict, dict, set, int]:
    """Return (results, failure_counts, timed_out, expected_total)."""
    results: dict = {}
    counts: dict = {}
    timed_out: set = set()
    expected = 0
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            try:
                text = Path(path).read_text(errors="replace")
            except OSError:
                continue
            shard_total = 0
            for match in PROGRESS.finditer(text):
                category = match.group("category")
                mark = match.group("mark")
                status = match.group("status")

                if mark:
                    passed = mark not in FAILING
                    failure_count = int(match.group("emoji_count") or 0)
                    is_timeout = mark == "🔥"
                elif status in PASSING_STATUS:
                    passed, failure_count, is_timeout = True, 0, False
                elif status in FAILING_STATUS:
                    passed = False
                    failure_count = int(match.group("count") or 0)
                    is_timeout = status in TIMEOUT_STATUS
                else:
                    # NO TESTS and anything unrecognised carry no verdict.
                    continue

                # Each shard counts its own slice, and the slices partition the
                # categories, so the run's expected total is their sum. Without
                # it a lost shard cannot be distinguished from a clean one.
                shard_total = max(shard_total, int(match.group("total")))

                # A category is only "passing" if nothing marked it failing;
                # shards never overlap, but be conservative if they ever do.
                results[category] = results.get(category, True) and passed
                if not passed:
                    counts[category] = failure_count
                    if is_timeout:
                        timed_out.add(category)
            expected += shard_total
    return results, counts, timed_out, expected


def load_baseline(path: str | Path) -> set:
    file = Path(path)
    if not file.exists():
        return set()
    out = set()
    for line in file.read_text(errors="replace").splitlines():
        token = line.split("#", 1)[0].strip()
        if token:
            out.add(token)
    return out


def build_summary(
    results, counts, timed_out, baseline, expected_total
) -> tuple[str, dict]:
    failing = {c for c, ok in results.items() if not ok}
    passing = set(results) - failing
    new = sorted(
        failing - baseline, key=lambda c: (c not in timed_out, -counts.get(c, 0), c)
    )
    recovered = sorted(baseline & passing)
    known = sorted(failing & baseline)
    missing = max(0, expected_total - len(results)) if expected_total else 0

    lines = ["# Weekly Tool Health Check", ""]
    lines.append(
        f"- Categories reported: **{len(results)}**"
        + (f" of {expected_total} — **{missing} never reached**" if missing else "")
    )
    lines.append(f"- Failing: **{len(failing)}**  |  baseline: **{len(baseline)}**")
    lines.append("")
    if missing:
        lines += [
            f"> {missing} category/categories were never reached — a shard was lost. "
            "They are **unknown**, not passing.",
            "",
        ]
    if new:
        lines += [f"## 🆕 NEW failing ({len(new)}) — investigate", ""]
        lines.append(
            ", ".join(
                f"`{c}`"
                + ("(timeout)" if c in timed_out else f"({counts.get(c, '?')})")
                for c in new
            )
        )
        lines += [
            "",
            "> Not in `.github/known_failing_categories.txt`. Reproduce before "
            "fixing — the sweep hits live APIs, where an outage looks exactly like "
            "a schema change:",
            "> `python scripts/test_all_tools.py --skip-remote --skip-mcp --pattern <category>`",
            "",
        ]
    else:
        lines += ["No new failures — every failing category is known. ✅", ""]
    if recovered:
        lines += [
            f"## ♻️ Recovered ({len(recovered)}) — prune the baseline",
            "",
            ", ".join(f"`{c}`" for c in recovered),
            "",
            "> Left in the baseline, the next real regression in these is invisible.",
            "",
        ]
    if known:
        lines += [
            f"<details><summary>Known failures ({len(known)})</summary>",
            "",
            ", ".join(f"`{c}`" for c in known),
            "",
            "</details>",
            "",
        ]

    row = {
        "reported": len(results),
        "expected": expected_total,
        "never_reached": missing,
        "passing": len(passing),
        "failing": len(failing),
        "new_failing": new,
        "recovered": recovered,
        "timed_out": sorted(timed_out),
        "baseline_size": len(baseline),
    }
    return "\n".join(lines), row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--logs", nargs="+", required=True, help="glob(s) of shard logs"
    )
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--history", help="JSONL file to append one row to")
    parser.add_argument("--summary", help="file to write the Markdown summary to")
    parser.add_argument(
        "--expected-total",
        type=int,
        default=0,
        help="categories the full sweep should cover",
    )
    parser.add_argument("--run-id", default="")
    parser.add_argument("--sha", default="")
    parser.add_argument(
        "--timestamp", default="", help="ISO timestamp; defaults to now (UTC)"
    )
    args = parser.parse_args(argv)

    results, counts, timed_out, parsed_total = parse_logs(args.logs)
    # The shards state their own slice size, so the run's expected total is
    # known without being told. Passing --expected-total still wins.
    expected_total = args.expected_total or parsed_total

    baseline = load_baseline(args.baseline)
    text, row = build_summary(results, counts, timed_out, baseline, expected_total)

    if not results:
        # This is how the check failed silently for weeks: the progress format
        # changed, the regex matched nothing, and "nothing failing" rendered as
        # a clean bill of health. An empty parse is a broken summary, never a
        # green one.
        message = (
            "no category results parsed from any shard log — the summary below "
            "is meaningless. Check that scripts/test_all_tools.py still prints "
            "'[i/N] category: STATUS' and that PROGRESS matches it."
        )
        print(message, file=sys.stderr)
        text = f"# Weekly Tool Health Check\n\n> **{message}**\n"

    print(text)
    if args.summary:
        with open(args.summary, "a") as handle:
            handle.write(text + "\n")

    if args.history:
        row.update(
            {
                "timestamp": args.timestamp or datetime.now(timezone.utc).isoformat(),
                "run_id": args.run_id,
                "sha": args.sha,
            }
        )
        path = Path(args.history)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        print(f"appended history row to {path}", file=sys.stderr)
    # A parse that found nothing must not be reported as a successful summary.
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
