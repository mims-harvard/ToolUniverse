"""Decide whether upstream MCP schema drift can be tolerated at load time.

A third-party MCP server changes its tool schemas whenever it likes. Refusing
every changed tool turns a vendor's documentation tweak into an outage for a
user who cannot review a third-party schema or re-pin it. Accepting the live
contract would let a server reshape what an autonomous agent sends, and put
unreviewed prose into what it reads.

The way out is to answer a much narrower question than "is this change safe?":

    would the contract we reviewed still work against the live server?

That is decidable, and it only ever decides *availability*. It never decides
*trust*: a tolerated tool runs on the reviewed contract in full, so nothing the
server changed reaches the agent, and every re-pin stays a human decision on the
CI diff (see scripts/sync_mcp_contracts.py). A wrong answer costs a tool, not a
secret.

Two properties make that safe to automate, and both matter:

* The reviewed contract is trusted only when it hashes to the
  ``contract_sha256`` pinned in the loader config. The lockfile is a *record* of
  what was reviewed, never an independent source of authority -- otherwise
  refreshing the lockfile alone (which ``--update`` does) would silently
  re-point the trust anchor at whatever the server currently serves.
* A tolerated tool is published from the reviewed contract entirely, input and
  output. ``outputSchema`` is not merely descriptive: it reaches the model as
  ``return_schema`` through ``get_tool_info``/``tool_specification``, so
  publishing a live one would let a server write arbitrary text into the
  agent's context without review.

Only drift that cannot invalidate the reviewed contract is tolerated:

* documentation-only edits (``description``, ``title``, ``examples`` ...)
* newly added *optional* input properties

Anything else -- a new required field, a removed or retyped property, a
tightened constraint, a restructured output -- disables that one tool until a
maintainer reviews the diff. When in doubt this module says "not compatible",
because the cost of a false reject is the status quo while the cost of a false
accept is a broken call or an unreviewed contract.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Keys that carry no constraint: they cannot make a previously valid request
# invalid, so a change confined to them is documentation, not interface. They
# are only ever stripped from a *schema object*, never from a map whose keys are
# property names -- a property legitimately called "description" must still be
# compared like any other.
_DOCUMENTATION_KEYS = {
    "description",
    "title",
    "examples",
    "$comment",
    "deprecated",
    "readOnly",
    "writeOnly",
}

# Keywords whose value is a map of NAME -> schema.
_SCHEMA_MAPS = {
    "properties",
    "patternProperties",
    "$defs",
    "definitions",
    "dependentSchemas",
}

# Keywords whose value is a single nested schema.
_NESTED_SCHEMA = {
    "items",
    "additionalItems",
    "additionalProperties",
    "unevaluatedProperties",
    "unevaluatedItems",
    "contains",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
}

# Keywords whose value is a list of nested schemas.
_SCHEMA_LISTS = {"allOf", "anyOf", "oneOf", "prefixItems"}

_LOCKFILE = Path(__file__).resolve().parent / "data" / "mcp_contracts.lock.json"

_MISSING = object()
_lockfile_cache: Any = _MISSING


def _read_lockfile() -> Dict[str, Any]:
    global _lockfile_cache
    if _lockfile_cache is _MISSING:
        try:
            parsed = json.loads(_LOCKFILE.read_text())
        except (OSError, ValueError):
            parsed = {}
        _lockfile_cache = parsed if isinstance(parsed, dict) else {}
    return _lockfile_cache


def load_reviewed_contracts(loader_name: str) -> Dict[str, Dict[str, Any]]:
    """Reviewed contracts for one loader, keyed by tool name.

    Returns an empty mapping when the lockfile is absent, unreadable or not
    shaped as expected; callers then keep the strict hash-only behaviour that
    shipped before the lockfile existed. A malformed record must never take down
    a whole category, so every level is type-checked rather than trusted.
    """
    loaders = _read_lockfile().get("loaders")
    if not isinstance(loaders, dict):
        return {}
    entry = loaders.get(loader_name)
    if not isinstance(entry, dict):
        return {}
    tools = entry.get("tools")
    if not isinstance(tools, dict):
        return {}
    return {
        name: record["contract"]
        for name, record in tools.items()
        if isinstance(record, dict) and isinstance(record.get("contract"), dict)
    }


def _values_equal(reviewed: Any, live: Any) -> bool:
    """Exact comparison that does not conflate ``True`` with ``1``."""
    if type(reviewed) is not type(live):
        return False
    if isinstance(reviewed, dict):
        return set(reviewed) == set(live) and all(
            _values_equal(reviewed[key], live[key]) for key in reviewed
        )
    if isinstance(reviewed, list):
        return len(reviewed) == len(live) and all(
            _values_equal(a, b) for a, b in zip(reviewed, live)
        )
    return reviewed == live


def _schemas_equal(reviewed: Any, live: Any) -> bool:
    """Compare two schema objects, ignoring purely documentary keywords."""
    if not isinstance(reviewed, dict) or not isinstance(live, dict):
        return _values_equal(reviewed, live)

    reviewed_keys = {k for k in reviewed if k not in _DOCUMENTATION_KEYS}
    live_keys = {k for k in live if k not in _DOCUMENTATION_KEYS}
    if reviewed_keys != live_keys:
        return False

    for key in reviewed_keys:
        left, right = reviewed[key], live[key]
        if key in _SCHEMA_MAPS:
            if not isinstance(left, dict) or not isinstance(right, dict):
                if not _values_equal(left, right):
                    return False
            elif set(left) != set(right) or not all(
                _schemas_equal(left[name], right[name]) for name in left
            ):
                return False
        elif key in _NESTED_SCHEMA:
            if not _schemas_equal(left, right):
                return False
        elif key in _SCHEMA_LISTS:
            if not isinstance(left, list) or not isinstance(right, list):
                return False
            if len(left) != len(right) or not all(
                _schemas_equal(a, b) for a, b in zip(left, right)
            ):
                return False
        elif not _values_equal(left, right):
            return False
    return True


def input_drift_reasons(
    reviewed: Optional[Dict[str, Any]], live: Optional[Dict[str, Any]]
) -> List[str]:
    """Why the reviewed call would no longer be valid; empty means tolerable."""
    if not isinstance(reviewed, dict) or not isinstance(live, dict):
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
    if isinstance(reviewed_props, dict) and isinstance(live_props, dict):
        for name, reviewed_sub in reviewed_props.items():
            if name not in live_props:
                reasons.append(f"{name!r} no longer accepted")
            elif not _schemas_equal(reviewed_sub, live_props[name]):
                reasons.append(f"{name!r} changed shape")
    elif not _values_equal(reviewed_props, live_props):
        reasons.append("'properties' changed shape")

    # Everything outside properties/required -- additionalProperties, type,
    # allOf, dependentRequired ... -- must be untouched. Added *optional*
    # properties are the deliberate exception and are simply never sent.
    ignored = {"properties", "required"} | _DOCUMENTATION_KEYS
    for key in sorted((set(reviewed) | set(live)) - ignored):
        if not _schemas_equal({key: reviewed.get(key)}, {key: live.get(key)}):
            reasons.append(f"schema keyword {key!r} changed")

    return reasons


def output_drift_reasons(
    reviewed: Optional[Dict[str, Any]], live: Optional[Dict[str, Any]]
) -> List[str]:
    """Why the reviewed output contract no longer describes the live one.

    Checked even though a tolerated tool publishes the *reviewed* output schema,
    because a restructured response would then fail validation in
    ``MCPProxyTool._normalize_result``. Documentation-only edits are ignored
    here exactly as for input -- and because the reviewed text is what ships, a
    server cannot use them to write into the agent's context.
    """
    if reviewed is None and live is None:
        return []
    if not _schemas_equal(reviewed, live):
        return ["output schema changed shape"]
    return []


def classify(
    reviewed_contract: Optional[Dict[str, Any]], live_tool: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Return (tolerable, reasons) for one tool's drift.

    ``tolerable`` means the reviewed contract still works against the live
    server, so the tool can keep running on it. It is not a statement that the
    change itself is benign -- that judgement stays with a human reviewing the
    CI diff.
    """
    if not reviewed_contract:
        # The hash already told us it moved; without a recorded schema there is
        # nothing to compare it against, so it cannot be assessed as tolerable.
        return False, ["contract changed, and no reviewed schema is recorded"]

    if reviewed_contract.get("name") != live_tool.get("name"):
        return False, ["tool name changed"]

    reasons = input_drift_reasons(
        reviewed_contract.get("inputSchema"), live_tool.get("inputSchema")
    )
    reasons += output_drift_reasons(
        reviewed_contract.get("outputSchema"), live_tool.get("outputSchema")
    )
    return (not reasons), reasons


def pinned_tool_from_reviewed(
    reviewed_contract: Dict[str, Any], live_tool: Dict[str, Any]
) -> Dict[str, Any]:
    """Build the tool to publish when tolerating compatible drift.

    Both schemas come from the reviewed contract, never the live one. The agent
    fills in any parameter a server advertises, so a live *input* schema would
    turn an added field into an unreviewed way for data to leave the session;
    and the *output* schema reaches the model as ``return_schema``, so a live
    one would let a server write unreviewed text into the agent's context. The
    drift is tolerable by construction, so the reviewed contract still matches
    what the server accepts and returns.

    Publishing the reviewed contract unchanged also keeps ``contract_sha256``
    honest: the hash stamped on the proxy is the hash that was reviewed.
    """
    pinned = copy.deepcopy(live_tool)
    pinned["inputSchema"] = copy.deepcopy(reviewed_contract.get("inputSchema"))
    if reviewed_contract.get("outputSchema") is None:
        pinned.pop("outputSchema", None)
    else:
        pinned["outputSchema"] = copy.deepcopy(reviewed_contract["outputSchema"])
    return pinned
