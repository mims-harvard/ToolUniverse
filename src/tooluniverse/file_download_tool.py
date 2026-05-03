"""
File download tool - A curl-like tool for downloading files from URLs.
Supports Windows, Mac, and Linux platforms.
"""

import requests
import os
import tempfile
from urllib.parse import urlparse
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("FileDownloadTool")
class FileDownloadTool(BaseTool):
    """
    Download files from HTTP/HTTPS URLs - similar to curl.

    Supports:
    - Direct file downloads to specified or temporary locations
    - Binary and text file handling
    - Progress tracking (optional)
    - Cross-platform (Windows, Mac, Linux)

    Expects: {"url": "https://...", "output_path": "/path/to/save"}
    Optional: {"timeout": seconds, "return_content": bool}
    Returns: {"file_path": "...", "file_size": bytes} or {"error": "..."}
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.return_key = fields.get("return_key", "file_path")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download a file from a URL.

        Args:
            arguments: Dictionary containing:
                - url (str): URL to download from
                - output_path (str, optional): Path to save the file
                - timeout (int, optional): Request timeout (default: 30)
                - return_content (bool): Return as text (default: False)
                - chunk_size (int, optional): Chunk size (default: 8192)
                - follow_redirects (bool): Follow redirects (default: True)
        Returns:
            Dict with file_path and file_size, or content, or error
        """
        url = arguments.get("url")
        if not url:
            return {"status": "error", "error": "Parameter 'url' is required."}

        if not (url.startswith("http://") or url.startswith("https://")):
            return {
                "status": "error",
                "error": "URL must start with http:// or https://",
            }

        # Parse parameters
        output_path = arguments.get("output_path")
        timeout = arguments.get("timeout", 30)
        return_content = arguments.get("return_content", False)
        chunk_size = arguments.get("chunk_size", 8192)
        follow_redirects = arguments.get("follow_redirects", True)

        # Determine output path
        if output_path:
            output_path = self._normalize_path(output_path)
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to create directory: {e}",
                    }
        else:
            temp_dir = tempfile.gettempdir()
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "downloaded_file"
            filename = filename.split("?")[0]
            if not filename:
                filename = "downloaded_file"
            output_path = os.path.join(temp_dir, filename)
        try:
            response = requests.get(
                url, timeout=timeout, allow_redirects=follow_redirects, stream=True
            )
            response.raise_for_status()

            if return_content:
                content = response.text
                content_type = response.headers.get("Content-Type", "").lower()
                return {
                    "content": content,
                    "content_type": content_type,
                    "size": len(content),
                    "url": url,
                }

            file_size = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        file_size += len(chunk)

            return {
                "file_path": output_path,
                "file_size": file_size,
                "url": url,
                "content_type": response.headers.get("Content-Type", ""),
                "status_code": response.status_code,
            }

        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Request timed out after {timeout} seconds",
            }
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e}"}
        except requests.exceptions.ConnectionError as e:
            return {"status": "error", "error": f"Connection error: {e}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {e}"}
        except IOError as e:
            return {"status": "error", "error": f"Failed to write file: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {e}"}

    def _normalize_path(self, path: str) -> str:
        """
        Normalize file path for cross-platform compatibility.

        Args:
            path: File path to normalize

        Returns:
            Normalized path
        """
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)

        if not os.path.isabs(path):
            path = os.path.abspath(path)

        return path


@register_tool("BinaryDownloadTool")
class BinaryDownloadTool(BaseTool):
    """
    Download binary files with chunked streaming.

    Optimized for large binary files like images, videos, executables.
    Supports chunked downloads for better memory management.

    Expects: {"url": "https://...", "output_path": "/path/to/save"}
    Optional: {"chunk_size": bytes, "timeout": seconds}
    Returns: {"file_path": "...", "size": bytes, "content_type": "..."}
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download binary file from URL.

        Args:
            arguments: Dictionary containing url and optional parameters

        Returns:
            Dictionary with file_path and metadata, or error
        """
        url = arguments.get("url")
        if not url:
            return {"status": "error", "error": "Parameter 'url' is required."}

        output_path = arguments.get("output_path")
        if not output_path:
            msg = "Parameter 'output_path' is required for binary downloads."
            return {"status": "error", "error": msg}

        timeout = arguments.get("timeout", 30)
        # 1MB chunks for binary files
        chunk_size = arguments.get("chunk_size", 1024 * 1024)

        output_path = os.path.expanduser(output_path)
        output_path = os.path.expandvars(output_path)

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                return {"status": "error", "error": f"Failed to create directory: {e}"}

        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()

            file_size = 0
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        file_size += len(chunk)

            return {
                "file_path": output_path,
                "size": file_size,
                "content_type": response.headers.get("Content-Type", ""),
                "content_length": response.headers.get("Content-Length", ""),
                "url": url,
                "status_code": response.status_code,
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to download binary file: {e}"}


@register_tool("TextDownloadTool")
class TextDownloadTool(BaseTool):
    """
    Download and return text content from URLs.

    Optimized for text files - returns content as string directly.
    Supports encoding detection and normalization.

    Expects: {"url": "https://..."}
    Optional: {"encoding": "utf-8", "timeout": seconds}
    Returns: {"content": "text content", "encoding": "utf-8"}
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Download text content from URL.

        Args:
            arguments: Dictionary containing url and optional parameters

        Returns:
            Dictionary with content and encoding, or error
        """
        url = arguments.get("url")
        if not url:
            return {"status": "error", "error": "Parameter 'url' is required."}

        timeout = arguments.get("timeout", 30)
        encoding = arguments.get("encoding", None)  # Auto-detect if None

        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            if encoding:
                content = response.content.decode(encoding)
            else:
                content = response.text

            return {
                "content": content,
                "encoding": response.encoding,
                "size": len(content),
                "url": url,
                "content_type": response.headers.get("Content-Type", ""),
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to download text content: {e}"}
