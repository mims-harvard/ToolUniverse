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
        max_results = int(arguments.get("max_results", 10))

        if not query:
            return {"error": "`query` parameter is required."}

        if search_type not in ["articles", "journals"]:
            return {"error": "`type` must be 'articles' or 'journals'."}

        endpoint = f"{self.base_url}/{search_type}/{query}"
        params = {
            "pageSize": max(1, min(max_results, 100)),
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {
                "error": "Network/API error calling DOAJ",
                "reason": str(e),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
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

        return items
