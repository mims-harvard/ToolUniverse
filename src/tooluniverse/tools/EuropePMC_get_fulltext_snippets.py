"""
EuropePMC_get_fulltext_snippets

Fetch an article's full text (best-effort) and return bounded text snippets around provided terms...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_get_fulltext_snippets(
    fulltext_xml_url: Optional[str] = None,
    pmcid: Optional[str] = None,
    source_db: Optional[str] = None,
    article_id: Optional[str] = None,
    terms: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    window_chars: Optional[int] = 220,
    max_snippets_per_term: Optional[int] = 3,
    max_total_chars: Optional[int] = 8000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Fetch an article's full text (best-effort) and return bounded text snippets around provided terms...

    Parameters
    ----------
    fulltext_xml_url : str
        Direct Europe PMC fullTextXML URL (recommended when you already have it from ...
    pmcid : str
        PMC ID (e.g., 'PMC11237425' or '11237425'). If provided, the tool derives the...
    source_db : str
        Europe PMC source database (e.g., 'MED' or 'PMC'). Used with `article_id` to ...
    article_id : str
        Europe PMC article ID within `source_db` (e.g., PMID for source_db='MED').
    terms : list[str]
        Terms to search for in the extracted full text (case-insensitive).
    keywords : list[str]
        Alias for `terms` (case-insensitive). Provided for backwards/UX compatibility.
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
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_get_fulltext_snippets",
            "arguments": {
                "fulltext_xml_url": fulltext_xml_url,
                "pmcid": pmcid,
                "source_db": source_db,
                "article_id": article_id,
                "terms": terms,
                "keywords": keywords,
                "window_chars": window_chars,
                "max_snippets_per_term": max_snippets_per_term,
                "max_total_chars": max_total_chars,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_get_fulltext_snippets"]
