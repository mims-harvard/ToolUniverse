import json
from pathlib import Path

from tooluniverse.default_config import default_tool_files


EXPECTED_TOOLS = {
    "list_models",
    "fetch_ensembl_sequence",
    "fetch_region",
    "fetch_gene_for_expression",
    "load_demo_sequence",
    "store_inline_sequence",
    "predict_promoter",
    "predict_splice",
    "predict_enhancer",
    "predict_chromatin",
    "predict_expression",
    "find_genes",
    "find_genes_and_predict_expression",
    "get_job",
    "list_jobs",
}

EXPECTED_CONTRACT_HASHES = {
    "list_models": "c3eb2b1b9be3a8192678dfbeb8c779a18564a4a2b6eea9792dbf09b2d7cb12dc",
    "fetch_ensembl_sequence": "ed1bf8d5b85881be6fd006b05236e5bfd4792fe60dd887c71ee86d10df4f47d4",
    "fetch_region": "781ae336e78ebb2e34e86313486a3a6617663bd7ea2e093c8f9cbb2ef4a525f9",
    "fetch_gene_for_expression": "19fac5803426ee310184ec38d9165c5d26e7b1b57d0840152811886c0ee6904f",
    "load_demo_sequence": "32fc312cf02faf55825d9f09aac3050edf5c279dd1883a5cff6d8199dd12f1b3",
    "store_inline_sequence": "54fa131fff438454071f7cd782cd9ace1c056523a385150a3b1f430c0178bdb9",
    "predict_promoter": "d9f5db6952f9f62bf34d9d5504a2b91886a6ea850791a53e7858e03be4f7ef05",
    "predict_splice": "3077a2a04af23489c3fc9166e19f1c28954f3e014eb57c6a21eb959fa5a86f4d",
    "predict_enhancer": "c6feb5fc03d3bae22213125833954256a63c807fcfe71149d68fb5484eb2fce2",
    "predict_chromatin": "580cfb99c06b8e1cd67353ac223739d5489badbae800d9822c20982f79409a39",
    "predict_expression": "ed6dd0cfb42e2e233baf750a3b4e5d2207329ba9367cefbe57fefc2e38dcfc56",
    "find_genes": "a3c71dbc2873a4af431def60c83f5eacb483ac7a8cbbc0800bf6b0c9acf68777",
    "find_genes_and_predict_expression": "0546d4ef54ce01e0c9ac5e4568ec884a7effd7452913fb735b414d2bf004147b",
    "get_job": "673945815b6c49bdb1b8bf93bbb27924692e95b56cd3881bd88060ced4601c6e",
    "list_jobs": "d99827e20992a088a4c659e3329161318feea9240de56a1519b34ec4b6c0394f",
}


def test_genomic_intelligence_loader_is_opt_in_and_allowlisted():
    config_path = Path(default_tool_files["mcp_auto_loader_gi"])
    config = json.loads(config_path.read_text())[0]

    assert config["server_url"] == "${GENOMIC_INTELLIGENCE_MCP_URL}"
    assert config["required_api_keys"] == ["GENOMIC_INTELLIGENCE_MCP_URL"]
    assert config["timeout"] == 90
    assert set(config["selected_tools"]) == EXPECTED_TOOLS
    assert len(config["selected_tools"]) == len(EXPECTED_TOOLS)
    assert config["strict_tool_contracts"] is True
    assert config["normalize_mcp_result"] is True
    assert config["require_structured_content"] is True
    assert config["mcp_structured_error_field"] == "error"
    assert config["http_headers_from_env"] == {
        "X-GI-Key": {"env": "GENOMIC_INTELLIGENCE_API_KEY"}
    }
    assert config["optional_api_keys"] == ["GENOMIC_INTELLIGENCE_API_KEY"]

    contracts = {contract["name"]: contract for contract in config["tool_contracts"]}
    assert set(contracts) == EXPECTED_TOOLS
    assert {
        name: contract["contract_sha256"] for name, contract in contracts.items()
    } == EXPECTED_CONTRACT_HASHES
    assert all("description" in contract for contract in contracts.values())
    assert all("annotations" in contract for contract in contracts.values())
    assert "private" in contracts["store_inline_sequence"]["description"]
    assert "third-party" in contracts["store_inline_sequence"]["description"]
