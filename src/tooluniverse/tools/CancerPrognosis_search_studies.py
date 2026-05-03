"""
CancerPrognosis_search_studies

Search cBioPortal for cancer genomics studies by keyword. Find studies by cancer type, institutio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CancerPrognosis_search_studies(
    operation: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: Optional[int | Any] = None,
    cancer_type: Optional[str] = None,
    cancer: Optional[str] = None,
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search cBioPortal for cancer genomics studies by keyword. Find studies by cancer type, institutio...

    Parameters
    ----------
    operation : str
        Operation type
    keyword : str
        Search keyword (e.g., 'breast', 'lung', 'TCGA', 'melanoma', 'glioblastoma')
    limit : int | Any
        Maximum number of results to return (default 20, max 100)
    cancer_type : str
        Cancer type to search for. Alias for keyword.
    cancer : str
        Cancer type to search for. Alias for keyword.
    query : str
        Search query. Alias for keyword (e.g., 'lung', 'breast', 'TCGA').
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
            "operation": operation,
            "keyword": keyword,
            "limit": limit,
            "cancer_type": cancer_type,
            "cancer": cancer,
            "query": query,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CancerPrognosis_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CancerPrognosis_search_studies"]
