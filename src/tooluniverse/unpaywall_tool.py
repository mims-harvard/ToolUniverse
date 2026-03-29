import requests
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
        doi = arguments.get("doi")
        email = arguments.get("email")

        if not doi:
            return {"status": "error", "error": "`doi` parameter is required."}

        if tool_name == "Unpaywall_get_full_text_url":
            return self._get_full_text_url(doi, email or DEFAULT_EMAIL)

        # Default: Unpaywall_check_oa_status (original behavior)
        if not email:
            return {
                "status": "error",
                "error": "`email` parameter is required for Unpaywall.",
            }
        return self._check_oa_status(doi, email)

    def _call_api(self, doi, email):
        """Shared API call logic."""
        url = f"{self.base_url}{doi}"
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

        return response.json(), None

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
            },
            "metadata": {"source": "Unpaywall", "email": email},
        }

    @staticmethod
    def _extract_oa_location(loc):
        """Extract relevant fields from a single OA location dict."""
        if not loc or not isinstance(loc, dict):
            return None
        return {
            "url": loc.get("url"),
            "url_for_pdf": loc.get("url_for_pdf"),
            "url_for_landing_page": loc.get("url_for_landing_page"),
            "host_type": loc.get("host_type"),
            "version": loc.get("version"),
            "license": loc.get("license"),
            "is_best": loc.get("is_best", False),
        }

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
                "journal_name": data.get("journal_name"),
                "publisher": data.get("publisher"),
                "year": data.get("year"),
            },
            "metadata": {
                "source": "Unpaywall",
                "api_version": "v2",
                "total_oa_locations": len(all_locations),
            },
        }
