"""USPTO Patent Claims Extractor --- download grant XML and parse every claim.

Metadata
--------
name:          patent_claims_tool
version:       1.0.0
owner:         ToolUniverse
last_reviewed: 2026-04-17

WHY THIS SHAPE
--------------
Patent claims are the legal heart of a patent --- they define exactly what is
protected.  Freedom-to-Operate (FTO) analysis starts here.  The USPTO Open Data
Portal stores claims inside grant XML documents, not as a standalone API
endpoint.  So this tool must:

1. Find the grant XML URI via the /associated-documents endpoint.
2. Download the (often large, 301-redirected) XML file.
3. Parse ``<claim>`` elements and classify each as independent or dependent.

Flow
----
    patent_number (optional)
        |
        v
    PatentResolverTool  -->  applicationNumberText
        |
        v
    /associated-documents  -->  grant XML URI
        |
        v
    GET XML (follow 301 redirects, 600s timeout)
        |
        v
    _parse_claims_from_xml  -->  list[dict]

Role / Module contract
----------------------
- Pure function ``_parse_claims_from_xml`` handles all XML parsing (testable
  without network).
- ``PatentClaimsTool.run()`` orchestrates the three-step download pipeline.

Inputs:  ``{"applicationNumberText": "14966067"}``  OR
         ``{"patent_number": "US9629826B2"}``
Outputs: ``{"status": "success", "data": {"claims": [...], ...}}``

Environment variables
---------------------
- ``USPTO_API_KEY`` --- required for ODP authentication (X-API-KEY header).

Callers
-------
- Any agent doing FTO analysis, prior-art review, or claim mapping.

Usage example
-------------
    from tooluniverse.patent_claims_tool import PatentClaimsTool
    tool = PatentClaimsTool({"name": "USPTO_get_patent_claims"})
    result = tool.run({"patent_number": "US9629826B2"})
"""

# --- Imports ---
import os
import re
import xml.etree.ElementTree as ET

import requests
from dotenv import find_dotenv, load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_tool import BaseTool
from .patent_resolver_tool import PatentResolverTool
from .tool_registry import register_tool

# --- Constants ---
load_dotenv(find_dotenv(usecwd=True))

USPTO_API_KEY = os.environ.get("USPTO_API_KEY")
BASE_URL = "https://api.uspto.gov/api/v1"

# Matches "of claim N" to detect dependent claims (e.g. "The method of claim 1")
_DEP_RE = re.compile(r"\bof claim (\d+)\b")


# --- Helpers (private) ---
def _parse_claims_from_xml(xml_text: str) -> list[dict]:
    """Extract structured claim data from USPTO grant XML.

    Parses ``<claim>`` elements inside ``<claims>`` and classifies each as
    independent or dependent by looking for the phrase "of claim N" in the
    claim text.

    Args:
        xml_text: Raw XML string from a USPTO grant document.

    Returns:
        List of dicts, each with keys: claim_number, claim_id, claim_text,
        is_independent, dependent_on.
    """
    root = ET.fromstring(xml_text)

    # <claims> may be missing entirely (e.g. design patents or empty XML)
    claims_element = root.find(".//claims")
    if claims_element is None:
        return []

    results: list[dict] = []
    for claim in claims_element.findall("claim"):
        # num attribute is a string in the XML --- cast to int
        claim_number = int(claim.get("num", "0"))
        claim_id = claim.get("id", "")

        # Collect all text from nested <claim-text> elements
        text_parts = []
        for ct in claim.iter("claim-text"):
            # .itertext() captures text inside nested sub-elements too
            text_parts.append("".join(ct.itertext()).strip())
        claim_text = " ".join(text_parts)

        # Detect dependency: "of claim N" pattern
        dep_match = _DEP_RE.search(claim_text)
        if dep_match:
            dependent_on = int(dep_match.group(1))
            is_independent = False
        else:
            dependent_on = None
            is_independent = True

        results.append(
            {
                "claim_number": claim_number,
                "claim_id": claim_id,
                "claim_text": claim_text,
                "is_independent": is_independent,
                "dependent_on": dependent_on,
            }
        )

    return results


# --- Public API ---
@register_tool("PatentClaimsTool")
class PatentClaimsTool(BaseTool):
    """Download and parse all claims from a granted US patent."""

    def __init__(
        self,
        tool_config: dict,
        api_key: str | None = USPTO_API_KEY,
        base_url: str = BASE_URL,
    ):
        super().__init__(tool_config)
        self.base_url = base_url

        if not api_key or api_key == "YOUR_API_KEY":
            raise ValueError(
                "Set USPTO_API_KEY environment variable for ODP authentication."
            )

        self.headers = {"X-API-KEY": api_key, "Accept": "application/json"}

        # Reuse session with retry --- same resilience pattern as PatentResolverTool
        self.session = requests.Session()
        retry = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=5,
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _resolve_patent_number(self, patent_number: str) -> str | None:
        """Convert a patent number to an application number via PatentResolverTool.

        Returns the application number string, or None on failure.
        """
        resolver = PatentResolverTool(
            {"name": "USPTO_patent_number_to_application"},
        )
        result = resolver.run({"patent_number": patent_number})

        if result.get("status") == "error":
            return None
        return result.get("data", {}).get("applicationNumberText")

    def _get_grant_xml_uri(self, app_number: str) -> str | None:
        """Fetch the grant XML download URI from /associated-documents.

        The response has grantDocumentMetaData at the top level of each
        patentFileWrapperDataBag item (NOT inside a nested document list).
        The fileLocationURI points directly to the downloadable XML.
        """
        url = f"{self.base_url}/patent/applications/{app_number}/associated-documents"
        resp = self.session.get(url, headers=self.headers, timeout=60)
        resp.raise_for_status()

        # The grant XML URI is at: patentFileWrapperDataBag[0].grantDocumentMetaData.fileLocationURI
        bag = resp.json().get("patentFileWrapperDataBag", [])
        if not bag:
            return None
        grant_meta = bag[0].get("grantDocumentMetaData")
        if not grant_meta:
            return None  # patent may not be granted yet
        return grant_meta.get("fileLocationURI")

    def _download_xml(self, uri: str) -> str:
        """Download XML from the given URI, following redirects.

        USPTO uses 301 redirects to route to the actual storage location.
        Grant XML can be large, so we use a generous 600-second timeout.
        """
        resp = self.session.get(
            uri,
            headers={"X-API-KEY": self.headers["X-API-KEY"]},
            allow_redirects=True,
            timeout=600,
        )
        resp.raise_for_status()
        return resp.text

    def run(self, arguments: dict) -> dict:
        """Extract claims from a granted US patent.

        Accepts ``applicationNumberText`` directly, or ``patent_number`` which
        gets resolved first via PatentResolverTool.
        """
        app_number = arguments.get("applicationNumberText", "").strip()
        patent_number = arguments.get("patent_number", "").strip()

        # Resolve patent_number -> applicationNumberText if needed
        if not app_number and patent_number:
            app_number = self._resolve_patent_number(patent_number) or ""

        if not app_number:
            return self.tool_error(
                "Provide applicationNumberText or patent_number",
                error_type="ValidationError",
                suggestion="Example: {'applicationNumberText': '14966067'} "
                "or {'patent_number': 'US9629826B2'}",
            )

        try:
            # Step 1: Get grant XML URI
            xml_uri = self._get_grant_xml_uri(app_number)
            if not xml_uri:
                return self.tool_error(
                    f"No grant XML found for application {app_number}",
                    error_type="NotFoundError",
                    suggestion="The patent may not be granted yet, or the "
                    "application number may be incorrect.",
                )

            # Step 2: Download the XML
            xml_text = self._download_xml(xml_uri)

            # Step 3: Parse claims
            claims = _parse_claims_from_xml(xml_text)

            independent_count = sum(1 for c in claims if c["is_independent"])

            return {
                "status": "success",
                "data": {
                    "application_number": app_number,
                    "claim_count": len(claims),
                    "independent_claim_count": independent_count,
                    "claims": claims,
                },
            }

        except requests.exceptions.RequestException as exc:
            return self.tool_error(
                f"USPTO API request failed: {exc}",
                error_type="NetworkError",
                suggestion="Check USPTO_API_KEY and network connectivity.",
            )
        except ET.ParseError as exc:
            return self.tool_error(
                f"Failed to parse grant XML: {exc}",
                error_type="ParseError",
                suggestion="The XML document may be malformed or empty.",
            )
