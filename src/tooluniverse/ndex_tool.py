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


# CX declares an attribute's type in `d`; without it every value is a string
# and a SAINT score cannot be compared.
_CX_NUMERIC = {"integer", "long", "short", "double", "float"}


DESCRIPTION_CHARACTERS = 300


def _network_properties(network: dict) -> dict:
    """NDEx's network-level properties, keyed by name.

    The search row returned the uuid, name, owner and counts and dropped
    this block, where the fields a caller picks a network BY actually live:
    `organism: Homo sapiens`, `disease: cancer`, `tissue: breast carcinoma`,
    `methods: coexpression analysis`, `networkType: unsigned`. The values are
    coerced by the `dataType` NDEx declares, the same treatment round
    twenty-nine gave the node and edge attributes of a single network.
    """
    out = {}
    for row in network.get("properties") or []:
        if not isinstance(row, dict):
            continue
        name = row.get("predicateString")
        if not name:
            continue
        out[name] = _cx_scalar(row.get("value"), (row.get("dataType") or "string"))
    return out


def _cx_value(attribute: dict):
    """One CX attribute value, coerced to the type CX declares for it."""
    value = attribute.get("v")
    kind = (attribute.get("d") or "string").lower()
    if kind.startswith("list_of"):
        inner = kind.replace("list_of_", "")
        values = value if isinstance(value, list) else [value]
        return [_cx_scalar(v, inner) for v in values]
    return _cx_scalar(value, kind)


def _cx_scalar(value, kind: str):
    if value is None:
        return None
    if kind in _CX_NUMERIC:
        try:
            return int(value) if kind in ("integer", "long", "short") else float(value)
        except (TypeError, ValueError):
            return value
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes")
    return value


def _cx_attributes(aspect_rows: list) -> dict:
    """{element id: {name: value}} from a CX nodeAttributes/edgeAttributes aspect.

    Each row points at its element with `po`. The aspects can arrive before
    or after the elements they describe, so they are collected first and
    attached afterwards.
    """
    out: dict = {}
    for row in aspect_rows or []:
        if not isinstance(row, dict):
            continue
        owner = row.get("po")
        name = row.get("n")
        if owner is None or not name:
            continue
        out.setdefault(owner, {})[name] = _cx_value(row)
    return out


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

        size = arguments.get("size", 10)
        start = arguments.get("start", 0)
        if size is None:
            size = 10
        if start is None:
            start = 0
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 1000:
            return {
                "status": "error",
                "error": "size must be an integer between 1 and 1000",
            }
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            return {
                "status": "error",
                "error": "start must be a non-negative integer",
            }

        url = f"{NDEX_BASE_URL}/search/network"
        params = {"start": start, "size": size}
        payload = {"searchString": query}

        response = requests.post(url, params=params, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        networks = []
        for n in data.get("networks", []):
            description = n.get("description") or ""
            networks.append(
                {
                    "uuid": n.get("externalId"),
                    "name": n.get("name"),
                    "description": description[:DESCRIPTION_CHARACTERS],
                    "description_truncated": len(description)
                    > DESCRIPTION_CHARACTERS,
                    # What the network is OF: organism, disease, tissue,
                    # method. The search row had none of it.
                    "properties": _network_properties(n),
                    "created": n.get("creationTime"),
                    "modified": n.get("modificationTime"),
                    "is_certified": n.get("isCertified"),
                    "is_valid": n.get("isValid"),
                    "has_layout": n.get("hasLayout"),
                    # How big the download is, in the two CX versions.
                    "cx_file_size": n.get("cxFileSize"),
                    "cx2_file_size": n.get("cx2FileSize"),
                    "warnings": [w for w in (n.get("warnings") or []) if w],
                    "owner": n.get("owner"),
                    "node_count": n.get("nodeCount"),
                    "edge_count": n.get("edgeCount"),
                    "visibility": n.get("visibility"),
                    "doi": n.get("doi"),
                    "version": n.get("version"),
                }
            )

        total_results = data.get("numFound")
        returned = len(networks)
        consumed_through = (start + 1) * size
        has_more = isinstance(total_results, int) and consumed_through < total_results
        expected_returned = (
            min(size, max(total_results - start * size, 0))
            if isinstance(total_results, int)
            else None
        )
        short_page = isinstance(expected_returned, int) and returned < expected_returned
        return {
            "status": "success",
            "data": networks,
            "metadata": {
                "source": "NDEx (Network Data Exchange)",
                "total_results": total_results,
                "returned": returned,
                "query": query,
                "start": start,
                "page_index": start,
                "size": size,
                "has_more": has_more,
                "truncated": has_more,
                "next_start": start + 1 if has_more else None,
                "short_page": short_page,
                "warning": (
                    "NDEx returned fewer visible networks than the requested window; "
                    "continue with next_start because total_results still indicates more matches."
                    if short_page and has_more
                    else None
                ),
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

        # The same reader the search row uses. This built
        # `str(value)[:300]`, so a numeric property arrived as a truncated
        # string and the two handlers of one module disagreed about what a
        # property value is.
        properties = _network_properties(data)

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

        node_limit = arguments.get("node_limit", 200)
        node_offset = arguments.get("node_offset", 0)
        edge_limit = arguments.get("edge_limit", 500)
        edge_offset = arguments.get("edge_offset", 0)
        if (
            not isinstance(node_limit, int)
            or isinstance(node_limit, bool)
            or node_limit < 1
        ):
            return {"status": "error", "error": "node_limit must be a positive integer"}
        if (
            not isinstance(edge_limit, int)
            or isinstance(edge_limit, bool)
            or edge_limit < 1
        ):
            return {"status": "error", "error": "edge_limit must be a positive integer"}
        if (
            not isinstance(node_offset, int)
            or isinstance(node_offset, bool)
            or node_offset < 0
        ):
            return {
                "status": "error",
                "error": "node_offset must be a non-negative integer",
            }
        if (
            not isinstance(edge_offset, int)
            or isinstance(edge_offset, bool)
            or edge_offset < 0
        ):
            return {
                "status": "error",
                "error": "edge_offset must be a non-negative integer",
            }

        node_limit = min(node_limit, 1000)
        edge_limit = min(edge_limit, 2000)

        url = f"{NDEX_BASE_URL}/network/{uuid}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Parse CX format to extract nodes and edges
        nodes = []
        edges = []
        network_attrs = {}
        # The measurements that make a network a finding rather than a
        # drawing: this network's 82 nodes carry 378 nodeAttributes and its
        # 118 edges 2,222 edgeAttributes -- Saintscore, logOddsScore,
        # Entropy, WD, "# of patients altered", PreyUniprot -- and the rows
        # returned id, name, represents and id, source, target, interaction.
        node_attributes: dict = {}
        edge_attributes: dict = {}

        for aspect in data:
            if not isinstance(aspect, dict):
                continue
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
            elif "nodeAttributes" in aspect:
                node_attributes.update(_cx_attributes(aspect["nodeAttributes"]))
            elif "edgeAttributes" in aspect:
                edge_attributes.update(_cx_attributes(aspect["edgeAttributes"]))
            elif "networkAttributes" in aspect:
                for attr in aspect["networkAttributes"]:
                    network_attrs[attr.get("n", "")] = str(attr.get("v", ""))[:200]

        for node in nodes:
            node["attributes"] = node_attributes.get(node["id"], {})
        for edge in edges:
            edge["attributes"] = edge_attributes.get(edge["id"], {})

        node_attribute_names = sorted(
            {name for attrs in node_attributes.values() for name in attrs}
        )
        edge_attribute_names = sorted(
            {name for attrs in edge_attributes.values() for name in attrs}
        )

        node_page = nodes[node_offset : node_offset + node_limit]
        edge_page = edges[edge_offset : edge_offset + edge_limit]
        nodes_have_more = node_offset + len(node_page) < len(nodes)
        edges_have_more = edge_offset + len(edge_page) < len(edges)

        return {
            "status": "success",
            "data": {
                "network_name": network_attrs.get("name", ""),
                "nodes": node_page,
                "edges": edge_page,
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_offset": node_offset,
                "edge_offset": edge_offset,
                "node_limit": node_limit,
                "edge_limit": edge_limit,
                "returned_nodes": len(node_page),
                "returned_edges": len(edge_page),
                "nodes_have_more": nodes_have_more,
                "edges_have_more": edges_have_more,
                "next_node_offset": node_offset + len(node_page)
                if nodes_have_more
                else None,
                "next_edge_offset": edge_offset + len(edge_page)
                if edges_have_more
                else None,
                "truncated_nodes": node_offset > 0 or nodes_have_more,
                "truncated_edges": edge_offset > 0 or edges_have_more,
                "network_attributes": network_attrs,
                "node_attribute_names": node_attribute_names,
                "edge_attribute_names": edge_attribute_names,
            },
            "metadata": {
                "source": "NDEx (Network Data Exchange)",
                "uuid": uuid,
                "format": "CX",
                "attributes_note": "Per-node and per-edge attributes are under "
                "each row's 'attributes', typed as CX declares them; "
                "node_attribute_names and edge_attribute_names list every "
                "name in the whole network, not only this page. Layout "
                "coordinates (cartesianLayout) and Cytoscape visual "
                "properties are not returned.",
            },
        }
