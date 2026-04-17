"""USPTO Patent Number Resolver --- convert any patent identifier to an application number.

Metadata
--------
name:          patent_resolver_tool
version:       1.0.0
owner:         ToolUniverse
last_reviewed: 2026-04-17

WHY THIS SHAPE
--------------
Every other USPTO Open Data Portal endpoint requires an *application number* as
its primary key, yet users almost never know it.  They have grant numbers, pub
numbers, or slash-formatted application numbers.  This tool sits in front of all
other patent tools and resolves any format into the canonical application number.

Flow
----
    raw input  ->  _normalize_patent_number  ->  (cleaned, type)
                                                      |
                 grant  -> search patentNumber         |
                 pub    -> search earliestPublicationNumber
                 app    -> verify via /meta-data        |
                 ambiguous -> try grant, then app       |
                 unknown   -> error                    v
                                                  application metadata

Role / Module contract
----------------------
- Accepts a single ``patent_number`` string in any common format.
- Returns the application number plus basic metadata (title, dates, status).

Inputs:  ``{"patent_number": "US9629826B2"}``
Outputs: ``{"status": "success", "data": {"applicationNumberText": "14966067", ...}}``

Environment variables
---------------------
- ``USPTO_API_KEY`` --- required for ODP authentication (X-API-KEY header).

Callers
-------
- Any agent or tool chain that needs to resolve a patent identifier before
  calling other USPTO tools (continuations, claims, assignments, etc.).

Usage example
-------------
    from tooluniverse.patent_resolver_tool import PatentResolverTool
    tool = PatentResolverTool({"name": "USPTO_patent_number_to_application"})
    result = tool.run({"patent_number": "US9629826B2"})
"""

# --- Imports ---
import os
import re

import requests
from dotenv import find_dotenv, load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_tool import BaseTool
from .tool_registry import register_tool

# --- Constants ---
load_dotenv(find_dotenv(usecwd=True))

USPTO_API_KEY = os.environ.get("USPTO_API_KEY")
BASE_URL = "https://api.uspto.gov/api/v1"

# Publication numbers: US + 4-digit year + 5-or-more digits + A-kind code (A1, A2, A9)
_PUB_RE = re.compile(r"^US\d{4}\d{5,}A\d$")

# Kind codes for granted patents (B1 = no prior pub, B2 = had prior pub)
_KIND_RE = re.compile(r"^(?:US)?(\d+)B\d?$")


# --- Helpers (private) ---
def _normalize_patent_number(raw: str) -> tuple[str, str]:
    """Clean a user-supplied patent identifier and classify its type.

    Returns (cleaned_number, type_string) where type_string is one of:
    ``'grant'``, ``'application'``, ``'publication'``, ``'ambiguous'``,
    or ``'unknown'``.
    """
    stripped = raw.strip()

    # Detect slash *before* removing punctuation --- it is the only reliable
    # signal that the user typed an application number (e.g. "14/966,067").
    has_slash = "/" in stripped

    # Remove internal spaces and commas so "US 9,629,826 B2" becomes "US9629826B2"
    cleaned = stripped.replace(" ", "").replace(",", "")

    # 1. Publication number --- must check first because it also starts with "US"
    if _PUB_RE.match(cleaned):
        return cleaned, "publication"

    # 2. Slash-formatted application number --- strip to digits only
    if has_slash:
        digits = re.sub(r"\D", "", stripped)
        return digits, "application"

    # 3. Kind-code grant (B1 / B2) --- extract the digit group
    kind_match = _KIND_RE.match(cleaned)
    if kind_match:
        return kind_match.group(1), "grant"

    # 4. Strip any remaining "US" prefix for pure-digit classification
    digits = cleaned.removeprefix("US")

    # 5. Classify by digit count
    if digits.isdigit():
        if len(digits) == 7:
            return digits, "grant"
        if len(digits) == 8:
            return digits, "ambiguous"

    return digits, "unknown"


# --- Public API ---
@register_tool("PatentResolverTool")
class PatentResolverTool(BaseTool):
    """Resolve any patent number format to a USPTO application number."""

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

        # Reuse session with retry --- same resilience pattern as USPTOOpenDataPortalTool
        self.session = requests.Session()
        retry = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=5,
            raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    # -- internal search helpers --

    def _search(self, query: str) -> dict | None:
        """Run a search query and return the first result (full bag item), or None."""
        resp = self.session.get(
            f"{self.base_url}/patent/applications/search",
            headers=self.headers,
            params={"q": query, "limit": 1},
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("patentFileWrapperDataBag", [])
        if not results:
            return None
        # Return the full bag item — applicationNumberText is at this level,
        # not inside applicationMetaData
        return results[0]

    def _get_meta(self, app_number: str) -> dict | None:
        """Fetch application metadata directly by application number."""
        resp = self.session.get(
            f"{self.base_url}/patent/applications/{app_number}/meta-data",
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        bag = resp.json().get("patentFileWrapperDataBag", [])
        if not bag:
            return None
        # Return the full bag item — applicationNumberText is at this level
        return bag[0]

    def _extract(self, bag_item: dict) -> dict:
        """Pull the fields callers need from a full patentFileWrapperDataBag item.

        applicationNumberText lives at the top level of the bag item.
        Everything else lives inside applicationMetaData.
        """
        meta = bag_item.get("applicationMetaData", {})
        return {
            # applicationNumberText is at the bag-item level, NOT inside applicationMetaData
            "applicationNumberText": bag_item.get("applicationNumberText", ""),
            "patentNumber": meta.get("patentNumber", ""),
            "inventionTitle": meta.get("inventionTitle", ""),
            "filingDate": meta.get("filingDate", ""),
            "grantDate": meta.get("grantDate", ""),
            "applicationStatusDescriptionText": meta.get(
                "applicationStatusDescriptionText", ""
            ),
        }

    # -- strategies per number type --

    def _resolve_grant(self, number: str) -> dict | None:
        meta = self._search(f"applicationMetaData.patentNumber:{number}")
        return self._extract(meta) if meta else None

    def _resolve_publication(self, number: str) -> dict | None:
        meta = self._search(f"applicationMetaData.earliestPublicationNumber:{number}")
        return self._extract(meta) if meta else None

    def _resolve_application(self, number: str) -> dict | None:
        meta = self._get_meta(number)
        return self._extract(meta) if meta else None

    def _resolve_ambiguous(self, number: str) -> dict | None:
        """Try grant first (more common), then fall back to application."""
        result = self._resolve_grant(number)
        if result:
            return result
        return self._resolve_application(number)

    # -- public interface --

    def run(self, arguments: dict) -> dict:
        """Accept ``{"patent_number": "..."}`` and return the application metadata."""
        raw = arguments.get("patent_number", "").strip()
        if not raw:
            return self.tool_error(
                "patent_number is required",
                error_type="ValidationError",
                suggestion="Provide a grant, application, or publication number.",
            )

        number, num_type = _normalize_patent_number(raw)

        if num_type == "unknown":
            return self.tool_error(
                f"Unrecognized patent number format: {raw}",
                error_type="ValidationError",
                suggestion=(
                    "Accepted formats: grant (US9629826B2, 9629826), "
                    "application (14/966,067), publication (US20160106718A1)."
                ),
            )

        # Dispatch to the right resolution strategy
        strategy = {
            "grant": self._resolve_grant,
            "publication": self._resolve_publication,
            "application": self._resolve_application,
            "ambiguous": self._resolve_ambiguous,
        }

        try:
            result = strategy[num_type](number)
        except requests.exceptions.RequestException as exc:
            return self.tool_error(
                f"USPTO API request failed: {exc}",
                error_type="NetworkError",
                suggestion="Check USPTO_API_KEY and network connectivity.",
            )

        if not result:
            return self.tool_error(
                f"No application found for {raw} (parsed as {num_type}: {number})",
                error_type="NotFoundError",
                suggestion="Verify the patent number and try again.",
            )

        return {"status": "success", "data": result}
