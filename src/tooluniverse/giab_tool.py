# giab_tool.py
"""
Genome in a Bottle (GIAB) benchmark file browser for ToolUniverse.

GIAB (NIST) publishes the reference-standard high-confidence variant call
sets (VCF) and callable regions (BED) used to validate variant-calling
pipelines, for samples HG001-HG007 across multiple reference builds and
release versions (NISTv3.2 through v5.0q, plus CMRG, structural-variant,
and tandem-repeat benchmark sets). There is no REST/JSON API for this data
-- only a plain Apache directory listing at
https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/ -- so
this tool parses that listing to let an agent navigate the tree (trio ->
sample -> version -> reference build -> files) and get direct download
URLs for the benchmark VCF/BED files it needs.

No authentication required.
"""

import re
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

GIAB_HOST = "https://ftp-trace.ncbi.nlm.nih.gov"
GIAB_RELEASE_ROOT = "/ReferenceSamples/giab/release/"

_ENTRY_PATTERN = re.compile(
    r'<a href="([^"]+)">([^<]+)</a>\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})?\s*(\S*)'
)


def _parse_listing(html: str, listing_url: str) -> List[Dict[str, Any]]:
    """Parse an Apache-style directory listing into structured entries."""
    entries = []
    for href, name, modified, size in _ENTRY_PATTERN.findall(html):
        name = name.strip()
        if name == "Parent Directory" or href.startswith("http"):
            continue
        is_dir = href.endswith("/")
        entries.append(
            {
                "name": name.rstrip("/") if is_dir else name,
                "type": "directory" if is_dir else "file",
                "size": None if size == "-" else size,
                "last_modified": modified or None,
                "url": urljoin(listing_url, href),
            }
        )
    return entries


def _normalize_path(path: str):
    """Validate and normalize a path relative to the GIAB release root.

    Returns (normalized_path, error_message). Exactly one is None.
    """
    path = (path or "").strip().strip("/")
    if ".." in path.split("/"):
        return None, "path must not contain '..' path traversal segments."
    return path, None


@register_tool("GIABTool")
class GIABTool(BaseTool):
    """Browse the GIAB benchmark file release tree (NIST FTP mirror).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        path, err = _normalize_path(arguments.get("path", ""))
        if err is not None:
            return {"status": "error", "error": err}

        listing_url = urljoin(GIAB_HOST + GIAB_RELEASE_ROOT, path + "/" if path else "")

        try:
            resp = requests.get(listing_url, timeout=self.timeout)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GIAB request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"GIAB request failed: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No such GIAB path: '{path or '/'}'. Start with an "
                "empty path to list the top-level trios/samples.",
            }
        resp.raise_for_status()

        entries = _parse_listing(resp.text, listing_url)
        if not entries:
            return {
                "status": "error",
                "error": f"'{path or '/'}' is empty or not a directory listing.",
            }

        return {
            "status": "success",
            "data": entries,
            "metadata": {
                "path": path or "/",
                "listing_url": listing_url,
                "returned": len(entries),
                "source": "NIST Genome in a Bottle (ftp-trace.ncbi.nlm.nih.gov)",
            },
        }
