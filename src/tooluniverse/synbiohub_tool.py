# synbiohub_tool.py
"""
SynBioHub API tool for ToolUniverse.

SynBioHub is an open-source repository and sharing platform for synthetic
biology designs encoded in SBOL (Synthetic Biology Open Language). It hosts
the iGEM Registry of Standard Biological Parts, containing thousands of
characterized genetic parts (promoters, coding sequences, terminators,
ribosome binding sites, reporters, etc.).

API: https://synbiohub.org/
No authentication required for public collections.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

SYNBIOHUB_BASE_URL = "https://synbiohub.org"


@register_tool("SynBioHubTool")
class SynBioHubTool(BaseTool):
    """
    Tool for querying SynBioHub, a synthetic biology parts repository.

    SynBioHub hosts the iGEM Registry (20,000+ BioBricks), as well as other
    public collections of genetic parts and designs encoded in SBOL format.
    Parts include promoters, coding sequences (CDS), terminators, ribosome
    binding sites (RBS), reporters (GFP, RFP, LacZ), regulatory elements,
    and composite devices.

    Supports: search parts by keyword, list collections, get part SBOL data.

    No authentication required for public collections.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SynBioHub API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"SynBioHub API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to SynBioHub API"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"SynBioHub API HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying SynBioHub: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate SynBioHub endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "get_collections":
            return self._get_collections(arguments)
        elif self.endpoint == "get_part":
            return self._get_part(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SynBioHub for genetic parts by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"error": "query parameter is required"}

        offset = arguments.get("offset") or 0
        limit = arguments.get("limit") or 10

        url = f"{SYNBIOHUB_BASE_URL}/search/{query}"
        params = {"offset": offset, "limit": min(limit, 50)}
        headers = {"Accept": "application/json"}

        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Map SO roles to human-readable types
        role_map = {
            "SO:0000167": "promoter",
            "SO:0000316": "CDS",
            "SO:0000141": "terminator",
            "SO:0000139": "RBS",
            "SO:0000110": "sequence_feature",
            "SO:0000804": "engineered_region",
            "SO:0000112": "primer",
            "SO:0000296": "origin_of_replication",
        }

        results = []
        for item in data:
            sbol_type_short = (item.get("type") or "").split("#")[-1]
            role_raw = (item.get("role") or "").split("/")[-1]
            role_label = role_map.get(role_raw, role_raw)

            results.append(
                {
                    "display_id": item.get("displayId"),
                    "name": item.get("name"),
                    "description": (item.get("description") or "")[:300],
                    "uri": item.get("uri"),
                    "version": item.get("version"),
                    "sbol_type": sbol_type_short,
                    "role": role_label,
                }
            )

        return {
            "data": results,
            "metadata": {
                "source": "SynBioHub",
                "query": query,
                "offset": offset,
                "results_returned": len(results),
            },
        }

    def _get_collections(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List public collections available on SynBioHub."""
        url = f"{SYNBIOHUB_BASE_URL}/rootCollections"
        headers = {"Accept": "application/json"}

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        collections = []
        for c in data:
            collections.append(
                {
                    "name": c.get("name"),
                    "description": (c.get("description") or "")[:300],
                    "display_id": c.get("displayId"),
                    "uri": c.get("uri"),
                    "version": c.get("version"),
                    "member_count": c.get("memberCount"),
                }
            )

        return {
            "data": collections,
            "metadata": {
                "source": "SynBioHub",
                "total_collections": len(collections),
            },
        }

    def _get_part(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed SBOL information for a specific genetic part."""
        part_uri = arguments.get("part_uri", "")
        display_id = arguments.get("display_id", "")

        if not part_uri and not display_id:
            return {"error": "Either part_uri or display_id is required"}

        if not part_uri and display_id:
            # Construct URI from display_id (assume iGEM collection)
            part_uri = f"{SYNBIOHUB_BASE_URL}/public/igem/{display_id}/1"

        # Get SBOL XML data
        url = f"{part_uri}/sbol"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        xml_content = response.text

        # Parse XML to extract key information
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_content)

        # Define namespaces
        ns = {
            "sbol": "http://sbols.org/v2#",
            "dcterms": "http://purl.org/dc/terms/",
            "prov": "http://www.w3.org/ns/prov#",
            "igem": "http://wiki.synbiohub.org/wiki/Terms/igem#",
        }

        result = {
            "display_id": None,
            "title": None,
            "description": None,
            "type": None,
            "role": None,
            "sequence": None,
            "sequence_length": None,
            "created": None,
            "modified": None,
            "derived_from": None,
        }

        # Extract ComponentDefinition
        comp_def = root.find(".//sbol:ComponentDefinition", ns)
        if comp_def is not None:
            result["display_id"] = self._find_text(comp_def, "sbol:displayId", ns)
            result["title"] = self._find_text(comp_def, "dcterms:title", ns)
            result["description"] = self._find_text(comp_def, "dcterms:description", ns)
            result["created"] = self._find_text(comp_def, "dcterms:created", ns)
            result["modified"] = self._find_text(comp_def, "dcterms:modified", ns)

            type_elem = comp_def.find("sbol:type", ns)
            if type_elem is not None:
                result["type"] = type_elem.get(
                    "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource", ""
                ).split("#")[-1]

            role_elems = comp_def.findall("sbol:role", ns)
            roles = []
            for r in role_elems:
                role_val = r.get(
                    "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource", ""
                )
                roles.append(role_val.split("/")[-1])
            result["role"] = roles

            derived = comp_def.find("prov:wasDerivedFrom", ns)
            if derived is not None:
                result["derived_from"] = derived.get(
                    "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
                )

        # Extract Sequence
        seq_elem = root.find(".//sbol:Sequence", ns)
        if seq_elem is not None:
            elements = self._find_text(seq_elem, "sbol:elements", ns)
            if elements:
                result["sequence"] = elements[:500]
                result["sequence_length"] = len(elements)

        return {
            "data": result,
            "metadata": {
                "source": "SynBioHub",
                "part_uri": part_uri,
                "format": "SBOL2",
            },
        }

    @staticmethod
    def _find_text(parent, tag, ns):
        """Find text content of an XML element."""
        elem = parent.find(tag, ns)
        return elem.text if elem is not None else None
