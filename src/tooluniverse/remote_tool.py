"""
Remote Tool Implementation

This module provides a RemoteTool class that represents external MCP/SMCP tools
that are available for listing but cannot be executed locally. These tools are
stored as configuration records only.
"""

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("RemoteTool")
class RemoteTool(BaseTool):
    """
    A placeholder tool class for external MCP/SMCP tools.

    RemoteTool represents tools that are hosted on external MCP/SMCP servers
    and are only available for discovery and listing purposes. These tools
    cannot be executed locally through ToolUniverse but their configurations
    are preserved for reference.

    Attributes:
        tool_config (dict): The tool configuration dictionary
        remote_info (dict): Information about the remote server and tool
    """

    def __init__(self, tool_config=None):
        """
        Initialize the RemoteTool.

        Args:
            tool_config (dict, optional): Tool configuration dictionary
        """
        super().__init__(tool_config)
        self.remote_info = tool_config.get("remote_info", {}) if tool_config else {}

    def run(self, arguments=None):
        """
        Placeholder run method for remote tools.

        Remote tools cannot be executed locally. This method always returns
        an error message indicating that the tool is not available for local execution.

        Args:
            arguments (dict, optional): Tool arguments (ignored)

        Returns
            dict: Error message indicating the tool is not available locally
        """
        server_type = self.remote_info.get("server_type", "Unknown")
        original_type = self.remote_info.get("original_type", "Unknown")

        return {
            "status": "error",
            "error": "Remote tool not available for local execution",
            "tool_name": (
                self.tool_config.get("name", "Unknown")
                if self.tool_config
                else "Unknown"
            ),
            "tool_type": "RemoteTool",
            "original_type": original_type,
            "server_type": server_type,
            "message": "This tool is hosted on an external MCP/SMCP server and cannot be executed locally. Please use the external server directly.",
            "remote_info": self.remote_info,
        }

    def get_remote_info(self):
        """
        Get information about the remote server hosting this tool.

        Returns
            dict: Remote server information including server type, URL, and original tool type
        """
        return self.remote_info.copy()

    def is_available_locally(self):
        """
        Check if this tool is available for local execution.

        Returns
            bool: Always False for RemoteTool instances
        """
        return False

    def get_server_info(self):
        """
        Get server connection information for this remote tool.

        Returns
            dict: Server connection details
        """
        return {
            "server_type": self.remote_info.get("server_type"),
            "server_url": self.remote_info.get("server_url"),
            "transport": self.remote_info.get("transport"),
            "mcp_tool_name": self.remote_info.get("mcp_tool_name"),
            "source_directory": self.remote_info.get("source_directory"),
        }
