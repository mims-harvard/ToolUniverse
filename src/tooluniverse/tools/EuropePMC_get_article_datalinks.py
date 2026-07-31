"""
EuropePMC_get_article_datalinks

Retrieve the Europe PMC 'datalinks' for an article: the text-mined and curated cross-references f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuropePMC_get_article_datalinks(
    pmid: str,
    source: Optional[str] = "MED",
    page: Optional[int] = 1,
    pageSize: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the Europe PMC 'datalinks' for an article: the text-mined and curated cross-references f...

    Parameters
    ----------
    pmid : str
        Article identifier whose data cross-references to retrieve. By default interp...
    source : str
        Europe PMC source database for the id. 'MED' (PubMed/MEDLINE, default), 'PMC'...
    page : int
        Page number for paginated results (1-based). Default: 1.
    pageSize : int
        Number of data-link records to return per page (1-1000). Default: 25.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "pmid": pmid,
            "source": source,
            "page": page,
            "pageSize": pageSize,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuropePMC_get_article_datalinks",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuropePMC_get_article_datalinks"]
