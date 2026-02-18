# orthodb_tool.py
"""
OrthoDB v12 tool for ToolUniverse.

OrthoDB provides orthologous groups of proteins at different taxonomic levels,
enabling evolutionary analysis of gene conservation, functional annotation
transfer between species, and phylogenetic profiling.

API: https://data.orthodb.org/v12/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

ORTHODB_BASE_URL = "https://data.orthodb.org/v12"


@register_tool("OrthoDBTool")
class OrthoDBTool(BaseTool):
    """
    OrthoDB v12 tool for orthologous group analysis.

    Provides search for orthologous groups, group details with functional
    annotations (KEGG, GO), and member gene lists across species.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OrthoDB API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"OrthoDB API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to OrthoDB API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"OrthoDB API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying OrthoDB API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "group":
            return self._get_group(arguments)
        elif self.endpoint == "orthologs":
            return self._get_orthologs(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for orthologous groups by gene/protein name."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query parameter is required (gene name, e.g., 'BRCA1')"}
        species = arguments.get("species")
        level = arguments.get("level")
        limit = arguments.get("limit", 10)

        params = {"query": query, "limit": min(limit, 50)}
        if species:
            params["species"] = species
        if level:
            params["level"] = level

        url = f"{ORTHODB_BASE_URL}/search"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        group_ids = data.get("data", [])

        # Get basic info for top groups via tab endpoint
        groups = []
        for gid in group_ids[:limit]:
            groups.append({"group_id": gid})

        # Enrich with group names using the tab endpoint for first few
        if group_ids:
            try:
                tab_url = f"{ORTHODB_BASE_URL}/tab"
                tab_params = {"id": group_ids[0], "limit": 1}
                tab_resp = requests.get(
                    tab_url, params=tab_params, timeout=self.timeout
                )
                if tab_resp.status_code == 200:
                    lines = tab_resp.text.strip().split("\n")
                    if len(lines) > 1:
                        cols = lines[1].split("\t")
                        if len(cols) >= 2:
                            groups[0]["name"] = cols[1]
                            groups[0]["level_taxid"] = (
                                cols[2] if len(cols) > 2 else None
                            )
            except Exception:
                pass

        return {
            "data": {
                "query": query,
                "groups": groups,
                "total_groups": len(group_ids),
            },
            "metadata": {
                "source": "OrthoDB v12 - Search",
                "query": query,
            },
        }

    def _get_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about an orthologous group."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {"error": "group_id parameter is required (e.g., '727649at7742')"}

        url = f"{ORTHODB_BASE_URL}/group"
        params = {"id": group_id}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        group_data = data.get("data", {})
        if not group_data:
            return {"error": f"No data found for group {group_id}"}

        # Extract GO terms
        go_terms = []
        for go in (group_data.get("GO") or [])[:20]:
            go_terms.append(
                {
                    "id": go.get("id"),
                    "description": go.get("description"),
                    "category": go.get("type"),
                    "count": go.get("count"),
                }
            )

        # Extract KEGG pathways
        kegg_pathways = []
        for k in (group_data.get("KEGGpathway") or [])[:20]:
            kegg_pathways.append(
                {
                    "id": k.get("id"),
                    "description": k.get("description"),
                    "count": k.get("count"),
                }
            )

        # Extract InterPro domains
        interpro = []
        for ip in (group_data.get("InterPro") or [])[:20]:
            interpro.append(
                {
                    "id": ip.get("id"),
                    "description": ip.get("description"),
                    "count": ip.get("count"),
                }
            )

        return {
            "data": {
                "group_id": group_data.get("id"),
                "name": group_data.get("name"),
                "level_name": group_data.get("level_name"),
                "tax_id": group_data.get("tax_id"),
                "go_terms": go_terms if go_terms else None,
                "kegg_pathways": kegg_pathways if kegg_pathways else None,
                "interpro_domains": interpro if interpro else None,
            },
            "metadata": {
                "source": "OrthoDB v12 - Group Details",
                "group_id": group_id,
            },
        }

    def _get_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologous genes in specific species from a group."""
        group_id = arguments.get("group_id", "")
        if not group_id:
            return {"error": "group_id parameter is required (e.g., '727649at7742')"}
        species = arguments.get("species")

        # Use tab endpoint which gives structured gene list
        url = f"{ORTHODB_BASE_URL}/tab"
        params = {"id": group_id, "limit": 100}
        if species:
            params["species"] = species

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        lines = response.text.strip().split("\n")
        if len(lines) < 2:
            return {"error": f"No ortholog data found for group {group_id}"}

        # Parse header
        lines[0].split("\t")

        orthologs = []
        for line in lines[1:101]:
            cols = line.split("\t")
            if len(cols) >= 6:
                orthologs.append(
                    {
                        "group_id": cols[0] if len(cols) > 0 else None,
                        "group_name": cols[1] if len(cols) > 1 else None,
                        "level_taxid": cols[2] if len(cols) > 2 else None,
                        "organism_taxid": cols[3] if len(cols) > 3 else None,
                        "organism_name": cols[4] if len(cols) > 4 else None,
                        "gene_id": cols[5] if len(cols) > 5 else None,
                        "description": cols[6] if len(cols) > 6 else None,
                    }
                )

        # Summarize by organism
        organisms = {}
        for o in orthologs:
            org = o.get("organism_name", "unknown")
            organisms[org] = organisms.get(org, 0) + 1

        return {
            "data": {
                "group_id": group_id,
                "orthologs": orthologs,
                "total_orthologs": len(orthologs),
                "organisms_summary": organisms,
            },
            "metadata": {
                "source": "OrthoDB v12 - Orthologs",
                "group_id": group_id,
            },
        }
