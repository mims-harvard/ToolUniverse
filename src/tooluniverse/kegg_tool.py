"""
KEGG Database REST API Tool

This tool provides access to the KEGG (Kyoto Encyclopedia of Genes and Genomes)
database for pathway analysis, gene information, and organism data.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


class KEGGRESTTool(BaseTool):
    """Base class for KEGG REST API tools."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://rest.kegg.jp"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "text/plain, application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the KEGG API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            # KEGG API returns text/plain by default, parse as text
            content = response.text.strip()

            # Try to parse as structured data if possible
            if content.startswith("{") or content.startswith("["):
                try:
                    return {"status": "success", "data": response.json()}
                except Exception:
                    pass

            # Return as text data
            return {
                "status": "success",
                "data": content,
                "url": url,
                "content_type": response.headers.get("content-type", "text/plain"),
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"KEGG API request failed: {str(e)}",
                "url": url,
            }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)


@register_tool("KEGGSearchPathway")
class KEGGSearchPathway(KEGGRESTTool):
    """Search KEGG pathways by keyword."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/find/pathway"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search pathways with keyword."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {"status": "error", "error": "keyword is required"}

        # KEGG API requires the search term in the URL path
        endpoint = f"{self.endpoint}/{keyword}"
        result = self._make_request(endpoint)

        # Parse pathway results
        if result.get("status") == "success" and isinstance(result.get("data"), str):
            lines = result["data"].split("\n")
            pathways = []
            for line in lines:
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        pathways.append(
                            {"pathway_id": parts[0], "description": parts[1]}
                        )
            result["data"] = pathways
            result["count"] = len(pathways)

        return result


@register_tool("KEGGGetPathwayInfo")
class KEGGGetPathwayInfo(KEGGRESTTool):
    """Get detailed pathway information by pathway ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/get"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get pathway information."""
        pathway_id = arguments.get("pathway_id", "")
        if not pathway_id:
            return {"status": "error", "error": "pathway_id is required"}

        # Add pathway prefix if not present
        if not pathway_id.startswith("path:"):
            pathway_id = f"path:{pathway_id}"

        # KEGG API requires the ID in the URL path
        endpoint = f"{self.endpoint}/{pathway_id}"
        result = self._make_request(endpoint)

        # Parse pathway data
        if result.get("status") == "success" and isinstance(result.get("data"), str):
            lines = result["data"].split("\n")
            pathway_info = {
                "pathway_id": pathway_id,
                "raw_data": result["data"],
                "lines": len(lines),
            }
            result["data"] = pathway_info

        return result


@register_tool("KEGGFindGenes")
class KEGGFindGenes(KEGGRESTTool):
    """Find genes by keyword in KEGG database."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/find/genes"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find genes with keyword, optionally filtered by organism."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {"status": "error", "error": "keyword is required"}

        # Use organism-specific endpoint when provided (e.g., /find/hsa/ALDH)
        organism = arguments.get("organism", "").strip()
        if organism:
            endpoint = f"/find/{organism}/{keyword}"
        else:
            endpoint = f"{self.endpoint}/{keyword}"
        result = self._make_request(endpoint)

        # Parse gene results
        if result.get("status") == "success" and isinstance(result.get("data"), str):
            lines = result["data"].split("\n")
            genes = []
            for line in lines:
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        genes.append({"gene_id": parts[0], "description": parts[1]})
            result["data"] = genes
            result["count"] = len(genes)

        return result


@register_tool("KEGGGetGeneInfo")
class KEGGGetGeneInfo(KEGGRESTTool):
    """Get detailed gene information by gene ID."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/get"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene information."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"status": "error", "error": "gene_id is required"}

        # KEGG API requires the ID in the URL path
        endpoint = f"{self.endpoint}/{gene_id}"
        result = self._make_request(endpoint)

        # Parse gene data
        if result.get("status") == "success" and isinstance(result.get("data"), str):
            lines = result["data"].split("\n")
            gene_info = {
                "gene_id": gene_id,
                "raw_data": result["data"],
                "lines": len(lines),
            }
            result["data"] = gene_info

        return result


@register_tool("KEGGListOrganisms")
class KEGGListOrganisms(KEGGRESTTool):
    """List available organisms in KEGG database."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "/list/organism"

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List organisms."""
        result = self._make_request(self.endpoint)

        # Parse organism list
        if result.get("status") == "success" and isinstance(result.get("data"), str):
            lines = result["data"].split("\n")
            organisms = []
            for line in lines:
                if "\t" in line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        organisms.append(
                            {
                                "organism_code": parts[0],
                                "organism_name": parts[1],
                                "description": parts[2] if len(parts) > 2 else "",
                            }
                        )
            result["data"] = organisms
            result["count"] = len(organisms)

        return result
