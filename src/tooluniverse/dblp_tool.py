import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DBLPTool")
class DBLPTool(BaseTool):
    """
    Search DBLP Computer Science Bibliography for publications.
    """

    def __init__(
        self,
        tool_config,
        base_url="https://dblp.org/search/publ/api",
    ):
        super().__init__(tool_config)
        self.base_url = base_url

    def run(self, arguments):
        query = arguments.get("query")
        limit = int(arguments.get("limit", 10))
        if not query:
            return {"status": "error", "error": "`query` parameter is required."}
        return self._search(query, limit)

    def _search(self, query, limit):
        params = {
            "q": query,
            "h": max(1, min(limit, 100)),
            "format": "json",
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=20)
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network error calling DBLP API",
                "reason": str(e),
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"DBLP API error {response.status_code}",
                "reason": response.reason,
            }

        hits = response.json().get("result", {}).get("hits", {}).get("hit", [])
        results = []
        for hit in hits:
            info = hit.get("info", {})

            # Extract title
            title = info.get("title")

            # Extract author information
            authors = info.get("authors", {}).get("author", [])
            if isinstance(authors, dict):
                authors = [authors]

            # Extract year
            year = info.get("year")
            if year and isinstance(year, str) and year.isdigit():
                year = int(year)

            # Extract journal/conference information
            venue = info.get("venue")
            if isinstance(venue, list):
                venue = venue[0] if venue else None

            # Extract URL
            url = info.get("url")

            # Extract electronic edition link
            ee = info.get("ee")

            # Extract DOI (from ee field)
            doi = None
            if ee and isinstance(ee, str) and "doi.org" in ee:
                doi = ee

            # Extract citation count (DBLP usually doesn't provide this)
            citations = 0

            # Open access status (DBLP usually doesn't provide this)
            open_access = False

            # Extract keywords (DBLP usually doesn't provide this)
            keywords = []

            # Extract article type
            article_type = "conference-paper"  # DBLP is mainly conference papers

            # Extract publisher
            publisher = "Unknown"

            # Handle missing abstract
            abstract = (
                "Abstract not available"  # DBLP usually doesn't provide abstracts
            )

            results.append(
                {
                    "title": title or "Title not available",
                    "abstract": abstract,
                    "authors": (
                        authors if authors else "Author information not available"
                    ),
                    "year": year,
                    "venue": venue or "Journal information not available",
                    "url": url or "URL not available",
                    "ee": ee or "Electronic edition not available",
                    "doi": doi or "DOI not available",
                    "citations": citations,
                    "open_access": open_access,
                    "keywords": keywords if keywords else "Keywords not available",
                    "article_type": article_type,
                    "publisher": publisher,
                    "source": "DBLP",
                    "data_quality": {
                        "has_abstract": False,  # DBLP usually doesn't provide abstracts
                        "has_authors": bool(authors),
                        "has_journal": bool(venue),
                        "has_year": bool(year),
                        "has_doi": bool(doi),
                        "has_citations": False,  # DBLP usually doesn't provide citation count
                        "has_keywords": False,  # DBLP usually doesn't provide keywords
                        "has_url": bool(url),
                    },
                }
            )

        return results
