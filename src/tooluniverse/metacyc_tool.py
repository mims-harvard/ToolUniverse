"""
MetaCyc tool for ToolUniverse.

MetaCyc is a curated database of experimentally elucidated metabolic
pathways from all domains of life.

Website: https://metacyc.org/
BioCyc: https://biocyc.org/
"""

import re
import requests
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOCYC_BASE_URL = "https://biocyc.org"
BIOCYC_API_URL = "https://websvc.biocyc.org"
_AUTH_WALL_ERROR = {
    "status": "error",
    "error": (
        "BioCyc now requires a free account for API access. MetaCyc tools are unavailable. "
        "Create an account at https://biocyc.org/signup.shtml or use KEGG/Reactome tools as alternatives."
    ),
    "retryable": False,
}


@register_tool("MetaCycTool")
class MetaCycTool(BaseTool):
    """
    Tool for querying MetaCyc metabolic pathway database.

    MetaCyc provides:
    - Experimentally elucidated metabolic pathways
    - Enzymes and reactions
    - Metabolites and compounds
    - Pathway diagrams

    Uses BioCyc web services API.
    No authentication required for basic access.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MetaCyc query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "search_pathways":
            return self._search_pathways(arguments)
        elif operation == "get_pathway":
            return self._get_pathway(arguments)
        elif operation == "get_compound":
            return self._get_compound(arguments)
        elif operation == "get_reaction":
            return self._get_reaction(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_pathways, get_pathway, get_compound, get_reaction",
            }

    def _fetch_biocyc_xml(self, object_id: str) -> Optional[str]:
        """Fetch BioCyc XML for a MetaCyc object using the web services API.

        Feature-84B-004/005: biocyc.org/getxml?META=ID returns HTML (wrong).
        websvc.biocyc.org/getxml?id=META:ID returns XML (correct).
        Returns "AUTH_REQUIRED" if BioCyc redirects to account-required page.
        """
        resp = requests.get(
            f"{BIOCYC_API_URL}/getxml",
            params={"id": f"META:{object_id}", "detail": "full"},
            timeout=self.timeout,
            headers={"User-Agent": "ToolUniverse/MetaCyc"},
        )
        if resp.status_code != 200:
            return None
        # Detect BioCyc authentication wall (redirected to account-required page)
        if "account-required" in resp.url:
            return "AUTH_REQUIRED"
        content = resp.text
        # Verify it's actually XML (not an HTML error page)
        return content if content.strip().startswith("<?xml") else None

    def _parse_xml_field(self, xml: str, tag: str) -> Optional[str]:
        """Extract the text content of the first matching XML tag."""
        m = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", xml)
        return m.group(1).strip() if m else None

    def _parse_xml_frameids(self, xml: str) -> List[str]:
        """Extract all frameid attribute values from an XML document."""
        return re.findall(r'frameid=["\']([^"\']+)["\']', xml)

    def _search_pathways(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search MetaCyc for pathways.

        Args:
            arguments: Dict containing:
                - query: Search query (pathway name or keyword)
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        try:
            # Use BioCyc quick search API
            response = requests.get(
                f"{BIOCYC_BASE_URL}/META/search-query",
                params={"type": "PATHWAY", "query": query},
                timeout=self.timeout,
                headers={
                    "User-Agent": "ToolUniverse/MetaCyc",
                    "Accept": "application/json",
                },
            )

            # If JSON response works
            if "json" in response.headers.get("Content-Type", ""):
                data = response.json()
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "results": data
                        if isinstance(data, list)
                        else data.get("results", []),
                    },
                    "metadata": {"source": "MetaCyc"},
                }

            # Non-JSON response — likely auth wall
            return _AUTH_WALL_ERROR

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_pathway(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get pathway details by MetaCyc pathway ID.

        Args:
            arguments: Dict containing:
                - pathway_id: MetaCyc pathway ID (e.g., PWY-5177)
        """
        pathway_id = arguments.get("pathway_id", "")
        if not pathway_id:
            return {
                "status": "error",
                "error": "Missing required parameter: pathway_id",
            }

        try:
            xml = self._fetch_biocyc_xml(pathway_id)
            if xml == "AUTH_REQUIRED":
                return _AUTH_WALL_ERROR
            if xml is None:
                return {"status": "error", "error": f"Pathway not found: {pathway_id}"}

            name = self._parse_xml_field(xml, "common-name")
            reaction_ids = [
                fid
                for fid in self._parse_xml_frameids(xml)
                if fid != pathway_id and not fid.endswith("-VARIANTS")
            ]
            synonyms = re.findall(r"<synonym[^>]*>([^<]+)</synonym>", xml)
            return {
                "status": "success",
                "data": {
                    "pathway_id": pathway_id,
                    "name": name,
                    "synonyms": synonyms,
                    "reaction_ids": list(dict.fromkeys(reaction_ids)),
                    "url": f"{BIOCYC_BASE_URL}/META/NEW-IMAGE?type=PATHWAY&object={pathway_id}",
                    "diagram_url": f"{BIOCYC_BASE_URL}/META/NEW-IMAGE?type=PATHWAY&object={pathway_id}&detail-level=2",
                },
                "metadata": {"source": "MetaCyc", "pathway_id": pathway_id},
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get compound details from MetaCyc.

        Args:
            arguments: Dict containing:
                - compound_id: MetaCyc compound ID (e.g., CPD-1)
        """
        compound_id = arguments.get("compound_id", "")
        if not compound_id:
            return {
                "status": "error",
                "error": "Missing required parameter: compound_id",
            }

        try:
            xml = self._fetch_biocyc_xml(compound_id)
            if xml == "AUTH_REQUIRED":
                return _AUTH_WALL_ERROR
            if xml is None:
                return {
                    "status": "error",
                    "error": f"Compound not found: {compound_id}",
                }

            name = self._parse_xml_field(xml, "common-name")
            formula = self._parse_xml_field(xml, "molecular-weight-exp")
            synonyms = re.findall(r"<synonym[^>]*>([^<]+)</synonym>", xml)
            return {
                "status": "success",
                "data": {
                    "compound_id": compound_id,
                    "name": name,
                    "synonyms": synonyms,
                    "molecular_weight": formula,
                    "url": f"{BIOCYC_BASE_URL}/compound?orgid=META&id={compound_id}",
                },
                "metadata": {"source": "MetaCyc", "compound_id": compound_id},
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_reaction(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get reaction details from MetaCyc.

        Args:
            arguments: Dict containing:
                - reaction_id: MetaCyc reaction ID (e.g., RXN-14500)
        """
        reaction_id = arguments.get("reaction_id", "")
        if not reaction_id:
            return {
                "status": "error",
                "error": "Missing required parameter: reaction_id",
            }

        try:
            xml = self._fetch_biocyc_xml(reaction_id)
            if xml == "AUTH_REQUIRED":
                return _AUTH_WALL_ERROR
            if xml is None:
                return {
                    "status": "error",
                    "error": f"Reaction not found: {reaction_id}",
                }

            name = self._parse_xml_field(xml, "common-name")
            ec_numbers = re.findall(r"<ec-number[^>]*>([^<]+)</ec-number>", xml)
            synonyms = re.findall(r"<synonym[^>]*>([^<]+)</synonym>", xml)
            return {
                "status": "success",
                "data": {
                    "reaction_id": reaction_id,
                    "name": name,
                    "ec_numbers": ec_numbers,
                    "synonyms": synonyms,
                    "url": f"{BIOCYC_BASE_URL}/META/NEW-IMAGE?type=REACTION&object={reaction_id}",
                },
                "metadata": {"source": "MetaCyc", "reaction_id": reaction_id},
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
