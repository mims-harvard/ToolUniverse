import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files

EXPECTED_HASHES = {
    "search_papers": (
        "f6513ebc66f1782538c832553cdd12e11a7451a60e5202c67ae9047cccc65425"
    ),
    "get_paper": ("82a8d636bf37353c187ed8d1b3b25eec2fccc63fbc47020dfec7879888e3f6a7"),
    "list_stories": (
        "cff4c45648b6eebe2f8250e99ef19204a42d8f945b819035facbb5772306d471"
    ),
    "find_entities": (
        "a3364a8905c6c3f0ba0e0a6e3034ad679059cdc2f4ceac34dc956b0872bb1f27"
    ),
    "get_entity": ("bc530f71bfdcef8fc0907129c266d8bead18b17bd98afa3b01c689bef3f467a9"),
    "list_claims": ("02d89349b20cd93065af22e75be77326afb9220e7483a9be6cc1583824c20f81"),
    "list_trials": ("145be7b1695ebe65fc6c4ccf16ee555db00a0f09a673ff12b2c439a654f10817"),
    "list_grants": ("5728b9e49f29039ae230d50c629d232cc33c7d838ca75b72ea1b881d027a3400"),
    "list_assets": ("cc20889b812294ba5e023a5c6dec53702226493c38a428788f76f75771492e64"),
}


def _config():
    config_path = Path(default_tool_files["mcp_auto_loader_agingresearch"])
    return json.loads(config_path.read_text())[0]


def test_agingresearch_loader_is_opt_in_allowlisted_and_contract_pinned():
    config = _config()
    contracts = {item["name"]: item for item in config["tool_contracts"]}

    assert config["server_url"] == "${AGINGRESEARCH_MCP_URL}"
    assert config["required_api_keys"] == ["AGINGRESEARCH_MCP_URL"]
    assert config["optional_api_keys"] == ["AGINGRESEARCH_API_KEY"]
    assert config["tool_prefix"] == "agingresearch_"
    assert config["strict_tool_contracts"] is True
    assert config["selected_tools"] == list(EXPECTED_HASHES)
    assert {
        name: item["contract_sha256"] for name, item in contracts.items()
    } == EXPECTED_HASHES
    assert all(item["annotations"]["readOnlyHint"] for item in contracts.values())
    assert all(
        not item["annotations"]["destructiveHint"] for item in contracts.values()
    )


def test_agingresearch_loader_pins_no_account_or_write_tools():
    """Follows, Ask and the user's own lists need a signed-in account and act on
    it; only signed-out, read-only lookups are allowlisted."""
    selected = set(_config()["selected_tools"])

    assert not selected & {
        "follow",
        "unfollow",
        "list_follows",
        "list_questions",
        "ask_arn",
        "start_ultradeep",
        "get_ask_answer",
    }


def test_agingresearch_loader_normalizes_without_requiring_structured_content():
    """Successful calls return structuredContent; argument errors come back as
    isError with plain text, so structuredContent is used when present but not
    required."""
    config = _config()

    assert config["normalize_mcp_result"] is True
    assert config.get("require_structured_content") is not True


def test_agingresearch_loader_optional_api_key_is_a_bearer_token():
    header = _config()["http_headers_from_env"]["Authorization"]

    assert header == {"env": "AGINGRESEARCH_API_KEY", "prefix": "Bearer "}
