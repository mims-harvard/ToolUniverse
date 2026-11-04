import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files

EXPECTED_HASHES = {
    "search_papers": (
        "732f06115e7d0ab47875a73c396241a60cde0835c83b989888ca8240fe2c3a79"
    ),
    "get_paper": ("ecc1046c974a86bc0bfaf65c74c1292e058a62d9685209b24461e124bdf5a9ca"),
    "list_stories": (
        "cff4c45648b6eebe2f8250e99ef19204a42d8f945b819035facbb5772306d471"
    ),
    "find_entities": (
        "a3364a8905c6c3f0ba0e0a6e3034ad679059cdc2f4ceac34dc956b0872bb1f27"
    ),
    "get_entity": ("bc530f71bfdcef8fc0907129c266d8bead18b17bd98afa3b01c689bef3f467a9"),
    "list_claims": ("13442c354494c6e6c43017a277ccf3c04d14e828ca23672c2c7c719e35d4ccd9"),
    "list_trials": ("145be7b1695ebe65fc6c4ccf16ee555db00a0f09a673ff12b2c439a654f10817"),
    "list_grants": ("f508b96b6f90e053cb677cf5f1bbf0afdef4237cb1d523ac9ccf945bc47bb24e"),
    "list_assets": ("9d8307cfaf5f5ff3297e1db3212dce611173bc4910455676e89bb416b18a614f"),
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
