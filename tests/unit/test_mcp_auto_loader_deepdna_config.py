import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files

DATA = Path(default_tool_files["mcp_auto_loader_deepdna"]).parent

EXPECTED_HASHES = {
    "list_genes": ("fc88b7626436a6c6146ff8a94ba79359cac2da2684cd987acb1580807306080b"),
    "lookup_gene": ("b3cd62c3304fe380a17a2d848064245067143ef807bbbba6530c839b65885ef7"),
    "lookup_variant": (
        "fb90e4701110830f0ae5ba1b5fbf463e03e5cf8d28c9d8b2ef5c434743a43823"
    ),
    "lookup_drug_gene": (
        "3aa9d82cbd0db2404c6d459516ac7e2ce76791727f70f2e665fa259c650e8e26"
    ),
    "check_medications": (
        "4d633d038d68af170ebed8bfdb7112c899e671b2b247c5ac428e1561954c3b7b"
    ),
}


def _config():
    config_path = Path(default_tool_files["mcp_auto_loader_deepdna"])
    return json.loads(config_path.read_text())[0]


def test_deepdna_loader_is_opt_in_allowlisted_and_contract_pinned():
    config = _config()
    contracts = {item["name"]: item for item in config["tool_contracts"]}

    assert config["server_url"] == "${DEEPDNA_MCP_URL}"
    assert config["required_api_keys"] == ["DEEPDNA_MCP_URL"]
    assert "optional_api_keys" not in config
    assert "http_headers_from_env" not in config
    assert config["tool_prefix"] == "deepdna_"
    assert config["strict_tool_contracts"] is True
    assert config["selected_tools"] == list(EXPECTED_HASHES)
    assert {
        name: item["contract_sha256"] for name, item in contracts.items()
    } == EXPECTED_HASHES
    assert all(item["annotations"]["readOnlyHint"] for item in contracts.values())
    assert all(
        not item["annotations"]["destructiveHint"] for item in contracts.values()
    )


def test_deepdna_reviewed_inputs_take_no_genotype():
    """The reviewed tools take gene symbols, rsIDs and drug names only, and
    refuse undeclared arguments, so no field exists for a genotype."""
    lock = json.loads((DATA / "mcp_contracts.lock.json").read_text())
    tools = lock["loaders"]["mcp_auto_loader_deepdna"]["tools"]

    assert sorted(tools) == sorted(EXPECTED_HASHES)
    for name, record in tools.items():
        schema = record["contract"]["inputSchema"]
        assert schema.get("additionalProperties") is False, name
        assert not {
            field for field in schema.get("properties", {}) if "genotype" in field
        }, name


def test_deepdna_loader_normalizes_without_requiring_structured_content():
    """Successful calls return structuredContent; a miss (unknown gene, rsID or
    drug) or an undeclared argument returns isError with plain text, so
    structuredContent is used when present but not required."""
    config = _config()

    assert config["normalize_mcp_result"] is True
    assert config.get("require_structured_content") is not True
