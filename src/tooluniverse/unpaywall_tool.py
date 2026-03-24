import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("UnpaywallTool")
class UnpaywallTool(BaseTool):
    """
    Query Unpaywall by DOI to check open-access status and OA locations.
    Requires a contact email.
    """

    def __init__(self, tool_config, base_url="https://api.unpaywall.org/v2/"):
        super().__init__(tool_config)
        self.base_url = base_url.rstrip("/") + "/"

    def run(self, arguments):
        doi = arguments.get("doi")
        email = arguments.get("email")  # required by Unpaywall
        if not doi:
            return {"status": "error", "error": "`doi` parameter is required."}
        if not email:
            return {
                "status": "error",
                "error": "`email` parameter is required for Unpaywall.",
            }
        return self._lookup(doi, email)

    def _lookup(self, doi, email):
        url = f"{self.base_url}{doi}"
        params = {"email": email}
        try:
            response = requests.get(
                url,
                params=params,
                timeout=20,
            )
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network error calling Unpaywall API",
                "reason": str(e),
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"Unpaywall API error {response.status_code}",
                "reason": response.reason,
            }

        data = response.json()
        result = {
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
        }
        return result
