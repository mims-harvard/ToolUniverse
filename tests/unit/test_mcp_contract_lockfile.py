"""The lockfile must stay an accurate record of every pinned MCP contract.

A pin stored only as a hash can show *that* an upstream server changed a tool
but never *what* changed, which leaves a maintainer asked to re-pin nothing to
review. These guard the recorded schemas that make that review possible.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
LOCKFILE = DATA / "mcp_contracts.lock.json"


def _pinned_loaders():
    for path in sorted(DATA.glob("mcp_auto_loader_*.json")):
        for config in json.loads(path.read_text()):
            if config.get("strict_tool_contracts"):
                yield config


def _lock():
    return json.loads(LOCKFILE.read_text())["loaders"]


def test_every_pinned_tool_has_a_recorded_contract():
    lock = _lock()
    missing = [
        f"{config['name']}/{contract['name']}"
        for config in _pinned_loaders()
        for contract in config["tool_contracts"]
        if contract["name"] not in lock.get(config["name"], {}).get("tools", {})
    ]
    assert not missing, (
        "pinned in a loader config but absent from the lockfile: "
        f"{missing}. Run scripts/sync_mcp_contracts.py --update"
    )


def test_recorded_schemas_hash_to_the_pinned_contract_sha256():
    """The lockfile and the config cannot be allowed to disagree.

    If they drift apart the lockfile stops describing what is actually
    enforced, and the diff a reviewer reads becomes fiction.
    """
    lock = _lock()
    mismatched = []
    for config in _pinned_loaders():
        recorded = lock.get(config["name"], {}).get("tools", {})
        for contract in config["tool_contracts"]:
            entry = recorded.get(contract["name"])
            if entry is None:
                continue
            actual = MCPAutoLoaderTool._contract_sha256(entry["contract"])
            if actual != contract["contract_sha256"]:
                mismatched.append(
                    f"{config['name']}/{contract['name']}: config says "
                    f"{contract['contract_sha256'][:12]}, recorded schema hashes "
                    f"to {actual[:12]}"
                )
    assert not mismatched, mismatched


def test_lockfile_records_no_tool_that_is_not_pinned():
    lock = _lock()
    pinned = {
        config["name"]: {c["name"] for c in config["tool_contracts"]}
        for config in _pinned_loaders()
    }
    extra = [
        f"{loader}/{tool}"
        for loader, entry in lock.items()
        for tool in entry.get("tools", {})
        if tool not in pinned.get(loader, set())
    ]
    assert not extra, f"recorded but not pinned in any config: {extra}"


def test_recorded_contracts_carry_the_schemas_not_just_a_hash():
    """The point of the lockfile is the schema; a hash alone is not reviewable."""
    for loader, entry in _lock().items():
        for tool, record in entry["tools"].items():
            contract = record["contract"]
            assert contract["name"] == tool, f"{loader}/{tool}: name mismatch"
            assert isinstance(contract["inputSchema"], dict), (
                f"{loader}/{tool}: inputSchema must be recorded so drift is diffable"
            )
            assert "outputSchema" in contract, f"{loader}/{tool}: outputSchema missing"


def test_every_pinned_loader_has_an_endpoint_for_the_drift_check():
    """A loader with no endpoint is silently never checked for drift."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sync_mcp_contracts",
        Path(__file__).resolve().parents[2] / "scripts" / "sync_mcp_contracts.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    unmapped = [
        config["name"]
        for config in _pinned_loaders()
        if config["name"] not in module.MCP_ENDPOINTS
    ]
    assert not unmapped, (
        f"contract-pinned loaders with no endpoint in MCP_ENDPOINTS: {unmapped}. "
        "They would never be checked for upstream drift."
    )
