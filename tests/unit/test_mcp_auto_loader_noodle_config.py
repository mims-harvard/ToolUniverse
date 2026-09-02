import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files


EXPECTED_HASHES = {
    "search_biomedical_literature": (
        "7f9ccd9ddaa845f2e412116ef322b5dc571f767b75ee6b8c346e8e256913f368"
    ),
    "get_publication_details": (
        "640e336c39dc047c7b56854f27d6acfe1293a130529ff633de5d0efb5e35fde0"
    ),
    "get_work_details": (
        "6ae98c93cd0ba0878b2d1f7b07ee082f2a94fb0062ca7a92cfdaa25f4274a14d"
    ),
    "get_publication_neighborhood": (
        "31cc91ee94d10ad4eb112b34ff0b36e14fdb3867c87f9da980e942c0918c3875"
    ),
    "get_work_neighborhood": (
        "7b0c25725c1c7c7ef848725923d59e59cdaa4231be999e3edf7b56cf312081bd"
    ),
    "get_corpus_summary": (
        "cf03aed706e344baa94da5ff1aa1e7fc0827d23c6e10ec8ebb8e9cf43bf8a590"
    ),
}


def test_noodle_loader_is_opt_in_allowlisted_and_contract_pinned():
    config_path = Path(default_tool_files["mcp_auto_loader_noodle"])
    config = json.loads(config_path.read_text())[0]
    contracts = {item["name"]: item for item in config["tool_contracts"]}

    assert config["server_url"] == "${NOODLE_MCP_URL}"
    assert config["required_api_keys"] == ["NOODLE_MCP_URL"]
    assert config["tool_prefix"] == "noodle_"
    assert config["strict_tool_contracts"] is True
    assert config["normalize_mcp_result"] is True
    assert config["require_structured_content"] is True
    assert config["selected_tools"] == list(EXPECTED_HASHES)
    assert {
        name: item["contract_sha256"] for name, item in contracts.items()
    } == EXPECTED_HASHES
    assert all(item["annotations"]["readOnlyHint"] for item in contracts.values())
    assert all(not item["annotations"]["destructiveHint"] for item in contracts.values())


def test_noodle_loader_copy_preserves_discovery_and_data_boundaries():
    config_path = Path(default_tool_files["mcp_auto_loader_noodle"])
    config = json.loads(config_path.read_text())[0]
    copy = " ".join(
        [config["description"]]
        + [item["description"] for item in config["tool_contracts"]]
        + [config["parameter"]["properties"]["tool_arguments"]["description"]]
    ).lower()

    for phrase in (
        "helena bioinformatics",
        "pubmed-derived",
        "citation",
        "semantic",
        "provenance",
        "not evidence of causality",
        "not diagnosis",
        "patient",
        "private case",
    ):
        assert phrase in copy
