"""
MarkItDown Tool for ToolUniverse

Simple implementation following Microsoft's official MCP pattern.
Supports http:, https:, file:, data: URIs.
"""

import os
import subprocess
import sys
import urllib.parse
import urllib.request
import tempfile
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("MarkItDownTool")
class MarkItDownTool(BaseTool):
    """MarkItDown tool for converting files to Markdown."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.tool_name = tool_config.get("name", "MarkItDownTool")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MarkItDown tool."""
        try:
            return self._convert_to_markdown(arguments)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _convert_to_markdown(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a resource described by URI to Markdown using markitdown CLI."""
        uri = arguments.get("uri")
        output_path = arguments.get("output_path")
        enable_plugins = arguments.get("enable_plugins", False)

        if not uri:
            return {"status": "error", "error": "URI is required"}

        try:
            # Parse URI
            parsed_uri = urllib.parse.urlparse(uri)
            scheme = parsed_uri.scheme.lower()

            # Handle different URI schemes
            if scheme in ["http", "https"]:
                # Download from URL
                temp_file = self._download_from_url(uri)
                if not temp_file:
                    return {
                        "status": "error",
                        "error": f"Failed to download from URL: {uri}",
                    }
                input_path = temp_file
                cleanup_temp = True

            elif scheme == "file":
                # Local file
                file_path = urllib.request.url2pathname(parsed_uri.path)
                if not os.path.exists(file_path):
                    return {"status": "error", "error": f"File not found: {file_path}"}
                input_path = file_path
                cleanup_temp = False

            elif scheme == "data":
                # Data URI
                temp_file = self._handle_data_uri(uri)
                if not temp_file:
                    return {
                        "status": "error",
                        "error": f"Failed to process data URI: {uri}",
                    }
                input_path = temp_file
                cleanup_temp = True

            else:
                return {
                    "status": "error",
                    "error": f"Unsupported URI scheme: {scheme}. Supported schemes: http, https, file, data",
                }

            # Build markitdown command
            cmd = [sys.executable, "-m", "markitdown", input_path]
            if enable_plugins:
                cmd.append("--use-plugins")
            if output_path:
                cmd.extend(["-o", output_path])

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                error_msg = f"MarkItDown failed: {result.stderr}"
                if cleanup_temp and os.path.exists(input_path):
                    os.unlink(input_path)
                return {"status": "error", "error": error_msg}

            # Get markdown content
            if output_path and os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
            else:
                markdown_content = result.stdout

            # Clean up temporary file if needed
            if cleanup_temp and os.path.exists(input_path):
                os.unlink(input_path)

            # Prepare response
            response = {
                "markdown_content": markdown_content,
                "file_info": {
                    "original_uri": uri,
                    "uri_scheme": scheme,
                    "output_file": output_path if output_path else None,
                },
            }

            # If no output_path specified, also return the content as a string for convenience
            if not output_path:
                response["content"] = markdown_content

            return response

        except Exception as e:
            return {"status": "error", "error": f"URI processing failed: {str(e)}"}

    def _download_from_url(self, url: str) -> str:
        """Download content from URL to temporary file."""
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read()

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                return temp_file.name
        except Exception:
            return None

    def _handle_data_uri(self, data_uri: str) -> str:
        """Handle data URI and save to temporary file."""
        try:
            # Parse data URI: data:[<mediatype>][;base64],<data>
            if "," not in data_uri:
                return None

            header, data = data_uri.split(",", 1)

            # Check if base64 encoded
            if ";base64" in header:
                import base64

                content = base64.b64decode(data)
            else:
                content = data.encode("utf-8")

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                return temp_file.name
        except Exception:
            return None
