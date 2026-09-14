#!/usr/bin/env python3
"""Record and check the reviewed contracts of pinned third-party MCP tools.

Each ``mcp_auto_loader_*.json`` config with ``strict_tool_contracts`` pins its
tools by ``contract_sha256`` -- a hash of ``{name, inputSchema, outputSchema}``.
The hash alone can show *that* an upstream server changed a tool, never *what*
it changed, so a maintainer asked to re-pin has nothing to review and can only
accept blind. This script keeps the reviewed schemas themselves in

    src/tooluniverse/data/mcp_contracts.lock.json

so upstream drift shows up as a readable diff.

Modes
-----
``--check-config``
    Offline. Verifies the lockfile and the loader configs agree, i.e. every
    pinned tool is present in the lockfile and the recorded schemas still hash
    to the ``contract_sha256`` in the config. Deterministic, so it is safe to
    run on every pull request.

``--check-live``
    Fetches each server's current contracts and diffs them against the
    lockfile. Exits non-zero on drift. A server that cannot be reached is
    reported and skipped rather than failed, so a vendor outage or a rate limit
    does not masquerade as drift.

``--update``
    Fetches current contracts and rewrites the lockfile. The resulting diff is
    the review material; commit it only after reading it.

Endpoints come from ``MCP_ENDPOINTS`` below (the public URLs documented in each
loader's ``api_key_info``), overridable via the loader's own environment
variable so a private deployment can be checked instead.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import difflib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "src" / "tooluniverse" / "data"
LOCKFILE = DATA / "mcp_contracts.lock.json"

sys.path.insert(0, str(REPO / "src"))

# Public endpoints documented in each loader's api_key_info "without" note.
# The env var is the loader's configured server_url variable; when it is set it
# wins, so a private deployment can be checked in place of the public one.
MCP_ENDPOINTS = {
    "mcp_auto_loader_exa": ("EXA_MCP_URL", "https://mcp.exa.ai/mcp"),
    "mcp_auto_loader_folklore": (
        "FOLKLORE_MCP_URL",
        "https://api.helena.bio/folklore/v1/mcp",
    ),
    "mcp_auto_loader_noodle": (
        "NOODLE_MCP_URL",
        "https://api.helena.bio/noodle/v1/mcp",
    ),
    "mcp_auto_loader_gi": (
        "GENOMIC_INTELLIGENCE_MCP_URL",
        "https://mcp.genomicintelligence.ai/mcp",
    ),
}


def _pinned_loader_configs():
    """Yield (loader_name, config) for every contract-pinned MCP loader."""
    for path in sorted(DATA.glob("mcp_auto_loader_*.json")):
        try:
            entries = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise SystemExit(f"{path.name}: invalid JSON ({error})") from error
        for config in entries:
            if config.get("strict_tool_contracts"):
                yield config["name"], config


def _endpoint_for(loader_name):
    env_name, default_url = MCP_ENDPOINTS.get(loader_name, (None, None))
    if env_name and os.environ.get(env_name, "").strip():
        return os.environ[env_name].strip()
    return default_url


def _describe_error(error):
    """Flatten an exception (including ExceptionGroup) to a useful one-liner.

    The MCP client raises through a TaskGroup, whose own message is just
    "unhandled errors in a TaskGroup" -- useless in a canary report, where the
    whole point is telling a rate limit apart from a real outage.
    """
    seen, queue = [], [error]
    while queue:
        current = queue.pop(0)
        nested = getattr(current, "exceptions", None)
        if nested:
            queue.extend(nested)
            continue
        if current.__cause__ is not None:
            queue.append(current.__cause__)
            continue
        text = str(current).strip() or current.__class__.__name__
        seen.append(f"{current.__class__.__name__}: {text}")
    return "; ".join(dict.fromkeys(seen))[:200] or repr(error)[:200]


def _contract_of(tool_info):
    """The subset of a tool that the pin actually covers."""
    return {
        "name": tool_info.get("name"),
        "inputSchema": tool_info.get("inputSchema"),
        "outputSchema": tool_info.get("outputSchema"),
    }


async def _fetch_live_tools(loader_name, config, endpoint):
    from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

    probe_config = copy.deepcopy(config)
    probe_config["server_url"] = endpoint
    # Contract verification is what this script is reporting on, so discovery
    # must not apply it -- fetch the raw remote list instead.
    probe_config["strict_tool_contracts"] = False
    loader = MCPAutoLoaderTool(probe_config)
    response = await loader._make_mcp_request("tools/list")
    return {
        tool["name"]: tool for tool in response.get("tools", []) if tool.get("name")
    }


def _load_lockfile():
    if not LOCKFILE.exists():
        return {"loaders": {}}
    return json.loads(LOCKFILE.read_text())


def _write_lockfile(payload):
    LOCKFILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _schema_diff(name, recorded, live):
    """A unified diff of two contracts, or '' when they are identical."""
    old = json.dumps(recorded, indent=2, sort_keys=True).splitlines()
    new = json.dumps(live, indent=2, sort_keys=True).splitlines()
    if old == new:
        return ""
    return "\n".join(
        difflib.unified_diff(
            old,
            new,
            fromfile=f"{name} (reviewed)",
            tofile=f"{name} (live)",
            lineterm="",
        )
    )


def check_config():
    """Offline: the lockfile and the loader configs must agree."""
    from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

    lock = _load_lockfile()
    problems = []
    for loader_name, config in _pinned_loader_configs():
        locked = lock.get("loaders", {}).get(loader_name, {}).get("tools", {})
        for contract in config.get("tool_contracts", []):
            tool_name = contract["name"]
            pinned_hash = contract.get("contract_sha256")
            entry = locked.get(tool_name)
            if entry is None:
                problems.append(
                    f"{loader_name}/{tool_name}: pinned in the config but absent "
                    f"from {LOCKFILE.name}"
                )
                continue
            recorded_hash = MCPAutoLoaderTool._contract_sha256(entry["contract"])
            if recorded_hash != pinned_hash:
                problems.append(
                    f"{loader_name}/{tool_name}: config contract_sha256 "
                    f"{pinned_hash[:12]}... does not match the recorded schema "
                    f"(hashes to {recorded_hash[:12]}...)"
                )
        for tool_name in sorted(
            set(locked) - {c["name"] for c in config["tool_contracts"]}
        ):
            problems.append(
                f"{loader_name}/{tool_name}: present in {LOCKFILE.name} but not "
                f"pinned in the config"
            )

    if problems:
        print(f"{LOCKFILE.name} is out of sync with the loader configs:\n")
        for problem in problems:
            print(f"  - {problem}")
        print("\nRun: python3 scripts/sync_mcp_contracts.py --update")
        return 1
    print(f"{LOCKFILE.name} agrees with every pinned loader config.")
    return 0


def check_live():
    """Compare each server's current contracts against the lockfile."""
    lock = _load_lockfile()
    drifted, unreachable = [], []

    for loader_name, config in _pinned_loader_configs():
        endpoint = _endpoint_for(loader_name)
        if not endpoint:
            print(f"- {loader_name}: no endpoint configured, skipped")
            continue
        try:
            live = asyncio.run(_fetch_live_tools(loader_name, config, endpoint))
        except Exception as error:  # noqa: BLE001 - any transport failure
            unreachable.append((loader_name, _describe_error(error)))
            continue

        locked = lock.get("loaders", {}).get(loader_name, {}).get("tools", {})
        loader_drift = []
        for tool_name in sorted(locked):
            recorded = locked[tool_name]["contract"]
            if tool_name not in live:
                loader_drift.append((tool_name, "no longer served", ""))
                continue
            diff = _schema_diff(tool_name, recorded, _contract_of(live[tool_name]))
            if diff:
                loader_drift.append((tool_name, "contract changed", diff))

        if loader_drift:
            drifted.append((loader_name, endpoint, loader_drift))
            print(f"- {loader_name}: {len(loader_drift)} of {len(locked)} drifted")
        else:
            print(f"- {loader_name}: {len(locked)} tools match")

    for loader_name, reason in unreachable:
        print(f"- {loader_name}: unreachable, skipped ({reason})")

    if not drifted:
        if unreachable:
            print(
                f"\nNo drift among the loaders that answered, but "
                f"{len(unreachable)} could not be checked (see above)."
            )
        else:
            print("\nNo contract drift.")
        return 0

    print("\n" + "=" * 72)
    print("UPSTREAM CONTRACT DRIFT")
    print("=" * 72)
    for loader_name, endpoint, items in drifted:
        print(f"\n## {loader_name}  ({endpoint})\n")
        for tool_name, reason, diff in items:
            print(f"### {tool_name}: {reason}")
            print(diff or "  (tool is gone from the server)")
            print()
    print(
        "Review each diff, then re-pin deliberately:\n"
        "  python3 scripts/sync_mcp_contracts.py --update\n"
        "and update the matching contract_sha256 in the loader config.\n"
        "Pay particular attention to NEW INPUT FIELDS: the agent fills in any\n"
        "parameter a server advertises, so an added field is a new path for\n"
        "data to leave the session."
    )
    return 1


def update():
    """Rewrite the lockfile from the servers' current contracts."""
    lock = _load_lockfile()
    loaders = lock.setdefault("loaders", {})
    lock["_comment"] = (
        "Reviewed contracts of pinned third-party MCP tools. Generated by "
        "scripts/sync_mcp_contracts.py -- do not hand-edit. Its diffs are the "
        "review material for upstream schema changes."
    )
    touched = False

    for loader_name, config in _pinned_loader_configs():
        endpoint = _endpoint_for(loader_name)
        if not endpoint:
            print(f"- {loader_name}: no endpoint configured, skipped")
            continue
        try:
            live = asyncio.run(_fetch_live_tools(loader_name, config, endpoint))
        except Exception as error:  # noqa: BLE001 - any transport failure
            print(
                f"- {loader_name}: unreachable, left unchanged ({_describe_error(error)})"
            )
            continue

        pinned_names = [c["name"] for c in config.get("tool_contracts", [])]
        missing = [n for n in pinned_names if n not in live]
        if missing:
            print(f"- {loader_name}: not served: {', '.join(missing)}")

        loaders[loader_name] = {
            "endpoint": endpoint,
            "tools": {
                name: {"contract": _contract_of(live[name])}
                for name in pinned_names
                if name in live
            },
        }
        touched = True
        print(f"- {loader_name}: recorded {len(loaders[loader_name]['tools'])} tools")

    if touched:
        _write_lockfile(lock)
        print(f"\nWrote {LOCKFILE.relative_to(REPO)}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check-config", action="store_true", help="offline consistency check"
    )
    group.add_argument(
        "--check-live", action="store_true", help="diff servers against the lockfile"
    )
    group.add_argument(
        "--update", action="store_true", help="re-record contracts from the servers"
    )
    args = parser.parse_args()

    if args.check_config:
        return check_config()
    if args.check_live:
        return check_live()
    return update()


if __name__ == "__main__":
    raise SystemExit(main())
