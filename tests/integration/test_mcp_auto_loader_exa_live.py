import copy
import json
from pathlib import Path

import pytest

from tooluniverse.default_config import default_tool_files
from tooluniverse.mcp_client_tool import MCPAutoLoaderTool, _unwrap_mcp_tool_result

PUBLIC_ENDPOINT = "https://mcp.exa.ai/mcp"


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.mcp
@pytest.mark.asyncio
async def test_exa_reviewed_tools_match_live_contract_and_return_readable_text():
    config_path = Path(default_tool_files["mcp_auto_loader_exa"])
    config = copy.deepcopy(json.loads(config_path.read_text())[0])
    config["server_url"] = PUBLIC_ENDPOINT

    loader = MCPAutoLoaderTool(config)
    tools = await loader.discover_tools()

    assert list(tools) == config["selected_tools"]
    assert all(tool["annotations"]["readOnlyHint"] for tool in tools.values())

    response = await loader.call_tool(
        "web_search_exa", {"query": "CRISPR gene editing", "numResults": 1}
    )
    assert not response.get("isError")
    result = _unwrap_mcp_tool_result(response)
    assert isinstance(result, str)
    assert "URL:" in result
