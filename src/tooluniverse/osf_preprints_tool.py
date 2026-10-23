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
        max_results = arguments.get("max_results", 10)
        page = arguments.get("page", 1)
        provider = arguments.get("provider")
        search_field = arguments.get("search_field", "title")

        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "`query` parameter is required."}
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 100
        ):
            return {
                "status": "error",
                "error": "max_results must be an integer between 1 and 100",
                "parameter": "max_results",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "error",
                "error": "page must be an integer greater than or equal to 1",
                "parameter": "page",
            }
        if search_field not in {"title", "description"}:
            return {
                "status": "error",
                "error": "search_field must be one of: title, description",
                "parameter": "search_field",
            }

        params = {
            "page[size]": max_results,
            # OSF uses the bare `page` parameter. `page[number]` is silently
            # ignored even though this is otherwise a JSON:API response.
            "page": page,
            f"filter[{search_field}]": query,
        }
        if provider:
            params["filter[provider]"] = provider

        try:
            resp = requests.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network/API error calling OSF",
                "reason": str(e),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "status": "error",
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
            doi = attrs.get("doi")
            if not doi:
                doi_url = links_obj.get("preprint_doi")
                if isinstance(doi_url, str):
                    doi = doi_url.removeprefix("https://doi.org/")
            relationships = item.get("relationships", {})
            provider_data = (
                relationships.get("provider", {}).get("data", {})
                if isinstance(relationships, dict)
                else {}
            )

            results.append(
                {
                    "id": item.get("id"),
                    "title": title,
                    "description": attrs.get("description"),
                    "date_published": date_published,
                    "published": is_published,
                    "doi": doi,
                    "url": url,
                    "provider": provider_data.get("id"),
                    "source": "OSF Preprints",
                }
            )

        links = data.get("links", {}) if isinstance(data, dict) else {}
        link_meta = links.get("meta", {}) if isinstance(links, dict) else {}
        total = link_meta.get("total") if isinstance(link_meta, dict) else None
        total_is_exact = isinstance(total, int) and not isinstance(total, bool)
        returned = len(results)
        next_url = links.get("next") if isinstance(links, dict) else None
        has_more = isinstance(next_url, str) and bool(next_url)
        per_page = link_meta.get("per_page", max_results)
        if isinstance(per_page, bool) or not isinstance(per_page, int) or per_page < 1:
            per_page = max_results
        total_pages = (total + per_page - 1) // per_page if total_is_exact else None
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "returned": returned,
                "total_results": total if total_is_exact else None,
                "total_results_is_exact": total_is_exact,
                "page": page,
                "page_size": per_page,
                "total_pages": total_pages,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
                "next_url": next_url if has_more else None,
                "truncated": page > 1 or has_more,
                "result_set_complete": bool(
                    total_is_exact and page == 1 and returned == total
                ),
                "search_field": search_field,
                "provider_filter": provider,
                "pagination_scope": "osf_bare_page_jsonapi_total",
            },
        }
