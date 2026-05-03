"""
ENA Browser API Tool

This tool provides access to the ENA Browser API for retrieving nucleotide
sequences, metadata, and cross-references from the European Nucleotide Archive.
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("ENABrowserRESTTool")
class ENABrowserRESTTool(BaseTool):
    """
    ENA Browser API REST tool.
    Generic wrapper for ENA Browser API endpoints defined in ena_browser_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/ena/browser/api"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "*/*", "User-Agent": "ToolUniverse/1.0"})
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config["fields"].get("endpoint", "")
        tool_name = self.tool_config.get("name", "")

        if endpoint_template:
            url = endpoint_template
            for k, v in args.items():
                url = url.replace(f"{{{k}}}", str(v))
            return url

        # Build URL based on tool name
        if tool_name == "ena_get_sequence_fasta":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/fasta/{accession}"

        elif tool_name == "ena_get_sequence_embl":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/embl/{accession}"

        elif tool_name == "ena_get_sequence_xml":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/xml/{accession}"

        elif tool_name == "ena_get_entry":
            accession = args.get("accession", "")
            if accession:
                # ENA Browser view endpoint doesn't exist, use FASTA and extract metadata
                # The endpoint template may specify /view/ but we'll override it
                return f"{self.base_url}/fasta/{accession}"

        elif tool_name == "ena_get_entry_history":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/versions/{accession}"

        elif tool_name == "ena_get_entry_summary":
            accession = args.get("accession", "")
            if accession:
                return f"{self.base_url}/summary/{accession}"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for ENA Browser API"""
        params = {}

        # ENA Browser API uses query parameters for some operations
        if "download" in args:
            params["download"] = args["download"]
        if "expanded" in args:
            params["expanded"] = args["expanded"]

        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ENA Browser API call"""
        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)
            tool_name = self.tool_config.get("name", "")

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # ENA Browser returns text (FASTA, EMBL, XML) or JSON
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                data = response.json()
            else:
                # Return text content
                data = response.text

            response_data = {
                "status": "success",
                "data": data,
                "url": response.url,
                "content_type": content_type,
            }

            # For entry metadata, extract from FASTA header
            if (
                tool_name == "ena_get_entry"
                and isinstance(data, str)
                and data.startswith(">")
            ):
                # Extract metadata from FASTA header
                lines = data.split("\n")
                header_line = lines[0] if lines else ""
                # Parse header: >ENA|accession|version description
                parts = header_line.replace(">", "").split(" ", 1)
                metadata = {
                    "header": header_line,
                    "accession": parts[0].split("|")[-1]
                    if "|" in parts[0]
                    else parts[0]
                    if parts
                    else "",
                    "description": parts[1] if len(parts) > 1 else "",
                    "sequence_length": len("".join(lines[1:])) if len(lines) > 1 else 0,
                    "note": "Metadata extracted from FASTA header. For comprehensive metadata, use EBI Search API with 'ena' domain or visit ENA website.",
                }
                response_data["metadata"] = metadata
                response_data["data"] = metadata  # Return metadata as main data

            # For FASTA sequences, count entries
            if tool_name == "ena_get_sequence_fasta" and isinstance(data, str):
                response_data["count"] = data.count(">")

            return response_data

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"ENA Browser API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
