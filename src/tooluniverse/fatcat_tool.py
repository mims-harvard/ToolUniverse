import requests
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse
from .base_tool import BaseTool
from .tool_registry import register_tool


class FatcatResultParser(HTMLParser):
    """Parse Fatcat search results from HTML."""

    def __init__(self):
        super().__init__()
        self.results = []
        self.current_result = None
        self.in_title = False
        self.title_text = []
        self.upstream_next_offset = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Look for release links
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            parsed = urlparse(href)
            next_values = parse_qs(parsed.query).get("offset", [])
            if next_values:
                try:
                    self.upstream_next_offset = int(next_values[0])
                except (TypeError, ValueError):
                    pass
            # Match pattern: /fatcat/release/{release_id}
            if href.startswith("/fatcat/release/") and len(href.split("/")) == 4:
                release_id = href.split("/")[-1]
                # Skip lookup links
                if release_id != "lookup" and release_id != "search":
                    self.current_result = {
                        "release_id": release_id,
                        "url": f"https://scholar.archive.org{href}",
                    }
                    self.in_title = True
                    self.title_text = []

    def handle_data(self, data):
        if self.in_title:
            self.title_text.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.in_title:
            self.in_title = False
            if self.current_result and self.title_text:
                title = " ".join(filter(None, self.title_text))
                if title and len(title) > 3:  # Filter out very short titles
                    self.current_result["title"] = title
                    self.results.append(self.current_result)
            self.current_result = None
            self.title_text = []


class FatcatMetadataParser(HTMLParser):
    """Extract metadata from Fatcat release page meta tags."""

    def __init__(self):
        super().__init__()
        self.metadata = {}
        self.authors = []

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs_dict = dict(attrs)
            name = attrs_dict.get("name", "")
            content = attrs_dict.get("content", "")

            # Extract various metadata fields
            if name == "citation_author":
                self.authors.append(content)
            elif name == "citation_publication_date":
                # Try to extract year
                try:
                    self.metadata["year"] = (
                        int(content.split("-")[0]) if content else None
                    )
                except (ValueError, IndexError):
                    pass
            elif name == "citation_doi":
                self.metadata["doi"] = content
            elif name == "citation_journal_title":
                self.metadata["journal"] = content
            elif name == "citation_publisher":
                self.metadata["publisher"] = content
            elif name == "abstract":
                self.metadata["abstract"] = content
            elif name == "citation_pdf_url":
                self.metadata["pdf_url"] = content


@register_tool("FatcatScholarTool")
class FatcatScholarTool(BaseTool):
    """
    Search Internet Archive Scholar via Fatcat releases search.

    Uses web scraping of the scholar.archive.org interface to retrieve
    bibliographic information about research papers and publications.

    Parameters (arguments):
        query (str): Query string
        max_results (int): Max results (default 10, max 100)
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://scholar.archive.org/fatcat/search"

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            error_msg = "`query` parameter is required."
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}
        query = query.strip()

        max_results = arguments.get("max_results", 10)
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 10
        ):
            error_msg = "max_results must be an integer from 1 to 10"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}
        offset = arguments.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            error_msg = "offset must be a non-negative integer"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}

        limit = max_results

        params = {
            "q": query,
            "entity_type": "releases",
            "offset": offset,
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            error_msg = f"Network/API error calling Fatcat: {str(e)}"
            return {
                "status": "error",
                "data": {
                    "error": "Network/API error calling Fatcat",
                    "reason": str(e),
                },
                "error": error_msg,
            }

        # Parse HTML to extract results
        try:
            parser = FatcatResultParser()
            parser.feed(resp.text)
            raw_results = parser.results
        except Exception as e:
            error_msg = f"Failed to parse Fatcat search results: {str(e)}"
            return {"status": "error", "data": {"error": error_msg}, "error": error_msg}

        # The Scholar HTML endpoint currently returns 25 records at a time and
        # ignores the legacy ``limit`` parameter.  Expose a smaller local page
        # so enrichment remains bounded, while keeping every record reachable
        # through offset navigation.
        page_records = raw_results[:limit]
        has_more = len(raw_results) > limit or parser.upstream_next_offset is not None

        # Fetch detailed metadata for every result on the requested local page.
        # Failures are recorded per item and in aggregate rather than silently
        # turning unavailable metadata into apparently genuine null fields.
        results = []
        metadata_fetch_failures = 0

        for r in page_records:
            result = {
                "title": r.get("title", ""),
                "authors": [],
                "year": None,
                "doi": None,
                "journal": None,
                "publisher": None,
                "abstract": None,
                "pdf_url": None,
                "url": r.get("url", ""),
                "source": "Fatcat/IA Scholar",
                "metadata_complete": False,
                "metadata_error": None,
            }

            # Fetch detailed metadata from release page
            try:
                release_resp = requests.get(r["url"], timeout=10)
                if release_resp.status_code == 200:
                    meta_parser = FatcatMetadataParser()
                    meta_parser.feed(release_resp.text)

                    # Update result with fetched metadata
                    result["authors"] = meta_parser.authors
                    result["year"] = meta_parser.metadata.get("year")
                    result["doi"] = meta_parser.metadata.get("doi")
                    result["journal"] = meta_parser.metadata.get("journal")
                    result["publisher"] = meta_parser.metadata.get("publisher")
                    result["abstract"] = meta_parser.metadata.get("abstract")
                    result["pdf_url"] = meta_parser.metadata.get("pdf_url")
                    result["metadata_complete"] = True
                else:
                    metadata_fetch_failures += 1
                    result["metadata_error"] = (
                        f"release page returned HTTP {release_resp.status_code}"
                    )
            except Exception as e:
                metadata_fetch_failures += 1
                result["metadata_error"] = str(e)

            results.append(result)

        returned = len(results)
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "returned": returned,
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": offset + returned if has_more else None,
                "total_results": None,
                "total_results_is_known": False,
                "complete": not has_more,
                "metadata_fetch_failures": metadata_fetch_failures,
                "metadata_complete_for_all_returned": metadata_fetch_failures == 0,
                "pagination_scope": "ia_scholar_html_offset_with_local_page",
            },
        }
