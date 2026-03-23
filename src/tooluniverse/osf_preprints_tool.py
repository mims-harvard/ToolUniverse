import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("OSFPreprintsTool")
class OSFPreprintsTool(BaseTool):
    """
    Search OSF Preprints via OSF API v2 filters.

    Parameters (arguments):
        query (str): Query string
        max_results (int): Max results (default 10, max 100)
        provider (str): Optional preprint provider (e.g., 'osf', 'psyarxiv')
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://api.osf.io/v2/preprints/"

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query")
        max_results = int(arguments.get("max_results", 10))
        provider = arguments.get("provider")

        if not query:
            return {"error": "`query` parameter is required."}

        params = {
            "page[size]": max(1, min(max_results, 100)),
            "filter[title]": query,
        }
        if provider:
            params["filter[provider]"] = provider

        try:
            resp = requests.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {"error": "Network/API error calling OSF", "reason": str(e)}
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "error": "Failed to decode OSF response as JSON",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "OSF API may be under maintenance. Retry in a few minutes.",
            }

        results = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            title = attrs.get("title")
            date_published = attrs.get("date_published")
            is_published = attrs.get("is_published")
            doi = attrs.get("doi")
            links_obj = item.get("links", {})
            url = links_obj.get("html") or links_obj.get("self")

            results.append(
                {
                    "title": title,
                    "date_published": date_published,
                    "published": is_published,
                    "doi": doi,
                    "url": url,
                    "source": "OSF Preprints",
                }
            )

        return results
