#!/usr/bin/env python3
"""
CORE API Tool for searching open access academic papers.

CORE is the world's largest collection of open access research papers.
This tool provides access to over 200 million open access papers from
repositories and journals worldwide.
"""

import requests
import os
import re
import tempfile
import io
from urllib.parse import urljoin
from typing import Dict, List, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry

try:
    from markitdown import MarkItDown

    MARKITDOWN_AVAILABLE = True
except Exception:
    MARKITDOWN_AVAILABLE = False
    MarkItDown = None

try:
    import fitz  # PyMuPDF

    FITZ_AVAILABLE = True
except Exception:
    FITZ_AVAILABLE = False
    fitz = None

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except Exception:
    PYPDF_AVAILABLE = False
    PdfReader = None


def _parse_int_param(
    arguments: Dict[str, Any], key: str, default: int, lo: int, hi: int
) -> int:
    """Parse an integer parameter from arguments, clamping to [lo, hi]."""
    try:
        value = int(arguments.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(value, hi))


@register_tool("CoreTool")
class CoreTool(BaseTool):
    """Tool for searching CORE open access academic papers."""

    def __init__(self, tool_config=None):
        super().__init__(tool_config)
        self.base_url = "https://api.core.ac.uk/v3"
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}
        )

    def _search(
        self,
        query: str,
        limit: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using CORE API.

        Args:
            query: Search query
            limit: Maximum number of results
            year_from: Start year filter
            year_to: End year filter
            language: Language filter (e.g., 'en', 'es', 'fr')

        Returns
            List of paper dictionaries
        """
        try:
            # Build search parameters
            params = {
                "q": query,
                "limit": min(limit, 100),  # CORE API max limit is 100
                "page": 1,
            }

            # Apply filters client-side: CORE query syntax for year/language is not
            # consistently supported and can lead to server 5xx in practice.

            # Make API request
            response = request_with_retry(
                self.session,
                "GET",
                f"{self.base_url}/search/works",
                params=params,
                timeout=30,
                max_attempts=3,
            )
            if response.status_code != 200:
                return [
                    {
                        "error": f"CORE API request failed: {response.status_code} for url: {getattr(response, 'url', None) or ''}".strip()
                    }
                ]

            data = response.json()
            results = []

            # Parse results
            for item in data.get("results", []):
                year = self._extract_year(item.get("publishedDate"))
                lang_code = (item.get("language") or {}).get("code") or "Unknown"

                if year_from is not None and isinstance(year, str) and year.isdigit():
                    if int(year) < int(year_from):
                        continue
                if year_to is not None and isinstance(year, str) and year.isdigit():
                    if int(year) > int(year_to):
                        continue
                if language and isinstance(lang_code, str):
                    if lang_code.lower() != str(language).lower():
                        continue

                paper = {
                    "title": item.get("title", "No title"),
                    "abstract": item.get("abstract", "No abstract available"),
                    "authors": self._extract_authors(item.get("authors", [])),
                    "year": year,
                    "doi": item.get("doi"),
                    "url": (
                        item.get("downloadUrl") or item.get("links", [{}])[0].get("url")
                    ),
                    "venue": item.get("publisher"),
                    "language": lang_code,
                    "open_access": True,  # CORE only contains open access papers
                    "source": "CORE",
                    "citations": item.get("citationCount", 0),
                    "downloads": item.get("downloadCount", 0),
                }
                results.append(paper)

            return results

        except requests.exceptions.RequestException as e:
            return [{"error": f"CORE API request failed: {str(e)}"}]
        except Exception as e:
            return [{"error": f"CORE API error: {str(e)}"}]

    def _extract_authors(self, authors: List[Dict]) -> List[str]:
        """Extract author names from CORE API response."""
        if not authors:
            return []
        return [author["name"] for author in authors if author.get("name")]

    def _extract_year(self, published_date: str) -> str:
        """Extract year from published date."""
        if not published_date:
            return "Unknown"

        try:
            # CORE API returns dates in ISO format
            return published_date[:4]
        except Exception:
            return "Unknown"

    def run(self, tool_arguments) -> List[Dict[str, Any]]:
        """
        Execute the CORE search.

        Args:
            tool_arguments: Dictionary containing search parameters

        Returns
            List of paper dictionaries
        """
        query = (
            tool_arguments.get("query")
            or tool_arguments.get("search")
            or tool_arguments.get("q")
            or ""
        )
        if not query:
            return [{"error": "Query parameter is required"}]

        limit = tool_arguments.get(
            "limit",
            tool_arguments.get("page_size", tool_arguments.get("max_results", 10)),
        )
        year_from = tool_arguments.get("year_from")
        year_to = tool_arguments.get("year_to")
        language = tool_arguments.get("language")

        return self._search(
            query=query,
            limit=limit,
            year_from=year_from,
            year_to=year_to,
            language=language,
        )


@register_tool("CorePDFSnippetsTool")
class CorePDFSnippetsTool(BaseTool):
    """
    Fetch an open-access PDF (commonly returned by CORE) and return bounded text
    snippets around user-provided terms.

    Extraction backends (fastest first when extractor="auto"):
    - PyMuPDF (fitz)
    - pypdf
    - markitdown
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/pdf, */*;q=0.8",
                "User-Agent": "ToolUniverse/1.0 (CORE pdf client; contact: support@tooluniverse.ai)",
            }
        )
        self.md_converter = MarkItDown() if MARKITDOWN_AVAILABLE else None

    def run(self, arguments) -> Dict[str, Any]:
        pdf_url = arguments.get("pdf_url") or arguments.get("url")
        terms = arguments.get("terms")
        extractor = str(arguments.get("extractor") or "auto").strip().lower()

        if not isinstance(terms, list) or not [
            t for t in terms if isinstance(t, str) and t.strip()
        ]:
            return {
                "status": "error",
                "error": "`terms` must be a non-empty list of strings.",
                "retryable": False,
            }

        if not isinstance(pdf_url, str) or not pdf_url.strip():
            return {
                "status": "error",
                "error": "Provide `pdf_url` (preferred) or `url` (alias) pointing to a PDF.",
                "retryable": False,
            }
        pdf_url = pdf_url.strip()

        if extractor not in {"auto", "fitz", "pypdf", "markitdown"}:
            return {
                "status": "error",
                "error": "`extractor` must be one of: auto, fitz, pypdf, markitdown.",
                "retryable": False,
            }

        # Fail fast on missing extractors to avoid unnecessary PDF downloads.
        if extractor == "markitdown" and not MARKITDOWN_AVAILABLE:
            return {
                "status": "error",
                "error": "markitdown library not available. Install with: pip install 'markitdown[all]'",
                "retryable": False,
            }
        if extractor == "fitz" and not FITZ_AVAILABLE:
            return {
                "status": "error",
                "error": "PyMuPDF (fitz) not available. Install with: pip install pymupdf",
                "retryable": False,
            }
        if extractor == "pypdf" and not PYPDF_AVAILABLE:
            return {
                "status": "error",
                "error": "pypdf not available. Install with: pip install pypdf",
                "retryable": False,
            }
        if extractor == "auto" and not (
            FITZ_AVAILABLE or PYPDF_AVAILABLE or MARKITDOWN_AVAILABLE
        ):
            return {
                "status": "error",
                "error": "No PDF text extractor available (need pymupdf, pypdf, or markitdown).",
                "retryable": False,
            }

        window_chars = _parse_int_param(arguments, "window_chars", 220, 20, 2000)
        max_snippets_per_term = _parse_int_param(
            arguments, "max_snippets_per_term", 3, 1, 10
        )
        max_total_chars = _parse_int_param(
            arguments, "max_total_chars", 8000, 1000, 50000
        )
        download_timeout = _parse_int_param(arguments, "timeout", 20, 5, 55)
        max_pdf_bytes = _parse_int_param(
            arguments, "max_pdf_bytes", 20_000_000, 1_000_000, 100_000_000
        )
        max_pages = _parse_int_param(arguments, "max_pages", 12, 1, 200)
        max_text_chars = _parse_int_param(
            arguments, "max_text_chars", 400_000, 50_000, 2_000_000
        )

        retrieval_trace: list[dict[str, Any]] = []

        final_url = pdf_url
        extractor_used: Optional[str] = None
        pages_scanned: Optional[int] = None

        def _looks_like_pdf(content_type: Optional[str], body: Optional[bytes]) -> bool:
            ct = (content_type or "").lower()
            if "application/pdf" in ct or ct.startswith("application/x-pdf"):
                return True
            if isinstance(body, (bytes, bytearray)) and body[:4] == b"%PDF":
                return True
            return False

        def _extract_pdf_url_from_html(base: str, html: str) -> Optional[str]:
            if not isinstance(html, str) or ".pdf" not in html.lower():
                return None
            # Prefer explicit href/src ending with .pdf
            m = re.search(r'(?is)(?:href|src)=["\']([^"\']+\.pdf[^"\']*)["\']', html)
            if not m:
                return None
            return urljoin(base, m.group(1))

        try:
            # Some CORE PDF URLs redirect to filesXX.core.ac.uk and can be unstable.
            # If a CORE numeric id is present, try a few variants.
            candidates = [pdf_url]
            m = re.search(r"/download/(?:pdf/)?(\\d+)\\.pdf", pdf_url)
            if m:
                pid = m.group(1)
                candidates.extend(
                    [
                        f"https://core.ac.uk/download/{pid}.pdf",
                        f"https://core.ac.uk/download/pdf/{pid}.pdf",
                    ]
                )

            resp = None
            pdf_bytes: Optional[bytes] = None

            seen: set[str] = set()
            i = 0
            while i < len(candidates):
                u = candidates[i]
                i += 1
                if u in seen:
                    continue
                seen.add(u)
                # HEAD to check size quickly when possible.
                try:
                    head = request_with_retry(
                        self.session,
                        "HEAD",
                        u,
                        timeout=min(10, download_timeout),
                        max_attempts=2,
                    )
                    retrieval_trace.append(
                        {
                            "attempt": "head_pdf",
                            "url": getattr(head, "url", None) or u,
                            "status_code": getattr(head, "status_code", None),
                            "content_type": (getattr(head, "headers", {}) or {}).get(
                                "content-type"
                            ),
                            "content_length": (getattr(head, "headers", {}) or {}).get(
                                "content-length"
                            ),
                            "note": None,
                        }
                    )
                    if head.status_code in (200, 206):
                        cl = (head.headers or {}).get("content-length")
                        if cl and str(cl).isdigit() and int(cl) > max_pdf_bytes:
                            return {
                                "status": "error",
                                "error": "PDF too large to download within tool limits.",
                                "pdf_url": pdf_url,
                                "candidate_url": u,
                                "content_length": int(cl),
                                "max_pdf_bytes": max_pdf_bytes,
                                "retryable": False,
                                "retrieval_trace": retrieval_trace,
                            }
                except Exception:
                    pass

                resp = request_with_retry(
                    self.session, "GET", u, timeout=download_timeout, max_attempts=2
                )
                final_url = getattr(resp, "url", None) or u
                content_type = (getattr(resp, "headers", {}) or {}).get("content-type")
                retrieval_trace.append(
                    {
                        "attempt": "download_pdf",
                        "url": final_url,
                        "status_code": getattr(resp, "status_code", None),
                        "content_type": content_type,
                        "note": None,
                    }
                )
                if resp.status_code == 200:
                    # Some "PDF" URLs (e.g., PMC /pdf/ endpoints) return an HTML page
                    # that contains the real .pdf link. Detect and follow once.
                    if not _looks_like_pdf(content_type, resp.content):
                        try:
                            html_text = (
                                resp.text
                                if hasattr(resp, "text")
                                else resp.content.decode("utf-8", "ignore")
                            )
                        except Exception:
                            html_text = ""
                        next_pdf = _extract_pdf_url_from_html(final_url, html_text)
                        if next_pdf:
                            candidates.append(next_pdf)
                            retrieval_trace.append(
                                {
                                    "attempt": "html_to_pdf_link",
                                    "url": next_pdf,
                                    "status_code": None,
                                    "content_type": "application/pdf",
                                    "note": "Followed PDF link extracted from HTML response.",
                                }
                            )
                            continue

                    pdf_bytes = resp.content
                    if pdf_bytes is not None and len(pdf_bytes) > max_pdf_bytes:
                        return {
                            "status": "error",
                            "error": "Downloaded PDF exceeds tool size cap.",
                            "pdf_url": pdf_url,
                            "candidate_url": u,
                            "downloaded_bytes": len(pdf_bytes),
                            "max_pdf_bytes": max_pdf_bytes,
                            "retryable": False,
                            "retrieval_trace": retrieval_trace,
                        }
                    break

            if resp is None or resp.status_code != 200 or pdf_bytes is None:
                sc = getattr(resp, "status_code", None)
                return {
                    "status": "error",
                    "error": f"PDF download failed (HTTP {sc})",
                    "pdf_url": pdf_url,
                    "status_code": sc,
                    "retryable": sc in (408, 429, 500, 502, 503, 504),
                    "retrieval_trace": retrieval_trace,
                }

            text = ""
            if extractor in {"auto", "fitz"} and FITZ_AVAILABLE:
                extractor_used = "fitz"
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                try:
                    parts = []
                    n = min(len(doc), max_pages)
                    for i in range(n):
                        parts.append(doc.load_page(i).get_text("text"))
                    pages_scanned = n
                    text = "\n".join(parts)
                finally:
                    try:
                        doc.close()
                    except Exception:
                        pass
            elif extractor in {"auto", "pypdf"} and PYPDF_AVAILABLE:
                extractor_used = "pypdf"
                reader = PdfReader(io.BytesIO(pdf_bytes))
                parts = []
                n = min(len(reader.pages), max_pages)
                for i in range(n):
                    try:
                        parts.append(reader.pages[i].extract_text() or "")
                    except Exception:
                        parts.append("")
                pages_scanned = n
                text = "\n".join(parts)
            else:
                # Specific extractor unavailability is caught by the fail-fast
                # checks at the top of run(). This else branch is only reachable
                # when extractor="auto" and both fitz and pypdf are unavailable,
                # so we fall through to markitdown as a last resort.
                if not MARKITDOWN_AVAILABLE:
                    return {
                        "status": "error",
                        "error": "No PDF text extractor available (need pymupdf, pypdf, or markitdown).",
                        "retryable": False,
                        "retrieval_trace": retrieval_trace,
                    }
                extractor_used = "markitdown"
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                try:
                    result = self.md_converter.convert(tmp_path)
                    text = (
                        result.text_content
                        if hasattr(result, "text_content")
                        else str(result)
                    )
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
        except Exception as e:
            retrieval_trace.append(
                {
                    "attempt": "download_pdf_exception",
                    "url": final_url,
                    "status_code": None,
                    "content_type": None,
                    "note": str(e),
                }
            )
            return {
                "status": "error",
                "error": f"PDF download/processing failed: {str(e)}",
                "pdf_url": pdf_url,
                "retryable": True,
                "retrieval_trace": retrieval_trace,
            }

        snippets: list[dict[str, str]] = []
        total_chars = 0
        text_scanned = (text or "")[:max_text_chars]
        low = text_scanned.lower()

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
                end = min(len(text_scanned), m.end() + window_chars)
                snippet = text_scanned[start:end].strip()
                if total_chars + len(snippet) > max_total_chars:
                    break
                snippets.append({"term": term, "snippet": snippet})
                total_chars += len(snippet)
                found += 1

        return {
            "status": "success",
            "pdf_url": final_url,
            "retrieval_trace": retrieval_trace,
            "snippets": snippets,
            "snippets_count": len(snippets),
            "truncated": total_chars >= max_total_chars,
            "extractor_used": extractor_used,
            "pages_scanned": pages_scanned,
            "text_chars_scanned": len(text_scanned),
        }
