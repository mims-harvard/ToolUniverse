import html
import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DBLPTool")
class DBLPTool(BaseTool):
    """
    Search DBLP Computer Science Bibliography for publications.
    """

    _TYPE_MAP = {
        "Conference and Workshop Papers": "conference-paper",
        "Journal Articles": "journal-article",
        "Parts in Books or Collections": "book-chapter",
        "Books and Theses": "book-or-thesis",
        "Editorship": "editorship",
        "Reference Works": "reference-work",
        "Informal and Other Publications": "informal-publication",
        "Data and Artifacts": "data-or-artifact",
    }

    def __init__(
        self,
        tool_config,
        base_url="https://dblp.org/search/publ/api",
    ):
        super().__init__(tool_config)
        self.base_url = base_url

    def run(self, arguments):
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "`query` parameter is required."}
        limit = arguments.get("limit", 10)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 1000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 1000",
                "parameter": "limit",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
                "parameter": "offset",
            }
        return self._search(query, limit, offset)

    def _search(self, query, limit, offset):
        params = {
            "q": query,
            "h": limit,
            "f": offset,
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

        hits_data = response.json().get("result", {}).get("hits", {})
        hits = hits_data.get("hit", [])
        if isinstance(hits, dict):
            hits = [hits]
        try:
            total_matches = int(hits_data.get("@total", len(hits)))
        except (TypeError, ValueError):
            total_matches = len(hits)
        try:
            accessible_results = int(hits_data.get("@computed", total_matches))
        except (TypeError, ValueError):
            accessible_results = total_matches
        try:
            first = int(hits_data.get("@first", offset))
        except (TypeError, ValueError):
            first = offset
        returned = len(hits)
        has_more = first + returned < accessible_results
        pagination = {
            "total_matches": total_matches,
            "accessible_results": accessible_results,
            "upstream_truncated": accessible_results < total_matches,
            "returned": returned,
            "offset": first,
            "requested_offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": first + returned if returned and has_more else None,
            "truncated": has_more or accessible_results < total_matches,
            "warning": (
                "DBLP matched more records than its search engine computed for "
                "this query. Pagination can traverse only accessible_results; "
                "refine the query to retrieve records outside that ranked window."
                if accessible_results < total_matches
                else None
            ),
        }
        results = []
        for hit in hits:
            info = hit.get("info", {})

            # Extract title
            title = info.get("title")
            if isinstance(title, str):
                title = html.unescape(title)

            # Extract author information
            authors = info.get("authors", {}).get("author", [])
            if isinstance(authors, dict):
                authors = [authors]
            elif isinstance(authors, str):
                authors = [{"text": authors}]
            normalized_authors = []
            for author in authors if isinstance(authors, list) else []:
                if isinstance(author, dict):
                    author = dict(author)
                    if isinstance(author.get("text"), str):
                        author["text"] = html.unescape(author["text"])
                    normalized_authors.append(author)
                elif isinstance(author, str):
                    normalized_authors.append({"text": html.unescape(author)})
            authors = normalized_authors

            # Extract year
            year = info.get("year")
            if year and isinstance(year, str) and year.isdigit():
                year = int(year)

            # Extract journal/conference information
            venue = info.get("venue")
            if isinstance(venue, list):
                venue = venue[0] if venue else None
            if isinstance(venue, str):
                venue = html.unescape(venue)

            # Extract URL
            url = info.get("url")

            # Extract electronic edition link
            ee = info.get("ee")

            # Extract DOI (from ee field)
            doi = None
            ee_values = ee if isinstance(ee, list) else [ee]
            for link in ee_values:
                if isinstance(link, str) and "doi.org/" in link:
                    doi = link.split("doi.org/", 1)[1]
                    break

            # DBLP does not supply these facts. None means unknown/unavailable;
            # zero/False would incorrectly assert zero citations or closed access.
            citations = None
            open_access = None
            keywords = []
            publication_type = info.get("type")
            article_type = self._TYPE_MAP.get(publication_type)
            if article_type is None and isinstance(publication_type, str):
                article_type = publication_type.lower().replace(" ", "-")
            publisher = info.get("publisher") or None
            abstract = None

            results.append(
                {
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "year": year,
                    "venue": venue,
                    "url": url,
                    "ee": ee,
                    "doi": doi,
                    "citations": citations,
                    "open_access": open_access,
                    "keywords": keywords,
                    "article_type": article_type,
                    "publication_type": publication_type,
                    "publisher": publisher,
                    "source": "DBLP",
                    "unavailable_fields": [
                        "abstract",
                        "citation_count",
                        "open_access_status",
                        "keywords",
                    ],
                    "search_pagination": dict(pagination),
                    "data_quality": {
                        "has_abstract": False,
                        "has_authors": bool(authors),
                        "has_journal": bool(venue),
                        "has_year": bool(year),
                        "has_doi": bool(doi),
                        "has_citations": False,
                        "has_open_access_status": False,
                        "has_keywords": False,
                        "has_url": bool(url),
                        "has_publication_type": bool(publication_type),
                    },
                }
            )

        return results
