import copy
import json
from pathlib import Path

import pytest

from tooluniverse.default_config import default_tool_files
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool


PUBLIC_ENDPOINT = "https://api.helena.bio/noodle/v1/mcp"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.mcp
@pytest.mark.asyncio
async def test_noodle_reviewed_tools_match_live_contract_and_return_boundaries():
    config_path = Path(default_tool_files["mcp_auto_loader_noodle"])
    config = copy.deepcopy(json.loads(config_path.read_text())[0])
    config["server_url"] = PUBLIC_ENDPOINT

    loader = MCPAutoLoaderTool(config)
    tools = await loader.discover_tools()

    assert list(tools) == config["selected_tools"]
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools.values())

    response = await loader.call_tool("get_corpus_summary", {})
    structured = response["structuredContent"]
    assert structured["contract_version"] == "1.0"
    assert structured["counts"]["unique_works"] > 0
    assert structured["sources"]
    assert "PubMed" in structured["scope"]
