"""
ArXiv_get_pdf_snippets

Fetch an arXiv paper's PDF and return bounded text snippets around provided terms. Uses markitdow...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ArXiv_get_pdf_snippets(
    terms: list[str],
    arxiv_id: Optional[str] = None,
    pdf_url: Optional[str] = None,
    window_chars: Optional[int] = 220,
    max_snippets_per_term: Optional[int] = 3,
    max_total_chars: Optional[int] = 8000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Fetch an arXiv paper's PDF and return bounded text snippets around provided terms. Uses markitdow...

    Parameters
    ----------
    arxiv_id : str
        arXiv paper ID (e.g., '2301.12345' or 'arXiv:2301.12345'). The tool will buil...
    pdf_url : str
        Direct PDF URL (e.g., 'https://arxiv.org/pdf/2301.12345.pdf').
    terms : list[str]
        Terms to search for in the extracted full text (case-insensitive).
    window_chars : int
        Context window size (characters) before and after each match.
    max_snippets_per_term : int
        Maximum number of snippets returned per term.
    max_total_chars : int
        Hard cap on total characters returned across all snippets.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "arxiv_id": arxiv_id,
            "pdf_url": pdf_url,
            "terms": terms,
            "window_chars": window_chars,
            "max_snippets_per_term": max_snippets_per_term,
            "max_total_chars": max_total_chars,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ArXiv_get_pdf_snippets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ArXiv_get_pdf_snippets"]
