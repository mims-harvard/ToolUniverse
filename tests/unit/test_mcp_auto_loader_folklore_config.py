import json
import re
from pathlib import Path

from tooluniverse.default_config import default_tool_files

EXPECTED_TOOLS = {
    "classify_germline_variant",
    "search_variant_literature",
    "get_publication_details",
    "search_literature_corpus",
}

EXPECTED_CONTRACT_HASHES = {
    "classify_germline_variant": (
        "800325ed81610b42dd876d0542d8169105b03acf3704f9c89ba2597272c983ad"
    ),
    "search_variant_literature": (
        "820a415743aa7338dc2bf2d27d9d2e3d320c878852ace63a1d44c1f66e9e953d"
    ),
    "get_publication_details": (
        "da2941fbfe688fa2c9cc5f0046fa9be4b8f9f7a08bf5924895f3f3c8b79cee5d"
    ),
    "search_literature_corpus": (
        "34b4eba562a9bb39b91792eac6a4e9da447b37696a3133bbe754ab46833f5035"
    ),
}


def test_folklore_loader_is_opt_in_allowlisted_and_contract_pinned():
    config_path = Path(default_tool_files["mcp_auto_loader_folklore"])
    config = json.loads(config_path.read_text())[0]

    assert config["server_url"] == "${FOLKLORE_MCP_URL}"
    assert config["required_api_keys"] == ["FOLKLORE_MCP_URL"]
    assert config["tool_prefix"] == "folklore_"
    assert config["timeout"] == 30
    assert set(config["selected_tools"]) == EXPECTED_TOOLS
    assert len(config["selected_tools"]) == len(EXPECTED_TOOLS)
    assert config["strict_tool_contracts"] is True
    assert config["normalize_mcp_result"] is True
    assert config["require_structured_content"] is True
    assert config["mcp_structured_error_field"] == "adapter_error"
    assert "authentication" in config["api_key_info"]["FOLKLORE_MCP_URL"]["without"]

    contracts = {contract["name"]: contract for contract in config["tool_contracts"]}
    assert set(contracts) == EXPECTED_TOOLS
    assert {
        name: contract["contract_sha256"] for name, contract in contracts.items()
    } == EXPECTED_CONTRACT_HASHES
    assert all(
        contract["annotations"]["readOnlyHint"] for contract in contracts.values()
    )
    assert all(
        not contract["annotations"]["destructiveHint"]
        for contract in contracts.values()
    )
    assert (
        "professional review" in contracts["classify_germline_variant"]["description"]
    )
    assert contracts["classify_germline_variant"]["title"] == (
        "Classify or interpret a germline variant under ACMG/AMP"
    )
    for trigger in (
        "pathogenicity",
        "VUS",
        "ClinVar assertions",
        "population-frequency evidence",
        "resolve a variant notation",
    ):
        assert trigger in contracts["classify_germline_variant"]["description"]
    assert "do not change" in contracts["search_variant_literature"]["description"]
    assert "no patient context" in contracts["get_publication_details"]["description"]
    assert "professional review" in contracts["search_literature_corpus"]["description"]


def test_folklore_loader_copy_preserves_clinical_and_data_boundaries():
    config_path = Path(default_tool_files["mcp_auto_loader_folklore"])
    config = json.loads(config_path.read_text())[0]
    copy = " ".join(
        [config["description"]]
        + [contract["description"] for contract in config["tool_contracts"]]
        + [
            config["parameter"]["properties"]["tool_arguments"]["description"],
        ]
    ).lower()

    assert "helena bioinformatics" in copy
    assert "patient" in copy
    assert "private case" in copy
    assert "not diagnoses" in copy
    assert "treatment recommendation" in copy
    assert "ambiguous" in copy


def _pinned_contract_versions():
    """The `contract_version` const each reviewed tool's own outputSchema declares.

    Only the root of the schema is read: `anyOf` branches each carry their own
    copy, and nested definitions carry a different field -- search_variant_literature's
    $defs/LiteratureAuthorityResponse pins contract_version "1.0", and every tool's
    result.search_contract_version is "1.0" as well. Neither is the envelope version
    this looks for.
    """
    lock = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "src"
            / "tooluniverse"
            / "data"
            / "mcp_contracts.lock.json"
        ).read_text()
    )
    tools = lock["loaders"]["mcp_auto_loader_folklore"]["tools"]
    found = {}
    for name, entry in tools.items():
        schema = entry["contract"]["outputSchema"]
        roots = schema.get("anyOf") or [schema]
        versions = {
            root["properties"]["contract_version"]["const"]
            for root in roots
            if "const" in (root.get("properties", {}).get("contract_version") or {})
        }
        if versions:
            found[name] = versions
    return found


def test_the_live_test_asserts_the_envelope_version_the_lockfile_pins():
    """Tie the live test to the pin, which is what nothing did before.

    The live test is marked `network` and CI deselects it, so when Folklore moved
    its envelope from 1 to 2 the stale assertion sat there unnoticed: the pinned
    contract said "2" while the test still demanded "1", and the first thing to
    notice was a hand-run of the test months later. This check runs offline, in
    CI, on every push.
    """
    pinned = _pinned_contract_versions()
    assert pinned, "no tool's pinned outputSchema declares a contract_version const"
    declared = {v for versions in pinned.values() for v in versions}
    assert len(declared) == 1, (
        f"the reviewed tools pin disagreeing envelope versions: {pinned}"
    )

    live_test = (
        Path(__file__).resolve().parents[1]
        / "integration"
        / "test_mcp_auto_loader_folklore_live.py"
    ).read_text()
    asserted = set(
        re.findall(r'structured\["contract_version"\] == "([^"]+)"', live_test)
    )
    assert asserted == declared, (
        f"the live test asserts contract_version {asserted} but the lockfile pins "
        f"{declared}; one of the two is describing a server that no longer answers "
        "that way"
    )
