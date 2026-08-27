import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files

EXPECTED_TOOLS = {
    "search_variant_evidence",
    "search_variant_literature",
    "get_publication_details",
    "search_literature_corpus",
}

EXPECTED_CONTRACT_HASHES = {
    "search_variant_evidence": (
        "7a537fea79ae459ada1ef188e0b84147b35aead716295b423a0d8c7173e5d42f"
    ),
    "search_variant_literature": (
        "999ec1ddb4ea413fe8a22df866086e0fa94f5e5f8027e6fbb6a1faabb38174d8"
    ),
    "get_publication_details": (
        "7f91cb6ac7c93b9a59116ab81aa74620b9eff248a66a29da2c0e3847c4f9017b"
    ),
    "search_literature_corpus": (
        "1bcff02b31b1b92ac225b3869e01089fa82f3cc3395c4659a327fd90373ed05d"
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
    assert "professional review" in contracts["search_variant_evidence"]["description"]
    assert contracts["search_variant_evidence"]["title"] == (
        "Classify or interpret a germline variant under ACMG/AMP"
    )
    for trigger in (
        "pathogenicity",
        "VUS",
        "ClinVar assertions",
        "population-frequency evidence",
        "resolve a variant notation",
    ):
        assert trigger in contracts["search_variant_evidence"]["description"]
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
