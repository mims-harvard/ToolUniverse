#!/usr/bin/env python3
"""What a tool returns, and what its `return_schema` admits to returning.

WHY THIS EXISTS. The field axis has two halves. `audit_upstream_field_coverage.py`
measures the first: a field the upstream answered that the wrapper never read.
This measures the second: a field the wrapper *does* return that the schema
never declares. An agent reads the schema to decide what a tool can answer, so
a field present in the payload and absent from the schema is barely less hidden
than one that was never fetched -- and a round that adds eight fields to a
wrapper and declares none of them has moved the drop rather than closed it.

It runs each tool's own first `test_example`, walks the live result against the
schema, and prints every path the schema does not account for.

THREE VACUOUS SHAPES MAKE A NAIVE CHECK SAY "OK". All three are in this
catalogue, and each hid real fields until the shape itself was treated as a
failure:

    {"type": "array", "items": {}}            Harmonizome_search
    {"type": "object"} as an `items` value    Alliance_get_gene_orthologs.paralogs
    a bare array schema, walked against the   FlyBase/ZFIN ortholog rows
      envelope dict, which has no array

So an object with no `properties` at all is reported as `*` -- "this level is
undeclared" -- rather than silently passing. An `additionalProperties` is the
one honest form of an open level: a map keyed by a value out of the data, such
as `synonym_type_counts`, declares its value shape and not its keys.

`return_schema` DESCRIBES EITHER THE INNER `data` OR THE WHOLE ENVELOPE, and no
config field says which. Both readings are printed. Do not take the one with
fewer complaints: against an envelope, a schema written for the inner data
reports exactly `.data`, `.metadata` and `.status` and so always looks tidier
than the reading that is actually in force.

    python scripts/audit_declared_return_fields.py --tools GOAPI_get_gene_functions
    python scripts/audit_declared_return_fields.py --shard 0/40
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "src" / "tooluniverse" / "data"
UNDECLARED_LEVEL = "*"
SAMPLE_PER_LIST = 20


def catalogue():
    """{tool name: config}, first definition wins as the loader does."""
    out = {}
    for path in sorted(DATA.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        for cfg in payload:
            if isinstance(cfg, dict) and cfg.get("name"):
                out.setdefault(cfg["name"], cfg)
    return out


def branches(schema):
    """The success and error alternatives a schema offers at one level."""
    if not isinstance(schema, dict):
        return []
    if "oneOf" in schema and isinstance(schema["oneOf"], list):
        return [b for b in schema["oneOf"] if isinstance(b, dict)]
    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        return [b for b in schema["anyOf"] if isinstance(b, dict)]
    return [schema]


def undeclared(value, schema, path="", found=None):
    """Paths in `value` that no branch of `schema` declares.

    A list descends through the first array branch's `items`; an object merges
    the `properties` of every non-array branch, because the error branch is a
    legitimate alternative at the same level.
    """
    if found is None:
        found = []
    bs = branches(schema)
    if isinstance(value, list):
        # `"items" in b`, not a truthiness test: `items: {}` is present and
        # declares nothing, which is a finding about the item level rather
        # than about the array.
        items = [b["items"] for b in bs if b.get("type") == "array" and "items" in b]
        if items:
            for item in value[:SAMPLE_PER_LIST]:
                undeclared(item, items[0], path + "[]", found)
        elif value and any(b.get("type") == "array" for b in bs):
            # An array declared without items: everything under it is undeclared.
            found.append(path + "[]" + UNDECLARED_LEVEL)
        return found
    if not isinstance(value, dict):
        return found
    object_bs = [b for b in bs if b.get("type") != "array"]
    # `oneOf` means the value validates against ONE branch, so a merge of the
    # branches is not the same schema. Merging defeated `additionalProperties`
    # outright: a success branch that declares its open level with
    # additionalProperties and no properties, beside an error branch that
    # declares `error`, merged to declared={"error"} -- non-empty, so the
    # additionalProperties was never consulted and every data key was
    # reported undeclared. That made the one form this script's own docstring
    # recommends for an open level impossible to use in a oneOf schema.
    #
    # Evaluating the branches independently and keeping the fewest findings
    # matches what oneOf means. A branch that declares nothing still reports
    # its level as `.*`, so a permissive branch cannot hide a gap, only
    # describe it more coarsely.
    if len(object_bs) > 1:
        best = None
        for b in object_bs:
            attempt = undeclared(value, b, path, [])
            if best is None or len(attempt) < len(best):
                best = attempt
        found.extend(best or [])
        return found
    declared = {}
    free = None
    for b in object_bs:
        declared.update(b.get("properties") or {})
        if isinstance(b.get("additionalProperties"), dict):
            free = b["additionalProperties"]
    if not declared:
        if free is not None:
            for sub in value.values():
                undeclared(sub, free, path + ".*", found)
        elif value:
            found.append(f"{path}.{UNDECLARED_LEVEL}")
        return found
    for key, sub in value.items():
        if key not in declared:
            if sub not in (None, [], {}):
                found.append(f"{path}.{key}")
            continue
        undeclared(sub, declared[key], f"{path}.{key}", found)
    return found


def select_shard(names, spec):
    """`i/n`: the i-th of n equal slices of the sorted name list."""
    if not spec:
        return names
    index, _, count = spec.partition("/")
    index, count = int(index), int(count)
    if count <= 0 or not 0 <= index < count:
        raise SystemExit(f"--shard {spec}: expected i/n with 0 <= i < n")
    return [n for position, n in enumerate(sorted(names)) if position % count == index]


def run_tool(name, arguments):
    from tooluniverse import ToolUniverse

    universe = ToolUniverse()
    universe.load_tools(include_tools=[name])
    return universe.run({"name": name, "arguments": arguments})


def audit(names, cfgs):
    reports = {}
    for name in names:
        cfg = cfgs.get(name)
        if cfg is None:
            reports[name] = {"skipped": "not in the catalogue"}
            continue
        schema = cfg.get("return_schema")
        if schema is None:
            reports[name] = {"undeclared_schema": True}
            print(f"!! {name}: return_schema ABSENT", flush=True)
            continue
        examples = cfg.get("test_examples") or []
        if not examples:
            reports[name] = {"skipped": "no test_example"}
            continue
        arguments = examples[0].get("arguments", examples[0])
        try:
            result = run_tool(name, arguments)
        except Exception as error:  # a live call; its failure is not a finding
            reports[name] = {"skipped": f"{type(error).__name__}: {error}"}
            print(f"?? {name}: {type(error).__name__}", flush=True)
            continue
        if not isinstance(result, (dict, list)):
            reports[name] = {"skipped": f"returned {type(result).__name__}"}
            continue
        readings = {}
        inner = result.get("data") if isinstance(result, dict) else None
        for label, value in (("data", inner), ("envelope", result)):
            if value is None:
                continue
            readings[label] = sorted(set(undeclared(value, schema)))
        reports[name] = {"readings": readings}
        for label, paths in readings.items():
            mark = "ok" if not paths else "!!"
            print(f"{mark} {name} [{label}]: {len(paths)} undeclared", flush=True)
            for item in paths[:30]:
                print(f"     {item}", flush=True)
    return reports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", nargs="*")
    parser.add_argument("--shard", help="i/n, to split the catalogue across jobs")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--json-output")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO / "src"))
    cfgs = catalogue()
    names = args.tools or select_shard(list(cfgs), args.shard)
    if args.limit:
        names = names[: args.limit]
    reports = audit(names, cfgs)
    thin = [
        name
        for name, report in reports.items()
        if report.get("undeclared_schema")
        or any(report.get("readings", {}).get(label) for label in ("data",))
    ]
    print(
        f"\nchecked {len(reports)} tool(s); {len(thin)} return a field their "
        "return_schema does not declare, read as the inner data"
    )
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(reports, indent=2))
        print(f"wrote {args.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
