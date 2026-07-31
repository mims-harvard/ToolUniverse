import logging
import sys

import tooluniverse.execute_function as execute_function_module
from tooluniverse.execute_function import ToolUniverse


class _SuccessfulAutoLoader:
    def __init__(self, _config):
        pass

    async def auto_load_and_register(self, _engine):
        return {
            "discovered_count": 1,
            "registered_count": 1,
            "tools": ["remote_tool"],
            "registered_tools": ["mcp_remote_tool"],
        }

    async def _close_session(self):
        pass


def test_successful_mcp_auto_loader_does_not_write_to_stdout(monkeypatch, capsys):
    engine = ToolUniverse.__new__(ToolUniverse)
    engine.logger = logging.getLogger("test_mcp_auto_loader_stdout")
    engine.all_tools = [
        {
            "name": "test_loader",
            "type": "MCPAutoLoaderTool",
            "server_url": "https://example.test/mcp",
            "timeout": 1,
        }
    ]
    engine.all_tool_dict = {}
    engine.callable_functions = {}

    # stdio mode routes ToolUniverse logs to stderr. Patch the convenience
    # logger locally so this test detects direct stdout writes without changing
    # the process-wide logging singleton for later tests.
    monkeypatch.setattr(
        execute_function_module,
        "info",
        lambda message: print(message, file=sys.stderr),
    )
    monkeypatch.setattr(
        execute_function_module,
        "get_tool_class_lazy",
        lambda _name: _SuccessfulAutoLoader,
    )

    engine._process_mcp_auto_loaders()

    assert capsys.readouterr().out == ""
