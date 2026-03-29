import os
import re
import tempfile
import threading
import time

import requests
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

try:
    from markitdown import MarkItDown

    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False


@register_tool("SemanticScholarTool")
class SemanticScholarTool(BaseTool):
    """
    Tool to search for papers on Semantic Scholar including abstracts.

    API key is read from environment variable SEMANTIC_SCHOLAR_API_KEY.
    Request an API key at: https://www.semanticscholar.org/product/api

    Rate limits:
    - Without API key: 1 request/second
    - With API key: 100 requests/second
    """

    _last_request_time = 0.0
    _rate_limit_lock = threading.Lock()

    def __init__(
        self,
        tool_config,
        base_url="https://api.semanticscholar.org/graph/v1/paper/search",
    ):
        super().__init__(tool_config)
        self.base_url = base_url
        # Get API key from environment as fallback
        self.default_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def run(self, arguments):
        query = arguments.get("query")
        limit = arguments.get("limit", 5)
        year = arguments.get("year")
        sort = arguments.get("sort")
        include_abstract = bool(arguments.get("include_abstract", False))
        if not query:
            return {"status": "error", "error": "`query` parameter is required."}
        if limit <= 0:
            return {"status": "success", "data": [], "metadata": {"total": 0}}
        papers = self._search(
            query, limit, year=year, sort=sort, include_abstract=include_abstract
        )
        # Check if _search returned an error list
        if papers and isinstance(papers[0], dict) and "error" in papers[0]:
            err = papers[0]
            return {
                "status": "error",
                "error": err.get("error", "Unknown error"),
                "retryable": err.get("retryable", False),
            }
        return {
            "status": "success",
            "data": papers,
            "metadata": {"total": len(papers), "query": query},
        }

    def _enforce_rate_limit(self, has_api_key: bool) -> None:
        # Keep anonymous usage below 1 req/sec to reduce 429s.
        min_interval = 0.02 if has_api_key else 1.05
        with self._rate_limit_lock:
            now = time.time()
            elapsed = now - SemanticScholarTool._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            SemanticScholarTool._last_request_time = time.time()

    def _fetch_missing_abstract(self, paper_id: str) -> dict | None:
        paper_id = (paper_id or "").strip()
        if not paper_id:
            return None

        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
        params = {"fields": "abstract,externalIds,openAccessPdf"}
        headers = {"x-api-key": self.default_api_key} if self.default_api_key else {}
        self._enforce_rate_limit(bool(self.default_api_key))
        resp = request_with_retry(
            self.session,
            "GET",
            url,
            params=params,
            headers=headers,
            timeout=20,
            max_attempts=3,
        )
        if resp.status_code != 200:
            return None
        try:
            payload = resp.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    def _search(
        self, query, limit, *, year=None, sort=None, include_abstract: bool = False
    ):
        params = {
            "query": query,
            "limit": limit,
            # Include identifiers and lightweight impact signals for better downstream utility.
            "fields": ",".join(
                [
                    "paperId",
                    "externalIds",
                    "title",
                    "abstract",
                    "tldr",
                    "year",
                    "venue",
                    "url",
                    "authors",
                    "citationCount",
                    "referenceCount",
                    "isOpenAccess",
                    "openAccessPdf",
                    "fieldsOfStudy",
                ]
            ),
        }
        if year:
            params["year"] = str(year)
        if sort:
            params["sort"] = sort
        headers = {"x-api-key": self.default_api_key} if self.default_api_key else {}
        self._enforce_rate_limit(bool(self.default_api_key))
        # Use /paper/search/bulk when sorting, as /paper/search silently
        # ignores the sort parameter and always returns relevance-ranked results.
        url = self.base_url
        if sort:
            url = url.replace("/paper/search", "/paper/search/bulk")
        response = request_with_retry(
            self.session,
            "GET",
            url,
            params=params,
            headers=headers,
            timeout=20,
            max_attempts=3,
        )
        if response.status_code != 200:
            retryable = response.status_code in (408, 429, 500, 502, 503, 504)
            return [
                {
                    "title": "Error",
                    "error": f"Semantic Scholar API error {response.status_code}",
                    "reason": response.reason,
                    "retryable": retryable,
                    "suggestion": "Try again later or set SEMANTIC_SCHOLAR_API_KEY for higher limits. Alternatives: ArXiv_search_papers, EuropePMC_search_articles, openalex_literature_search, PubMed_search_articles.",
                }
            ]
        try:
            payload = response.json()
        except ValueError:
            return [
                {
                    "title": "Error",
                    "error": "Semantic Scholar returned invalid JSON",
                    "retryable": True,
                }
            ]

        results = payload.get("data", []) if isinstance(payload, dict) else []
        papers = []
        for p in results:
            # Extract basic information
            external_ids = (
                p.get("externalIds") if isinstance(p.get("externalIds"), dict) else {}
            )
            doi = (
                external_ids.get("DOI")
                if isinstance(external_ids.get("DOI"), str)
                else None
            )
            doi_url = f"https://doi.org/{doi}" if doi else None
            title = p.get("title")
            abstract = p.get("abstract") or None
            journal = p.get("venue") or None
            year = p.get("year")
            url = p.get("url")
            paper_id = p.get("paperId") if isinstance(p.get("paperId"), str) else None

            # Extract TLDR summary
            raw_tldr = p.get("tldr")
            tldr = None
            if isinstance(raw_tldr, dict) and isinstance(raw_tldr.get("text"), str):
                tldr = raw_tldr["text"]

            # Extract fields of study
            raw_fields = p.get("fieldsOfStudy")
            fields_of_study = raw_fields if isinstance(raw_fields, list) else None

            authors = []
            raw_authors = p.get("authors", [])
            if isinstance(raw_authors, list):
                for a in raw_authors:
                    if (
                        isinstance(a, dict)
                        and isinstance(a.get("name"), str)
                        and a["name"].strip()
                    ):
                        authors.append(a["name"].strip())

            citation_count = p.get("citationCount")
            reference_count = p.get("referenceCount")
            is_open_access = p.get("isOpenAccess")
            open_access_pdf = (
                p.get("openAccessPdf")
                if isinstance(p.get("openAccessPdf"), dict)
                else None
            )
            open_access_pdf_url = (
                open_access_pdf.get("url")
                if open_access_pdf
                and isinstance(open_access_pdf.get("url"), str)
                and open_access_pdf.get("url", "").strip()
                else None
            )

            if include_abstract and not abstract and paper_id:
                details = self._fetch_missing_abstract(paper_id)
                if details:
                    details_external = (
                        details.get("externalIds")
                        if isinstance(details.get("externalIds"), dict)
                        else {}
                    )
                    details_doi = (
                        details_external.get("DOI")
                        if isinstance(details_external.get("DOI"), str)
                        else None
                    )
                    if not doi and details_doi:
                        doi = details_doi
                        doi_url = f"https://doi.org/{doi}"

                    details_abstract = details.get("abstract")
                    if isinstance(details_abstract, str) and details_abstract.strip():
                        abstract = details_abstract.strip()

                    details_open_access_pdf = (
                        details.get("openAccessPdf")
                        if isinstance(details.get("openAccessPdf"), dict)
                        else None
                    )
                    if (
                        not open_access_pdf_url
                        and details_open_access_pdf
                        and isinstance(details_open_access_pdf.get("url"), str)
                    ):
                        open_access_pdf_url = details_open_access_pdf.get("url")

            papers.append(
                {
                    "title": title or "Title not available",
                    "abstract": abstract,
                    "tldr": tldr,
                    "journal": journal,
                    "year": year,
                    "url": url,
                    "paper_id": paper_id,
                    "doi": doi,
                    "doi_url": doi_url,
                    "authors": authors,
                    "fields_of_study": fields_of_study,
                    "citation_count": citation_count,
                    "reference_count": reference_count,
                    "open_access": is_open_access
                    if isinstance(is_open_access, bool)
                    else None,
                    "open_access_pdf_url": open_access_pdf_url,
                    "data_quality": {
                        "has_abstract": bool(abstract),
                        "has_tldr": bool(tldr),
                        "has_journal": bool(journal),
                        "has_year": bool(year),
                        "has_url": bool(url),
                        "has_doi": bool(doi),
                        "has_authors": bool(authors),
                    },
                }
            )
        return papers


@register_tool("SemanticScholarPDFSnippetsTool")
class SemanticScholarPDFSnippetsTool(BaseTool):
    """
    Fetch a paper's PDF from Semantic Scholar and return bounded text snippets
    around user-provided terms. Uses markitdown to convert PDF to markdown text.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/pdf, */*;q=0.8"})
        if MARKITDOWN_AVAILABLE:
            self.md_converter = MarkItDown()
        else:
            self.md_converter = None

    def run(self, arguments):
        paper_id = arguments.get("paper_id")
        open_access_pdf_url = arguments.get("open_access_pdf_url")
        terms = arguments.get("terms")

        # Validate terms
        if not isinstance(terms, list) or not [
            t for t in terms if isinstance(t, str) and t.strip()
        ]:
            return {
                "status": "error",
                "error": "`terms` must be a non-empty list of strings.",
                "retryable": False,
            }

        # Get PDF URL
        pdf_url = None
        lookup_error = None
        if isinstance(open_access_pdf_url, str) and open_access_pdf_url.strip():
            pdf_url = open_access_pdf_url.strip()
        elif isinstance(paper_id, str) and paper_id.strip():
            # Fetch paper details to get PDF URL
            paper_id = paper_id.strip()
            api_url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
            params = {"fields": "openAccessPdf"}
            try:
                resp = request_with_retry(
                    self.session,
                    "GET",
                    api_url,
                    params=params,
                    timeout=20,
                    max_attempts=2,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and isinstance(
                        data.get("openAccessPdf"), dict
                    ):
                        pdf_url = data["openAccessPdf"].get("url")
            except Exception as e:
                lookup_error = str(e)

        if not pdf_url:
            msg = "Could not determine PDF URL. Provide `open_access_pdf_url` or a valid `paper_id` with available open access PDF."
            if lookup_error:
                msg += f" (API lookup failed: {lookup_error})"
            return {
                "status": "error",
                "error": msg,
                "retryable": "429" in (lookup_error or "")
                or "timeout" in (lookup_error or "").lower(),
            }

        # Check if markitdown is available
        if not MARKITDOWN_AVAILABLE:
            return {
                "status": "error",
                "error": "markitdown library not available. Install with: pip install 'markitdown[all]'",
                "retryable": False,
            }

        # Parse optional parameters
        try:
            window_chars = int(arguments.get("window_chars", 220))
        except (TypeError, ValueError):
            window_chars = 220
        window_chars = max(20, min(window_chars, 2000))

        try:
            max_snippets_per_term = int(arguments.get("max_snippets_per_term", 3))
        except (TypeError, ValueError):
            max_snippets_per_term = 3
        max_snippets_per_term = max(1, min(max_snippets_per_term, 10))

        try:
            max_total_chars = int(arguments.get("max_total_chars", 8000))
        except (TypeError, ValueError):
            max_total_chars = 8000
        max_total_chars = max(1000, min(max_total_chars, 50000))

        # Download PDF to temp file
        try:
            resp = request_with_retry(
                self.session, "GET", pdf_url, timeout=60, max_attempts=2
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"PDF download failed (HTTP {resp.status_code})",
                    "url": pdf_url,
                    "status_code": resp.status_code,
                    "retryable": resp.status_code in (408, 429, 500, 502, 503, 504),
                }

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            # Convert PDF to markdown using markitdown
            try:
                result = self.md_converter.convert(tmp_path)
                text = (
                    result.text_content
                    if hasattr(result, "text_content")
                    else str(result)
                )
            except Exception as e:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                return {
                    "status": "error",
                    "error": f"PDF to markdown conversion failed: {str(e)}",
                    "url": pdf_url,
                    "retryable": False,
                }

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        except Exception as e:
            return {
                "status": "error",
                "error": f"PDF download/processing failed: {str(e)}",
                "url": pdf_url,
                "retryable": True,
            }

        # Extract snippets around terms
        snippets = []
        total_chars = 0
        low = text.lower()

        for raw_term in terms:
            if not isinstance(raw_term, str):
                continue
            term = raw_term.strip()
            if not term:
                continue

            needle = term.lower()
            found = 0
            for m in re.finditer(re.escape(needle), low):
                if found >= max_snippets_per_term:
                    break
                start = max(0, m.start() - window_chars)
                end = min(len(text), m.end() + window_chars)
                snippet = text[start:end].strip()
                # Bound total output size
                if total_chars + len(snippet) > max_total_chars:
                    break
                snippets.append({"term": term, "snippet": snippet})
                total_chars += len(snippet)
                found += 1

        return {
            "status": "success",
            "pdf_url": pdf_url,
            "snippets": snippets,
            "snippets_count": len(snippets),
            "truncated": total_chars >= max_total_chars,
        }
