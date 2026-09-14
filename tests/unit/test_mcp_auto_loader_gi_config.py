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
    "store_inline_sequence": "434f38f220ce4be8a15ec81b9e0fc6ef14f5fff45e871fd18ec4ec372b22a097",
    "predict_promoter": "eccb902b11415f3189e1caa604f018cb0356ab32625572c168f68242b6a4cc58",
    "predict_splice": "5af1ca0fd53975ec26639de3e41f40068b8ee67ce8b8e0c538348d5f43ec63ec",
    "predict_enhancer": "31764dbf1037225a1d6895f49b3715204f76ced412c343d8e5f1cef77f3be391",
    "predict_chromatin": "23fde61976ec60cd1e33c88b2c94624e168a14fc5c7314cf61555d4f2d5f8c85",
    "predict_expression": "41b8c67d2d1a022ea3b6c043eb8161d54685d60a4eca82a14f4cfcb84eb7e2ce",
    "find_genes": "2fded6f0f98cf1661b8775f623e83ecd2792e148c88db6a62013a9a560cbc2b8",
    "find_genes_and_predict_expression": "42681714a809d268bb89453ce49ec0db3d56a06b1e539c07840e75edf2fda8c5",
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
