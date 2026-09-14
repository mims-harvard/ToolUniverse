"""Decide whether upstream MCP schema drift can be tolerated at load time.

A third-party MCP server changes its tool schemas whenever it likes. Refusing
every changed tool turns a vendor's documentation tweak into an outage for a
user who cannot review a third-party schema or re-pin it. Accepting every
changed tool would let a server reshape what an autonomous agent sends.

The way out is to answer a much narrower question than "is this change safe?":

    would a call built from the contract we reviewed still be valid?

That is decidable, and it only ever decides *availability*. It never decides
*trust*: the schema handed to the agent is always the reviewed one, so a field
the server added is never filled in, and every re-pin stays a human decision in
CI (see scripts/sync_mcp_contracts.py). A wrong answer here costs a tool, not a
secret.

Only two kinds of drift are tolerated, both provably incapable of invalidating
a reviewed call:

* documentation-only edits (``description``, ``title``, ``examples`` ...)
* newly added *optional* properties

Anything else -- a new required field, a removed or retyped property, a
tightened constraint -- disables that one tool until a maintainer reviews the
diff. When in doubt this module says "not compatible", because the cost of a
false reject is the status quo while the cost of a false accept is a broken
call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Keys that carry no constraint: they cannot make a previously valid request
# invalid, so a change confined to them is documentation, not interface.
_DOCUMENTATION_KEYS = {
    "description",
    "title",
    "examples",
    "$comment",
    "deprecated",
    "readOnly",
    "writeOnly",
}

_LOCKFILE = Path(__file__).resolve().parent / "data" / "mcp_contracts.lock.json"

_lockfile_cache: Optional[Dict[str, Any]] = None


def load_reviewed_contracts(loader_name: str) -> Dict[str, Dict[str, Any]]:
    """Reviewed contracts for one loader, keyed by tool name.

    Returns an empty mapping when the lockfile is absent or unreadable; callers
    then keep the strict hash-only behaviour, which is what shipped before the
    lockfile existed.
    """
    global _lockfile_cache
    if _lockfile_cache is None:
        try:
            _lockfile_cache = json.loads(_LOCKFILE.read_text())
        except (OSError, json.JSONDecodeError):
            _lockfile_cache = {}
    loaders = _lockfile_cache.get("loaders", {})
    entry = loaders.get(loader_name, {})
    return {
        name: record["contract"]
        for name, record in entry.get("tools", {}).items()
        if isinstance(record, dict) and isinstance(record.get("contract"), dict)
    }


def _constraints_equal(reviewed: Any, live: Any) -> bool:
    """Compare two schema fragments ignoring purely documentary keys."""
    if isinstance(reviewed, dict) and isinstance(live, dict):
        reviewed_keys = {k for k in reviewed if k not in _DOCUMENTATION_KEYS}
        live_keys = {k for k in live if k not in _DOCUMENTATION_KEYS}
        if reviewed_keys != live_keys:
            return False
        return all(_constraints_equal(reviewed[k], live[k]) for k in reviewed_keys)
    if isinstance(reviewed, list) and isinstance(live, list):
        return len(reviewed) == len(live) and all(
            _constraints_equal(a, b) for a, b in zip(reviewed, live)
        )
    return reviewed == live


def input_drift_reasons(
    reviewed: Optional[Dict[str, Any]], live: Optional[Dict[str, Any]]
) -> List[str]:
    """Why a reviewed call would no longer be valid; empty means tolerable."""
    if not isinstance(reviewed, dict) or not isinstance(live, dict):
        # Nothing to reason about, so do not claim the drift is safe.
        return ["input schema is not an object"]

    reasons: List[str] = []

    # A field that became required is the one drift we have actually seen break
    # a tool: reviewed calls omit it, so the server rejects them.
    reviewed_required = set(reviewed.get("required") or [])
    live_required = set(live.get("required") or [])
    for name in sorted(live_required - reviewed_required):
        reasons.append(f"{name!r} is now required")

    reviewed_props = reviewed.get("properties") or {}
    live_props = live.get("properties") or {}
    for name, reviewed_sub in reviewed_props.items():
        if name not in live_props:
            reasons.append(f"{name!r} no longer accepted")
        elif not _constraints_equal(reviewed_sub, live_props[name]):
            reasons.append(f"{name!r} changed shape")

    # Everything outside properties/required -- additionalProperties, type,
    # allOf, dependencies ... -- must be untouched. Added *optional* properties
    # are the deliberate exception and are simply never sent.
    ignored = {"properties", "required"} | _DOCUMENTATION_KEYS
    for key in sorted((set(reviewed) | set(live)) - ignored):
        if not _constraints_equal(reviewed.get(key), live.get(key)):
            reasons.append(f"schema keyword {key!r} changed")

    return reasons


def classify(
    reviewed_contract: Optional[Dict[str, Any]], live_tool: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Return (tolerable, reasons) for one tool's drift.

    ``tolerable`` means a call built from the reviewed contract is still valid
    against the live server, so the tool can keep working on the reviewed
    schema. It is not a statement that the change is benign.
    """
    if not reviewed_contract:
        # The hash already told us it moved; without a recorded schema there is
        # nothing to compare it against, so it cannot be assessed as tolerable.
        return False, ["contract changed, and no reviewed schema is recorded"]
    reasons = input_drift_reasons(
        reviewed_contract.get("inputSchema"), live_tool.get("inputSchema")
    )
    return (not reasons), reasons


def pinned_tool_from_reviewed(
    reviewed_contract: Dict[str, Any], live_tool: Dict[str, Any]
) -> Dict[str, Any]:
    """Build the tool to expose when tolerating compatible drift.

    The *input* schema is the reviewed one: that is the whole safety property.
    The agent fills in any parameter a server advertises, so exposing the live
    schema would let a newly added field collect data nobody reviewed. Since
    the drift is call-compatible, requests shaped by the reviewed schema remain
    valid, and the added field is simply never used.

    The *output* schema is taken live, because it is validated against what the
    server actually returns; holding a stale one would reject good responses.
    It describes returned data and so is not a path for data to leave.
    """
    pinned = dict(live_tool)
    pinned["inputSchema"] = json.loads(json.dumps(reviewed_contract["inputSchema"]))
    return pinned
