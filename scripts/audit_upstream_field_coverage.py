#!/usr/bin/env python3
"""What a tool's upstream answered, and what the tool passed on to the caller.

WHY THIS EXISTS. "Part of a result returned as all of it" has two axes. The row
axis was swept in #824: search and list tools now report `returned`,
`total_results`, `has_more`, `truncated` and `result_set_complete`. The field
axis -- a wrapper selecting a hand-written subset of each record and returning
it as the record -- can be measured mechanically for the 102 tools with a
declared GraphQL query, because the endpoint can be introspected. For the other
2,786 it cannot: nothing static says what the upstream offers.

This measures it from the call that is already being made. It records every
JSON response at the HTTP layer, runs the tool's own first test_example, and
compares the two.

IT COMPARES VALUES, NOT KEY NAMES. Wrappers rename. ComplexPortal answers
`ac`, `systematicName` and `participants`; the tool returns `complex_id`,
`systematic_name` and `subunits`. A key-name diff calls all three losses. A
value reaching the caller under any name is not a loss, so each upstream field
is scored by whether its own leaf values survive anywhere in the output.

IT REPORTS A FIELD WITH NO SURVIVING VALUE, NOT A LOW RATIO. A ratio flags
pagination, which is the other axis and already disclosed: MediaDive's upstream
answers 3,344 media and the tool returns a page of 20, so `data[].name` scores
20/3344 and reads as a loss while the field is plainly exposed. A field the
wrapper drops has no surviving value at all; a field it exposes has at least the
current page's. `--min-values` then suppresses the other false positive, a
single value that was transformed rather than dropped: ComplexPortal splits
`species` into `species` and `taxonomy_id`, so the combined upstream string
matches nothing.

Measured on CPX-1, what survives the two filters is real: the subunit records
drop `participants[].linkedFeatures[].*` -- which region of each subunit binds
which partner -- along with `bioRole` and the ontology ids used for
cross-referencing.

WHAT IT DOES NOT DECIDE. Whether a dropped field matters is the judgement rule
from devtu-silent-failures: it is a defect when the skipped field is the
substance of what the tool's own description promises. A wrapper may select
narrowly on purpose. This script names candidates.

USAGE
    python scripts/audit_upstream_field_coverage.py --pattern complex_portal
    python scripts/audit_upstream_field_coverage.py --tools ClinVar_get_submitted_records
    python scripts/audit_upstream_field_coverage.py --shard 0/8 --json-output cov.json

In the weekly sweep it rides on a call the sweep already makes, so the marginal
cost is the comparison, not the request.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MAX_DEPTH = 8
MIN_VALUE_LENGTH = 2  # one-character values match by accident


def leaf_values(node, out=None, depth=0):
    """Scalar leaf values reachable from `node`, as a list of strings."""
    if out is None:
        out = []
    if depth > MAX_DEPTH:
        return out
    if isinstance(node, dict):
        for value in node.values():
            leaf_values(value, out, depth + 1)
    elif isinstance(node, list):
        for value in node:
            leaf_values(value, out, depth + 1)
    elif node is None or isinstance(node, bool):
        pass
    else:
        text = str(node).strip()
        if len(text) >= MIN_VALUE_LENGTH:
            out.append(text)
    return out


def leaf_fields(node, prefix="", out=None, depth=0):
    """`{field path: [leaf values]}` for a nested structure.

    List indices are collapsed, so every element of `participants` contributes
    to `participants[].bioRole` rather than to 30 separate paths.
    """
    if out is None:
        out = {}
    if depth > MAX_DEPTH:
        return out
    if isinstance(node, dict):
        for key, value in node.items():
            leaf_fields(value, f"{prefix}.{key}" if prefix else key, out, depth + 1)
    elif isinstance(node, list):
        for value in node:
            leaf_fields(value, f"{prefix}[]", out, depth + 1)
    elif node is None or isinstance(node, bool):
        pass
    else:
        text = str(node).strip()
        if len(text) >= MIN_VALUE_LENGTH:
            out.setdefault(prefix, []).append(text)
    return out


def compare(upstream, returned):
    """Per upstream field: how many of its leaf values reached the caller."""
    survivors = set(leaf_values(returned))
    rows = []
    for field, values in leaf_fields(upstream).items():
        kept = sum(1 for value in values if value in survivors)
        rows.append({"field": field, "kept": kept, "total": len(values)})
    rows.sort(key=lambda r: (r["kept"] / r["total"], -r["total"]))
    return rows


def record_http():
    """Patch requests so every JSON response body is kept. Returns (list, undo)."""
    import requests

    captured = []
    original = requests.Session.send

    def send(self, request, **kwargs):
        response = original(self, request, **kwargs)
        try:
            body = response.json()
        except Exception:
            body = None
        captured.append(
            {
                "method": request.method,
                "url": request.url.split("?")[0],
                "status": response.status_code,
                "body": body,
            }
        )
        return response

    requests.Session.send = send
    return captured, lambda: setattr(requests.Session, "send", original)


def _emit(finding, on_result):
    if on_result is not None:
        on_result(finding)
    return finding


def tool_configs(names=None, pattern=None):
    found = {}
    for path in sorted((REPO / "src" / "tooluniverse" / "data").glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        for cfg in entries:
            if not isinstance(cfg, dict) or "name" not in cfg:
                continue
            if names and cfg["name"] not in names:
                continue
            if pattern and pattern.lower() not in (
                cfg["name"].lower() + " " + path.name.lower()
            ):
                continue
            if cfg.get("test_examples"):
                found[cfg["name"]] = cfg
    return found


def select_shard(names, spec):
    if not spec:
        return names
    index, count = (int(part) for part in spec.split("/"))
    return [
        name for position, name in enumerate(sorted(names)) if position % count == index
    ]


def audit(
    names=None,
    pattern=None,
    limit=None,
    shard=None,
    min_values=4,
    on_result=None,
):
    """Audit each tool, reporting through `on_result` as each one lands.

    Incremental by design, for the reason the sweep itself is sharded: a run
    killed part-way must still yield what it measured. A 45-minute step that
    prints only at the end yields nothing when it is cut off.
    """
    sys.path.insert(0, str(REPO / "src"))
    from tooluniverse import ToolUniverse

    configs = tool_configs(names, pattern)
    chosen = select_shard(list(configs), shard)
    if limit:
        chosen = chosen[:limit]
    if not chosen:
        return []

    findings = []
    universe = ToolUniverse()
    universe.load_tools(include_tools=chosen)

    for name in chosen:
        config = configs[name]
        example = config["test_examples"][0]
        captured, undo = record_http()
        try:
            result = universe.run({"name": name, "arguments": example})
        except Exception as exc:
            undo()
            findings.append(
                _emit(
                    {"tool": name, "skipped": f"{type(exc).__name__}: {exc}"}, on_result
                )
            )
            continue
        finally:
            undo()

        if not isinstance(result, dict) or result.get("status") == "error":
            findings.append(
                _emit(
                    {"tool": name, "skipped": "the tool returned an error"}, on_result
                )
            )
            continue
        bodies = [c["body"] for c in captured if isinstance(c["body"], (dict, list))]
        if not bodies:
            findings.append(
                _emit({"tool": name, "skipped": "no JSON upstream response"}, on_result)
            )
            continue

        returned = result.get("data", result)
        thin = []
        for body in bodies:
            for row in compare(body, returned):
                if row["total"] < min_values:
                    continue  # a single value that moved is a rename, not a loss
                # Zero survivors, not a low ratio. A ratio flags PAGINATION:
                # MediaDive's upstream answers 3,344 media and the tool returns
                # a page of 20, so `data[].name` scored 20/3344 and read as a
                # loss while the field is plainly exposed. That is the row axis,
                # which #824 already discloses. A field the wrapper drops has
                # NO surviving value; a field it exposes has at least the
                # current page's.
                if row["kept"] == 0:
                    thin.append(row)
        thin.sort(key=lambda r: -r["total"])
        findings.append(
            _emit(
                {
                    "tool": name,
                    "upstream_calls": len(captured),
                    "urls": sorted({c["url"] for c in captured})[:3],
                    "thin_fields": thin[:12],
                },
                on_result,
            )
        )
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", nargs="*")
    parser.add_argument("--pattern")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--shard", help="i/n, to split the catalogue across jobs")
    parser.add_argument(
        "--min-values",
        type=int,
        default=4,
        help="ignore upstream fields with fewer leaf values",
    )
    parser.add_argument("--json-output")
    args = parser.parse_args()

    # Print and persist as each tool lands. A step that is cut off -- a
    # 45-minute budget, an evicted runner -- still leaves everything it
    # measured, which is the lesson the sweep's own sharding records.
    def report(finding):
        if "thin_fields" not in finding:
            print(
                f"  skip  {finding['tool']:44s} {finding['skipped'][:60]}", flush=True
            )
            return
        rows = finding["thin_fields"]
        label = "THIN" if rows else "ok  "
        detail = ", ".join(f"{r['field']} {r['kept']}/{r['total']}" for r in rows[:5])
        print(f"  {label}  {finding['tool']:44s} {detail}", flush=True)
        if args.json_output:
            pathlib.Path(args.json_output).write_text(json.dumps(seen, indent=2))

    seen = []

    def on_result(finding):
        seen.append(finding)
        report(finding)

    findings = audit(
        args.tools,
        args.pattern,
        args.limit,
        args.shard,
        args.min_values,
        on_result=on_result,
    )
    audited = [f for f in findings if "thin_fields" in f]
    with_loss = [f for f in audited if f["thin_fields"]]
    print(
        f"\naudited {len(audited)} tool(s); {len(with_loss)} carry an upstream "
        f"field whose values mostly do not reach the caller"
    )
    if args.json_output:
        pathlib.Path(args.json_output).write_text(json.dumps(findings, indent=2))
        print("wrote", args.json_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
