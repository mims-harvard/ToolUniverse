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


def test_genomic_intelligence_loader_is_opt_in_and_allowlisted():
    config_path = Path(default_tool_files["mcp_auto_loader_gi"])
    config = json.loads(config_path.read_text())[0]

    assert config["server_url"] == "${GENOMIC_INTELLIGENCE_MCP_URL}"
    assert config["required_api_keys"] == ["GENOMIC_INTELLIGENCE_MCP_URL"]
    assert config["timeout"] == 30
    assert set(config["selected_tools"]) == EXPECTED_TOOLS
    assert len(config["selected_tools"]) == len(EXPECTED_TOOLS)
