# ndex_tool.py
"""
NDEx (Network Data Exchange) API tool for ToolUniverse.

NDEx is a public repository and sharing platform for biological network models.
It hosts thousands of curated biological networks (protein-protein interaction,
signaling, metabolic, gene regulatory) from published studies.

API: https://public.ndexbio.org/v2/
No authentication required for public networks.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

NDEX_BASE_URL = "https://public.ndexbio.org/v2"


@register_tool("NDExTool")
class NDExTool(BaseTool):
    """
    Tool for querying the NDEx biological network repository.

    NDEx provides access to thousands of published biological networks
    including protein-protein interaction (PPI), signaling pathways,
    gene regulatory networks, and metabolic networks. Networks are
    contributed by research groups and databases like NCI-PID, SIGNOR,
    and individual labs.

    Supports: network search, network summary, network content retrieval.

    No authentication required for public networks.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NDEx API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NDEx API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to NDEx API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"NDEx API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying NDEx: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate NDEx endpoint."""
        if self.endpoint == "search":
            return self._search_networks(arguments)
        elif self.endpoint == "get_summary":
            return self._get_network_summary(arguments)
        elif self.endpoint == "get_network":
            return self._get_network(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search_networks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search NDEx for biological networks by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        size = arguments.get("size") or 10
        start = arguments.get("start") or 0

        url = f"{NDEX_BASE_URL}/search/network"
        params = {"start": start, "size": min(size, 100)}
        payload = {"searchString": query}

        response = requests.post(url, params=params, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        networks = []
        for n in data.get("networks", []):
            networks.append(
                {
                    "uuid": n.get("externalId"),
                    "name": n.get("name"),
                    "description": (n.get("description") or "")[:300],
                    "owner": n.get("owner"),
                    "node_count": n.get("nodeCount"),
                    "edge_count": n.get("edgeCount"),
                    "visibility": n.get("visibility"),
                    "doi": n.get("doi"),
                    "version": n.get("version"),
                }
            )

        return {
            "status": "success",
            "data": networks,
            "metadata": {
                "source": "NDEx (Network Data Exchange)",
                "total_results": data.get("numFound", len(networks)),
                "query": query,
                "start": start,
            },
        }

    def _get_network_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary information for a specific network by UUID."""
        uuid = arguments.get("uuid", "")
        if not uuid:
            return {"status": "error", "error": "uuid parameter is required"}

        url = f"{NDEX_BASE_URL}/network/{uuid}/summary"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Extract properties
        properties = {}
        for p in data.get("properties", []):
            properties[p.get("predicateString", "")] = str(p.get("value", ""))[:300]

        return {
            "status": "success",
            "data": {
                "uuid": data.get("externalId"),
                "name": data.get("name"),
                "description": (data.get("description") or "")[:500],
                "owner": data.get("owner"),
                "node_count": data.get("nodeCount"),
                "edge_count": data.get("edgeCount"),
                "visibility": data.get("visibility"),
                "doi": data.get("doi"),
                "version": data.get("version"),
                "creation_time": data.get("creationTime"),
                "modification_time": data.get("modificationTime"),
                "properties": properties,
            },
            "metadata": {
                "source": "NDEx (Network Data Exchange)",
            },
        }

    def _get_network(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get network content (nodes and edges) in CX format."""
        uuid = arguments.get("uuid", "")
        if not uuid:
            return {"status": "error", "error": "uuid parameter is required"}

        url = f"{NDEX_BASE_URL}/network/{uuid}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Parse CX format to extract nodes and edges
        nodes = []
        edges = []
        network_attrs = {}

        for aspect in data:
            if "nodes" in aspect:
                for node in aspect["nodes"]:
                    nodes.append(
                        {
                            "id": node.get("@id"),
                            "name": node.get("n"),
                            "represents": node.get("r"),
                        }
                    )
            elif "edges" in aspect:
                for edge in aspect["edges"]:
                    edges.append(
                        {
                            "id": edge.get("@id"),
                            "source": edge.get("s"),
                            "target": edge.get("t"),
                            "interaction": edge.get("i"),
                        }
                    )
            elif "networkAttributes" in aspect:
                for attr in aspect["networkAttributes"]:
                    network_attrs[attr.get("n", "")] = str(attr.get("v", ""))[:200]

        # Limit output size
        max_nodes = 200
        max_edges = 500

        return {
            "status": "success",
            "data": {
                "network_name": network_attrs.get("name", ""),
                "nodes": nodes[:max_nodes],
                "edges": edges[:max_edges],
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "truncated_nodes": len(nodes) > max_nodes,
                "truncated_edges": len(edges) > max_edges,
            },
            "metadata": {
                "source": "NDEx (Network Data Exchange)",
                "uuid": uuid,
                "format": "CX",
            },
        }
