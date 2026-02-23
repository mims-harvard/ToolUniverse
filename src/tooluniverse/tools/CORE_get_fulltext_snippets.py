"""
CORE_get_fulltext_snippets

Fetch an open-access PDF (commonly returned by CORE_search_papers) and return bounded text snippe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CORE_get_fulltext_snippets(
    terms: list[str],
    pdf_url: Optional[str] = None,
    url: Optional[str] = None,
    window_chars: Optional[int] = 220,
    max_snippets_per_term: Optional[int] = 3,
    max_total_chars: Optional[int] = 8000,
    extractor: Optional[str] = "auto",
    timeout: Optional[int] = 20,
    max_pdf_bytes: Optional[int] = 20000000,
    max_pages: Optional[int] = 12,
    max_text_chars: Optional[int] = 400000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Fetch an open-access PDF (commonly returned by CORE_search_papers) and return bounded text snippe...

    Parameters
    ----------
    pdf_url : str
        Direct PDF URL to download (preferred). CORE_search_papers returns this as th...
    url : str
        Alias for `pdf_url` for convenience when piping CORE_search_papers outputs.
    terms : list[str]
        Terms to search for in the extracted PDF text (case-insensitive).
    window_chars : int
        Context window size (characters) before and after each match.
    max_snippets_per_term : int
        Maximum number of snippets returned per term.
    max_total_chars : int
        Hard cap on total characters returned across all snippets.
    extractor : str
        PDF text extraction backend: auto (default), fitz (PyMuPDF), pypdf, or markit...
    timeout : int
        Download timeout in seconds (bounded to <=55 to stay under typical MCP call d...
    max_pdf_bytes : int
        Maximum PDF size (bytes) allowed for download/scan. Prevents timeouts on huge...
    max_pages : int
        Maximum number of PDF pages to scan when using fitz/pypdf extractors.
    max_text_chars : int
        Maximum number of extracted text characters to scan for term matches (limits ...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "CORE_get_fulltext_snippets",
            "arguments": {
                "pdf_url": pdf_url,
                "url": url,
                "terms": terms,
                "window_chars": window_chars,
                "max_snippets_per_term": max_snippets_per_term,
                "max_total_chars": max_total_chars,
                "extractor": extractor,
                "timeout": timeout,
                "max_pdf_bytes": max_pdf_bytes,
                "max_pages": max_pages,
                "max_text_chars": max_text_chars,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CORE_get_fulltext_snippets"]
