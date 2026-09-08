import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files

EXPECTED_HASHES = {
    "web_search_exa": (
        "3bd880d7e5c7f2110eaf5c1d08dee4b02cf95e27d6b944c7af5275c682e1ab64"
    ),
    "web_fetch_exa": (
        "c52bc77073c7d3ba0fcc0f08e3bd2a0e90fd2327d50f64ad765e9549194e1dd0"
    ),
}


def test_exa_loader_is_opt_in_allowlisted_and_contract_pinned():
    config_path = Path(default_tool_files["mcp_auto_loader_exa"])
    config = json.loads(config_path.read_text())[0]
    contracts = {item["name"]: item for item in config["tool_contracts"]}

    assert config["server_url"] == "${EXA_MCP_URL}"
    assert config["required_api_keys"] == ["EXA_MCP_URL"]
    assert config["optional_api_keys"] == ["EXA_API_KEY"]
    assert config["tool_prefix"] == "exa_"
    assert config["strict_tool_contracts"] is True
    assert config["selected_tools"] == list(EXPECTED_HASHES)
    assert {
        name: item["contract_sha256"] for name, item in contracts.items()
    } == EXPECTED_HASHES
    assert all(item["annotations"]["readOnlyHint"] for item in contracts.values())
    assert all(
        not item["annotations"]["destructiveHint"] for item in contracts.values()
    )


def test_exa_loader_does_not_require_structured_content():
    """Exa's public MCP server returns plain-text content, not structuredContent
    (verified live) — requiring it would make every call fail with 'did not
    return required structuredContent'."""
    config_path = Path(default_tool_files["mcp_auto_loader_exa"])
    config = json.loads(config_path.read_text())[0]

    assert config.get("normalize_mcp_result") is not True
    assert config.get("require_structured_content") is not True


def test_exa_loader_optional_api_key_lifts_rate_limit_via_header():
    config_path = Path(default_tool_files["mcp_auto_loader_exa"])
    config = json.loads(config_path.read_text())[0]

    assert config["http_headers_from_env"]["x-api-key"]["env"] == "EXA_API_KEY"
