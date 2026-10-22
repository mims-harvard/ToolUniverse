import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DOAJTool")
class DOAJTool(BaseTool):
    """
    Search DOAJ (Directory of Open Access Journals) articles and journals.

    Parameters (arguments):
        query (str): Query string (Lucene syntax supported by DOAJ)
        max_results (int): Max number of results (default 10, max 100)
        type (str): "articles" or "journals" (default: "articles")
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://doaj.org/api/search"

    def run(self, arguments=None):
        arguments = arguments or {}
        query = arguments.get("query")
        search_type = arguments.get("type", "articles")
        raw_max_results = arguments.get("max_results", 10)
        page = arguments.get("page", 1)
        if (
            isinstance(raw_max_results, bool)
            or not isinstance(raw_max_results, int)
            or not 1 <= raw_max_results <= 100
        ):
            return {
                "status": "error",
                "error": "max_results must be an integer between 1 and 100",
            }
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            return {
                "status": "error",
                "error": "page must be a positive integer (1-based)",
            }
        max_results = raw_max_results

        if not query:
            return {"status": "error", "error": "`query` parameter is required."}

        if search_type not in ["articles", "journals"]:
            return {
                "status": "error",
                "error": "`type` must be 'articles' or 'journals'.",
            }

        endpoint = f"{self.base_url}/{search_type}/{query}"
        params = {
            "pageSize": max_results,
            "page": page,
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network/API error calling DOAJ",
                "reason": str(e),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "status": "error",
                "error": "Failed to decode DOAJ response as JSON",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "DOAJ API may be under maintenance. Retry in a few minutes.",
            }

        results = data.get("results", [])
        items = []
        if search_type == "articles":
            for r in results:
                b = r.get("bibjson", {})
                title = b.get("title")

                # Extract year
                year = None
                try:
                    year = int((b.get("year") or 0))
                except Exception:
                    year = b.get("year")

                # Extract author information
                authors = [a.get("name") for a in b.get("author", []) if a.get("name")]

                # Extract DOI
                doi = None
                for i in b.get("identifier", []):
                    if i.get("type") == "doi":
                        doi = i.get("id")
                        break

                # Extract URL
                url = None
                for link_item in b.get("link", []):
                    if link_item.get("type") == "fulltext" or link_item.get("url"):
                        url = link_item.get("url")
                        break

                # Extract journal information
                journal = (b.get("journal") or {}).get("title")

                # Extract abstract
                abstract = b.get("abstract")
                if abstract and isinstance(abstract, str):
                    # Clean HTML tags
                    import re

                    abstract = re.sub(r"<[^>]+>", "", abstract)
                    abstract = abstract.strip()

                # Extract keywords
                keywords = []
                subject_list = b.get("subject", [])
                if isinstance(subject_list, list):
                    for subject in subject_list:
                        if isinstance(subject, dict):
                            term = subject.get("term", "")
                            if term:
                                keywords.append(term)
                        elif isinstance(subject, str):
                            keywords.append(subject)

                # Extract citation count (DOAJ usually doesn't provide this)
                citations = 0

                # Open access status (DOAJ is all open access)
                open_access = True

                # Extract article type
                article_type = b.get("type", "journal-article")

                # Extract publisher
                publisher = (b.get("journal") or {}).get("publisher")

                # Handle missing abstract
                if not abstract:
                    abstract = "Abstract not available"

                items.append(
                    {
                        "title": title or "Title not available",
                        "abstract": abstract,
                        "authors": (
                            authors if authors else "Author information not available"
                        ),
                        "year": year,
                        "doi": doi or "DOI not available",
                        "venue": journal or "Journal information not available",
                        "url": url or "URL not available",
                        "citations": citations,
                        "open_access": open_access,
                        "keywords": keywords if keywords else "Keywords not available",
                        "article_type": article_type,
                        "publisher": publisher or "Publisher information not available",
                        "source": "DOAJ",
                        "data_quality": {
                            "has_abstract": bool(
                                abstract and abstract != "Abstract not available"
                            ),
                            "has_authors": bool(authors),
                            "has_journal": bool(journal),
                            "has_year": bool(year),
                            "has_doi": bool(doi),
                            "has_citations": False,  # DOAJ usually doesn't provide citation count
                            "has_keywords": bool(keywords),
                            "has_url": bool(url),
                        },
                    }
                )
        else:
            for r in results:
                b = r.get("bibjson", {})
                title = b.get("title")
                publisher = b.get("publisher")
                eissn = None
                pissn = None
                for i in b.get("identifier", []):
                    if i.get("type") == "eissn":
                        eissn = i.get("id")
                    if i.get("type") == "pissn":
                        pissn = i.get("id")
                homepage_url = None
                for link_item in b.get("link", []):
                    if link_item.get("url"):
                        homepage_url = link_item.get("url")
                        break
                subjects = [
                    s.get("term") for s in b.get("subject", []) if s.get("term")
                ]
                items.append(
                    {
                        "title": title,
                        "publisher": publisher,
                        "eissn": eissn,
                        "pissn": pissn,
                        "subjects": subjects,
                        "url": homepage_url,
                        "source": "DOAJ",
                    }
                )

        try:
            total_results = int(data.get("total", len(items)))
        except (TypeError, ValueError):
            total_results = len(items)
        try:
            actual_page = int(data.get("page", page))
            actual_page_size = int(data.get("pageSize", max_results))
        except (TypeError, ValueError):
            actual_page = page
            actual_page_size = max_results
        total_pages = (
            (total_results + actual_page_size - 1) // actual_page_size
            if actual_page_size
            else None
        )
        has_more = (
            bool(data.get("next"))
            if "next" in data
            else total_pages is not None and actual_page < total_pages
        )
        return {
            "status": "success",
            "data": items,
            "metadata": {
                "query": query,
                "type": search_type,
                "total_results": total_results,
                "total_results_is_exact": True,
                "returned": len(items),
                "page": actual_page,
                "page_size": actual_page_size,
                "total_pages": total_pages,
                "has_more": has_more,
                "next_page": actual_page + 1 if has_more else None,
                "last_page": total_pages,
            },
        }
