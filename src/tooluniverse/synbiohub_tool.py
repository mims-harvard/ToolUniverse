# synbiohub_tool.py
"""
SynBioHub API tool for ToolUniverse.

SynBioHub is an open-source repository and sharing platform for synthetic
biology designs encoded in SBOL (Synthetic Biology Open Language). It hosts
the iGEM Registry of Standard Biological Parts, containing thousands of
characterized genetic parts (promoters, coding sequences, terminators,
ribosome binding sites, reporters, etc.).

API: https://synbiohub.org/
Note: synbiohub.org now requires a logged-in session for /search,
/rootCollections, and per-part /sbol requests (confirmed live: all three
return HTTP 401 or an HTML login redirect for unauthenticated requests as
of this writing), despite this having been a public, keyless API
previously. This tool does not support authentication, so these calls
will currently fail until synbiohub.org's policy changes or auth support
is added.
"""

import os
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

    Note: synbiohub.org now requires a logged-in session for /search,
    /rootCollections, and per-part /sbol requests (confirmed live: all
    three return HTTP 401 or an HTML login redirect for unauthenticated
    requests as of this writing), despite this having been a public,
    keyless API previously. This tool does not support authentication, so
    these calls will currently fail until synbiohub.org's policy changes
    or auth support is added.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")
        # Each tool's own description already documents this env var as
        # the workaround for synbiohub.org's login wall, but nothing in
        # this module previously read it -- the documented capability
        # didn't exist. SynBioHub's REST API accepts a prior /login
        # session token via the "X-authorization" header.
        self.api_token = os.environ.get("SYNBIOHUB_API_TOKEN")

    def _token_header(self) -> Dict[str, str]:
        """X-authorization header carrying the SynBioHub session token, if set."""
        return {"X-authorization": self.api_token} if self.api_token else {}

    def _auth_headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", **self._token_header()}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SynBioHub API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SynBioHub API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to SynBioHub API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 401:
                # Confirmed live: synbiohub.org now requires login for
                # /search, /rootCollections, and per-part /sbol requests,
                # contradicting this family's original "no authentication
                # required for public collections" premise.
                hint = (
                    "no SYNBIOHUB_API_TOKEN is set"
                    if not self.api_token
                    else "the configured SYNBIOHUB_API_TOKEN may be invalid or expired"
                )
                return {
                    "status": "error",
                    "error": (
                        "SynBioHub API HTTP error: 401 (login required). "
                        "synbiohub.org now requires an authenticated session for "
                        f"this endpoint ({hint}). Log in at synbiohub.org, then "
                        "set SYNBIOHUB_API_TOKEN to the session token to retry."
                    ),
                }
            return {
                "status": "error",
                "error": f"SynBioHub API HTTP error: {code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying SynBioHub: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate SynBioHub endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "get_collections":
            return self._get_collections(arguments)
        elif self.endpoint == "get_part":
            return self._get_part(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SynBioHub for genetic parts by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        offset = arguments.get("offset") or 0
        limit = arguments.get("limit") or 10

        url = f"{SYNBIOHUB_BASE_URL}/search/{query}"
        params = {"offset": offset, "limit": min(limit, 50)}

        response = requests.get(
            url, params=params, headers=self._auth_headers(), timeout=self.timeout
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
            "status": "success",
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

        response = requests.get(url, headers=self._auth_headers(), timeout=self.timeout)
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
            "status": "success",
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
            return {
                "status": "error",
                "error": "Either part_uri or display_id is required",
            }

        if not part_uri and display_id:
            # Construct URI from display_id (assume iGEM collection)
            part_uri = f"{SYNBIOHUB_BASE_URL}/public/igem/{display_id}/1"

        # Get SBOL XML data (no Accept: application/json here -- this
        # endpoint returns XML, not JSON).
        url = f"{part_uri}/sbol"
        response = requests.get(url, headers=self._token_header(), timeout=self.timeout)
        response.raise_for_status()
        xml_content = response.text

        # SynBioHub now requires login for some/all part-detail requests
        # (confirmed live: an unauthenticated /sbol request lands on an
        # HTML login page, served as a plain 200 OK -- raise_for_status()
        # above doesn't catch this). Detect non-XML content before
        # attempting to parse it, since ET.fromstring() on an HTML page
        # otherwise raises an opaque "mismatched tag: line N, column M"
        # with no indication of the real cause.
        content_type = response.headers.get("Content-Type", "")
        looks_like_xml = xml_content.lstrip().startswith(("<?xml", "<rdf:RDF"))
        if "xml" not in content_type.lower() and not looks_like_xml:
            return {
                "status": "error",
                "error": (
                    f"SynBioHub did not return SBOL/XML data for '{part_uri}' "
                    "(got non-XML content, likely an HTML login or error page). "
                    "The part may not exist, or SynBioHub may now require "
                    "authentication for this request."
                ),
            }

        # Parse XML to extract key information
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return {
                "status": "error",
                "error": f"Failed to parse SBOL/XML response for '{part_uri}': {e}",
            }

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
            "status": "success",
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
