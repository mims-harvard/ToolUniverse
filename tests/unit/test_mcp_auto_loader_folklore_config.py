import json
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
        "c221b7142324feadfab11242c05af17eb98b8fe4a5a7df3a666dec90ed50a7eb"
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
