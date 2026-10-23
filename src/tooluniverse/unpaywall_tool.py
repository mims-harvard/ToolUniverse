import requests
import re
from urllib.parse import quote, unquote

from .base_tool import BaseTool
from .tool_registry import register_tool

DEFAULT_EMAIL = "tools@tooluniverse.org"


@register_tool("UnpaywallTool")
class UnpaywallTool(BaseTool):
    """
    Query Unpaywall by DOI to check open-access status, OA locations,
    and retrieve full-text URLs.
    """

    def __init__(self, tool_config, base_url="https://api.unpaywall.org/v2/"):
        super().__init__(tool_config)
        self.base_url = base_url.rstrip("/") + "/"

    def run(self, arguments):
        tool_name = self.tool_config.get("name", "")
        unknown = sorted(set(arguments) - {"doi", "email"})
        if unknown:
            return {
                "status": "error",
                "error": f"Unrecognized parameter(s): {', '.join(unknown)}",
            }
        doi, doi_error = self._normalize_doi(arguments.get("doi"))
        email = arguments.get("email")

        if doi_error:
            return {"status": "error", "error": doi_error}
        assert doi is not None
        if email is not None and (
            not isinstance(email, str)
            or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip())
        ):
            return {"status": "error", "error": "email must be a valid email address"}
        email = email.strip() if email else None

        if tool_name == "Unpaywall_get_full_text_url":
            return self._get_full_text_url(doi, email or DEFAULT_EMAIL)

        # Default: Unpaywall_check_oa_status (original behavior)
        if not email:
            return {
                "status": "error",
                "error": "`email` parameter is required for Unpaywall.",
            }
        return self._check_oa_status(doi, email)

    @staticmethod
    def _normalize_doi(value):
        if not isinstance(value, str) or not value.strip():
            return None, "`doi` must be a non-empty string."
        doi = unquote(value.strip())
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
        doi = doi.strip().rstrip(".")
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi, flags=re.IGNORECASE):
            return None, "doi must be a valid DOI such as 10.7554/eLife.01567"
        return doi.lower(), None

    def _call_api(self, doi, email):
        """Shared API call logic."""
        url = f"{self.base_url}{quote(doi, safe='/')}"
        params = {"email": email}
        try:
            response = requests.get(url, params=params, timeout=20)
        except requests.RequestException as e:
            return None, {
                "status": "error",
                "error": "Network error calling Unpaywall API",
                "reason": str(e),
            }

        if response.status_code == 404:
            return None, {
                "status": "error",
                "error": f"DOI not found in Unpaywall: {doi}",
            }

        if response.status_code != 200:
            return None, {
                "status": "error",
                "error": f"Unpaywall API error {response.status_code}",
                "reason": response.reason,
            }

        try:
            data = response.json()
        except ValueError as exc:
            return None, {
                "status": "error",
                "error": f"Unpaywall returned invalid JSON: {exc}",
            }
        if not isinstance(data, dict):
            return None, {
                "status": "error",
                "error": "Unpaywall returned an unexpected response shape",
            }
        returned_doi = data.get("doi")
        if not isinstance(returned_doi, str) or returned_doi.lower() != doi.lower():
            return None, {
                "status": "error",
                "error": "Unpaywall returned a different DOI than requested",
                "requested_doi": doi,
                "returned_doi": returned_doi,
            }
        for field in ("oa_locations", "oa_locations_embargoed"):
            value = data.get(field)
            if value is not None and (
                not isinstance(value, list)
                or any(not isinstance(location, dict) for location in value)
            ):
                return None, {
                    "status": "error",
                    "error": f"Unpaywall returned malformed {field}",
                }
        return data, None

    def _check_oa_status(self, doi, email):
        """Original OA status check."""
        data, err = self._call_api(doi, email)
        if err:
            return err

        return {
            "status": "success",
            "data": {
                "is_oa": data.get("is_oa"),
                "oa_status": data.get("oa_status"),
                "best_oa_location": data.get("best_oa_location"),
                "oa_locations": data.get("oa_locations"),
                "journal_is_oa": data.get("journal_is_oa"),
                "journal_issn_l": data.get("journal_issn_l"),
                "journal_issns": data.get("journal_issns"),
                "doi": data.get("doi"),
                "title": data.get("title"),
                "year": data.get("year"),
                "publisher": data.get("publisher"),
                "url": data.get("url"),
                "doi_url": data.get("doi_url"),
                "genre": data.get("genre"),
                "published_date": data.get("published_date"),
                "updated": data.get("updated"),
                "has_repository_copy": data.get("has_repository_copy"),
                "is_paratext": data.get("is_paratext"),
                "journal_is_in_doaj": data.get("journal_is_in_doaj"),
                "first_oa_location": data.get("first_oa_location"),
                "oa_locations_embargoed": data.get("oa_locations_embargoed") or [],
                "authors": data.get("z_authors") or [],
                "data_standard": data.get("data_standard"),
                "record": data,
            },
            "metadata": {
                "source": "Unpaywall",
                "email": email,
                "requested_doi": doi,
                "returned_doi_verified": True,
                "source_record_complete": True,
                "oa_location_count": len(data.get("oa_locations") or []),
                "embargoed_oa_location_count": len(
                    data.get("oa_locations_embargoed") or []
                ),
            },
        }

    @staticmethod
    def _extract_oa_location(loc):
        """Extract relevant fields from a single OA location dict."""
        if not loc or not isinstance(loc, dict):
            return None
        return dict(loc)

    def _get_full_text_url(self, doi, email):
        """Retrieve full-text PDF and landing page URLs for a DOI."""
        data, err = self._call_api(doi, email)
        if err:
            return err

        best = data.get("best_oa_location") or {}
        all_locations = [
            extracted
            for loc in (data.get("oa_locations") or [])
            if (extracted := self._extract_oa_location(loc))
        ]
        embargoed_locations = [
            extracted
            for loc in (data.get("oa_locations_embargoed") or [])
            if (extracted := self._extract_oa_location(loc))
        ]

        return {
            "status": "success",
            "data": {
                "doi": data.get("doi"),
                "title": data.get("title"),
                "is_oa": data.get("is_oa", False),
                "oa_status": data.get("oa_status"),
                "best_pdf_url": best.get("url_for_pdf"),
                "best_landing_page_url": best.get("url_for_landing_page"),
                "best_oa_url": best.get("url"),
                "best_oa_host_type": best.get("host_type"),
                "best_oa_version": best.get("version"),
                "best_oa_license": best.get("license"),
                "all_oa_locations": all_locations,
                "embargoed_oa_locations": embargoed_locations,
                "journal_name": data.get("journal_name"),
                "publisher": data.get("publisher"),
                "year": data.get("year"),
                "record": data,
            },
            "metadata": {
                "source": "Unpaywall",
                "api_version": "v2",
                "total_oa_locations": len(all_locations),
                "total_embargoed_oa_locations": len(embargoed_locations),
                "requested_doi": doi,
                "returned_doi_verified": True,
                "source_record_complete": True,
            },
        }
