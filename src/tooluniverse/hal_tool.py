import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("HALTool")
class HALTool(BaseTool):
    """
    Search the French HAL open archive via its public API.

    Arguments:
        query (str): Search term (Lucene syntax)
        max_results (int): Max results to return (default 10, max 100)
    """

    def __init__(
        self,
        tool_config,
        base_url="https://api.archives-ouvertes.fr/search/",
    ):
        super().__init__(tool_config)
        self.base_url = base_url.rstrip("/") + "/"

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query")
        max_results = int(arguments.get("max_results", 10))
        if not query:
            return {"error": "`query` parameter is required."}
        return self._search(query, max_results)

    def _search(self, query, max_results):
        params = {
            "q": query,
            "wt": "json",
            "rows": max(1, min(max_results, 100)),
            "fl": (
                "title_s,authFullName_s,producedDateY_i,uri_s,doiId_s,"
                "docType_s,abstract_s,source_s"
            ),
        }
        try:
            resp = requests.get(f"{self.base_url}", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {"error": "Network/API error calling HAL", "reason": str(e)}
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "error": "Failed to decode HAL response as JSON",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "HAL API may be under maintenance. Retry in a few minutes.",
            }

        docs = data.get("response", {}).get("docs", [])
        results = []
        for d in docs:
            title = d.get("title_s") or [None]
            if isinstance(title, list):
                title = title[0]
            authors = d.get("authFullName_s") or []
            year = d.get("producedDateY_i")
            doi = d.get("doiId_s")
            url = d.get("uri_s")
            abstract = d.get("abstract_s")
            if isinstance(abstract, list):
                abstract = abstract[0]
            source = d.get("source_s")
            results.append(
                {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "doi": doi,
                    "url": url,
                    "abstract": abstract,
                    "source": source,
                }
            )

        return results
