import requests
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("BioRxivTool")
class BioRxivTool(BaseTool):
    """
    Get bioRxiv or medRxiv preprint metadata by DOI.

    This tool retrieves full metadata for a specific preprint using the bioRxiv API.
    For searching preprints by keywords, use EuropePMC_search_articles with 'SRC:PPR' filter instead.

    Arguments:
        doi (str): bioRxiv or medRxiv DOI (e.g., '10.1101/2023.12.01.569554' or '2023.12.01.569554')
        server (str): Server name - 'biorxiv' or 'medrxiv' (default: 'biorxiv')
    """

    def __init__(
        self,
        tool_config,
        base_url="https://api.biorxiv.org/details",
    ):
        super().__init__(tool_config)
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def run(self, arguments=None):
        arguments = arguments or {}
        doi = arguments.get("doi")
        server = arguments.get("server", "biorxiv")

        if not doi:
            return {
                "status": "error",
                "error": "`doi` parameter is required. Provide a bioRxiv DOI like '10.1101/2023.12.01.569554' or '2023.12.01.569554'.",
                "data": None,
            }

        # Validate server
        if server not in ("biorxiv", "medrxiv"):
            return {
                "status": "error",
                "error": f"Invalid server '{server}'. Must be 'biorxiv' or 'medrxiv'.",
                "data": None,
            }

        # Normalize DOI - allow partial DOIs like "2023.12.01.569554"
        doi = str(doi).strip()
        if not doi.startswith("10.1101/"):
            doi = f"10.1101/{doi}"

        # API format: /details/{server}/{doi}/na/json
        url = f"{self.base_url}/{server}/{doi}/na/json"

        try:
            resp = request_with_retry(
                self.session, "GET", url, timeout=10, max_attempts=2
            )

            if resp.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Preprint not found with DOI: {doi}. Check the DOI is correct and the paper exists on {server}.",
                    "data": None,
                }

            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"{server} API returned status {resp.status_code}",
                    "reason": resp.reason,
                    "data": None,
                }

            data = resp.json()
            collection = data.get("collection", [])

            if not collection:
                return {
                    "status": "error",
                    "error": "No data returned from bioRxiv API",
                    "data": None,
                }

            # Get first (and only) result
            item = collection[0]

            # Parse authors string into list
            authors_str = item.get("authors", "")
            if isinstance(authors_str, str) and authors_str:
                authors = [a.strip() for a in authors_str.split(";") if a.strip()]
            else:
                authors = []

            # Build response with comprehensive metadata
            doi_val = item.get("doi")
            result = {
                "doi": doi_val,
                "title": item.get("title"),
                "authors": authors,
                "author_corresponding": item.get("author_corresponding"),
                "author_corresponding_institution": item.get(
                    "author_corresponding_institution"
                ),
                "abstract": item.get("abstract"),
                "date": item.get("date"),
                "version": item.get("version"),
                "type": item.get("type"),
                "license": item.get("license"),
                "category": item.get("category"),
                "published": item.get("published") or None,
                "url": f"https://www.{server}.org/content/{doi_val}"
                if doi_val
                else None,
                "pdf_url": f"https://www.{server}.org/content/{doi_val}.full.pdf"
                if doi_val
                else None,
                "xml_url": item.get("jatsxml"),
                "server": server,
            }

            return {"status": "success", "data": result}

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": f"Network error retrieving preprint: {str(e)}",
                "data": None,
            }
        except ValueError:
            return {
                "status": "error",
                "error": f"{server} API returned invalid JSON response",
                "data": None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to retrieve preprint: {str(e)}",
                "data": None,
            }
