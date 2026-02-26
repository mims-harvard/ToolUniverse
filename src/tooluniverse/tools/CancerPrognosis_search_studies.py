"""
CancerPrognosis_search_studies

Search cBioPortal for cancer genomics studies by keyword. Find studies by cancer type, institutio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CancerPrognosis_search_studies(
    operation: str,
    keyword: str,
    limit: Optional[int | Any] = None,
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
            "name": "CancerPrognosis_search_studies",
            "arguments": {"operation": operation, "keyword": keyword, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CancerPrognosis_search_studies"]
