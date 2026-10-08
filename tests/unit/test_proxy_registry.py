"""The registry must map "MCPProxyTool" to the class.

describe_remote_call_failure was inserted between @register_tool("MCPProxyTool") and the class
it decorated, so the registry held the function. Remote machines still loaded -- the auto
loader passes the class directly -- but anything that builds a proxy from its type name, as
ToolUniverse does for a tool config with "type": "MCPProxyTool", called the function with a
config dict instead.
"""

from __future__ import annotations

from tooluniverse.mcp_client_tool import MCPProxyTool
from tooluniverse.tool_registry import get_tool_class_lazy, get_tool_registry


def test_the_registry_holds_the_class():
    assert get_tool_registry().get("MCPProxyTool") is MCPProxyTool
    assert get_tool_class_lazy("MCPProxyTool") is MCPProxyTool


def test_a_proxy_can_be_built_from_its_type_name():
    cls = get_tool_class_lazy("MCPProxyTool")
    tool = cls({"name": "x_predict", "type": "MCPProxyTool",
                "server_url": "http://127.0.0.1:9/mcp", "target_tool_name": "predict"})

    assert isinstance(tool, MCPProxyTool)
