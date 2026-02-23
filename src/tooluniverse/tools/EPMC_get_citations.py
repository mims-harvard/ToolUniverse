"""
EPMC_get_citations

Get articles that cite a specific paper from Europe PMC. Given a PubMed ID (PMID), returns a list...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPMC_get_citations(
    pmid: str,
    page: Optional[int] = 1,
    pageSize: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get articles that cite a specific paper from Europe PMC. Given a PubMed ID (PMID), returns a list...

    Parameters
    ----------
    pmid : str
        PubMed ID of the article to find citations for. Examples: '25378148' (AlphaFo...
    page : int
        Page number for paginated results (1-based). Default: 1.
    pageSize : int
        Number of citing articles to return per page (1-1000). Default: 25.
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

    return get_shared_client().run_one_function(
        {
            "name": "EPMC_get_citations",
            "arguments": {"pmid": pmid, "page": page, "pageSize": pageSize},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EPMC_get_citations"]
