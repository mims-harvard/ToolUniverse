"""
Wikipedia tools for ToolUniverse using MediaWiki API.

This module provides access to Wikipedia articles, search, and content
extraction using the public MediaWiki API. No API key is required.
"""

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("WikipediaSearchTool")
class WikipediaSearchTool(BaseTool):
    """
    Search Wikipedia articles using MediaWiki API.

    Parameters (arguments):
        query (str): Search query string
        limit (int): Maximum number of results to return (default: 10, max: 50)
        language (str): Wikipedia language code (default: "en")
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://{language}.wikipedia.org/w/api.php"

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query", "").strip()
        limit = arguments.get("limit", 10)
        language = arguments.get("language", "en")

        if not query:
            return {"status": "error", "error": "`query` parameter is required."}

        # Validate limit
        limit = max(1, min(limit, 50))

        api_url = self.base_url.format(language=language)

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "srnamespace": 0,  # Only search in main namespace (articles)
        }

        headers = {
            "User-Agent": "ToolUniverse/1.0 (https://github.com)",
        }

        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                return {
                    "status": "error",
                    "error": f"Wikipedia API error: {data['error']}",
                }

            search_results = data.get("query", {}).get("search", [])
            results = []
            for item in search_results:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "size": item.get("size", 0),
                        "wordcount": item.get("wordcount", 0),
                        "timestamp": item.get("timestamp", ""),
                    }
                )

            return {
                "query": query,
                "language": language,
                "total_results": len(results),
                "results": results,
            }

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network/API error calling Wikipedia",
                "reason": str(e),
            }
        except (ValueError, KeyError) as e:
            return {
                "status": "error",
                "error": "Failed to parse Wikipedia API response",
                "reason": str(e),
            }


@register_tool("WikipediaContentTool")
class WikipediaContentTool(BaseTool):
    """
    Extract content from Wikipedia articles using MediaWiki API.

    Parameters (arguments):
        title (str): Article title (required)
        language (str): Wikipedia language code (default: "en")
        extract_type (str): Type of content - "intro" (first paragraph),
                           "summary" (first few paragraphs), or "full"
                           (entire article) (default: "summary")
        max_chars (int): Maximum characters for summary/extract
            (default: 2000)
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://{language}.wikipedia.org/w/api.php"

    def run(self, arguments=None):
        arguments = arguments or {}
        title = arguments.get("title", "").strip()
        language = arguments.get("language", "en")
        extract_type = arguments.get("extract_type", "summary")
        max_chars = arguments.get("max_chars", 2000)

        if not title:
            return {"status": "error", "error": "`title` parameter is required."}

        api_url = self.base_url.format(language=language)

        # Determine what to extract
        if extract_type == "intro":
            exintro = True
            explaintext = True
        elif extract_type == "summary":
            exintro = True
            explaintext = True
        elif extract_type == "full":
            exintro = False
            explaintext = True
        else:
            exintro = True
            explaintext = True

        exchars = max_chars if extract_type != "full" else None
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info|links",
            "exintro": exintro,
            "explaintext": explaintext,
            "exchars": exchars,
            "format": "json",
            "inprop": "url",
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        headers = {
            "User-Agent": "ToolUniverse/1.0 (https://github.com)",
        }

        try:
            resp = requests.get(api_url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                return {
                    "status": "error",
                    "error": f"Wikipedia API error: {data['error']}",
                }

            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return {"status": "error", "error": f"Article '{title}' not found."}

            # Get first page (should only be one)
            page_id = list(pages.keys())[0]
            page_data = pages[page_id]

            if page_id == "-1":
                return {"status": "error", "error": f"Article '{title}' not found."}

            extract = page_data.get("extract", "")
            fullurl = page_data.get("fullurl", "")
            links = page_data.get("links", [])

            result = {
                "title": page_data.get("title", title),
                "pageid": int(page_id),
                "url": fullurl,
                "content": extract,
                "content_length": len(extract),
                "extract_type": extract_type,
            }

            # Add links if available
            if links:
                # Limit to 20 links
                result["links"] = [link.get("title", "") for link in links[:20]]

            return result

        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network/API error calling Wikipedia",
                "reason": str(e),
            }
        except (ValueError, KeyError) as e:
            return {
                "status": "error",
                "error": "Failed to parse Wikipedia API response",
                "reason": str(e),
            }


@register_tool("WikipediaSummaryTool")
class WikipediaSummaryTool(BaseTool):
    """
    Get a brief summary/introduction from a Wikipedia article.

    This is a convenience tool that extracts just the first
    paragraph(s) of an article.

    Parameters (arguments):
        title (str): Article title (required)
        language (str): Wikipedia language code (default: "en")
        max_chars (int): Maximum characters to return (default: 500)
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.content_tool = WikipediaContentTool(tool_config)

    def run(self, arguments=None):
        arguments = arguments or {}
        # Override extract_type to always get intro
        arguments["extract_type"] = "intro"
        arguments["max_chars"] = arguments.get("max_chars", 500)
        return self.content_tool.run(arguments)
