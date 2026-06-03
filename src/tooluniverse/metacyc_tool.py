"""
MetaCyc tool for ToolUniverse.

MetaCyc is a curated database of experimentally elucidated metabolic
pathways from all domains of life.

Website: https://metacyc.org/
BioCyc: https://biocyc.org/
"""

import os
import re
import requests
from typing import Any, Dict, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

BIOCYC_BASE_URL = "https://biocyc.org"
BIOCYC_API_URL = "https://websvc.biocyc.org"
# BioCyc gates its web services behind a free account: anonymous requests are
# allowed for ~1 call then redirected to a "Create Account" page. Logging in
# (POST email+password -> session cookie) lifts the wall. Verified 2026-06-03.
BIOCYC_LOGIN_URL = f"{BIOCYC_API_URL}/credentials/login/"
_AUTH_WALL_ERROR = {
    "status": "error",
    "error": (
        "BioCyc requires a free account for API access. "
        "Set BIOCYC_EMAIL and BIOCYC_PASSWORD environment variables. "
        "Register for free at https://biocyc.org/signup.shtml "
        "(or use the KEGG/Reactome tools, which need no account)."
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
        # Reused across calls so the BioCyc session cookie obtained at login is
        # carried on every subsequent web-service request.
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ToolUniverse/MetaCyc"})
        self._logged_in = False

    def _ensure_login(self) -> Optional[Dict[str, Any]]:
        """Authenticate against BioCyc once per tool instance.

        Returns None on success (the session now carries the auth cookie), or
        an error dict (no credentials / bad credentials) the caller returns.
        """
        if self._logged_in:
            return None

        email = os.environ.get("BIOCYC_EMAIL", "")
        password = os.environ.get("BIOCYC_PASSWORD", "")
        if not email or not password:
            return _AUTH_WALL_ERROR

        try:
            resp = self.session.post(
                BIOCYC_LOGIN_URL,
                data={"email": email, "password": password},
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"BioCyc login failed: {str(e)}"}

        # Wrong credentials -> HTTP 401 {"error": "no match for email and password"}.
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": (
                    "Invalid BioCyc credentials. Check BIOCYC_EMAIL and "
                    "BIOCYC_PASSWORD (register at https://biocyc.org/signup.shtml)."
                ),
            }

        self._logged_in = True
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MetaCyc query based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        # All operations hit the account-gated BioCyc web services, so log in
        # first and surface a clear credentials error before doing any work.
        auth_error = self._ensure_login()
        if auth_error is not None:
            return auth_error

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
        Uses the authenticated session (see _ensure_login). Returns
        "AUTH_REQUIRED" if BioCyc still redirects to an account-required page.
        """
        resp = self.session.get(
            f"{BIOCYC_API_URL}/getxml",
            params={"id": f"META:{object_id}", "detail": "full"},
            timeout=self.timeout,
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

    def _parse_pathway_hits(self, xml: str) -> List[Dict[str, str]]:
        """Extract (id, name) pairs from each <Pathway> element of a query result."""
        hits = []
        for block in re.findall(r"<Pathway\b[^>]*>.*?</Pathway>", xml, flags=re.DOTALL):
            m_id = re.search(r'frameid=["\']([^"\']+)["\']', block)
            if not m_id:
                continue
            name = self._parse_xml_field(block, "common-name")
            hits.append({"pathway_id": m_id.group(1), "name": name or m_id.group(1)})
        return hits

    def _search_pathways(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search MetaCyc for pathways whose name matches the query.

        Args:
            arguments: Dict containing:
                - query: Search query (pathway name or keyword)

        Uses the authenticated BioVelo xmlquery web service, which returns
        parseable XML (the public /META/search-query path serves an HTML page).
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        # BioVelo: every MetaCyc pathway whose common-name contains the query.
        escaped = query.replace('"', "")
        biovelo = f'[x:x<-meta^^pathways,x^common-name~"{escaped}"]'

        try:
            response = self.session.get(
                f"{BIOCYC_API_URL}/xmlquery",
                params={"": biovelo, "detail": "low"},
                timeout=self.timeout,
            )
            if response.status_code != 200 or "account-required" in response.url:
                return _AUTH_WALL_ERROR
            xml = response.text
            if not xml.strip().startswith("<?xml"):
                return _AUTH_WALL_ERROR

            hits = self._parse_pathway_hits(xml)
            return {
                "status": "success",
                "data": {"query": query, "results": hits},
                "metadata": {"source": "MetaCyc", "count": len(hits)},
            }

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
