import copy
import json
from pathlib import Path

import pytest

from tooluniverse.default_config import default_tool_files
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool

PUBLIC_ENDPOINT = "https://deepdna.ai/mcp"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.mcp
@pytest.mark.asyncio
async def test_deepdna_reviewed_tools_match_live_contract_and_return_a_pair():
    config_path = Path(default_tool_files["mcp_auto_loader_deepdna"])
    config = copy.deepcopy(json.loads(config_path.read_text())[0])
    config["server_url"] = PUBLIC_ENDPOINT

    loader = MCPAutoLoaderTool(config)
    tools = await loader.discover_tools()

    assert list(tools) == config["selected_tools"]
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools.values())

    response = await loader.call_tool(
        "lookup_drug_gene", {"gene": "CYP2C19", "drug": "clopidogrel"}
    )
    assert not response.get("isError")
    pair = response["structuredContent"]["pair"]
    assert pair["gene"] == "CYP2C19" and pair["drug"] == "clopidogrel"
    assert pair["sources"]
