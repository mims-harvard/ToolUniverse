"""
OpenML_search_datasets

Search the OpenML platform for machine learning benchmark datasets. OpenML hosts thousands of cur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenML_search_datasets(
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the OpenML platform for machine learning benchmark datasets. OpenML hosts thousands of cur...

    Parameters
    ----------
    limit : int
        Maximum number of datasets to return (default 20, max 10000). Controls pagina...
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
        {"name": "OpenML_search_datasets", "arguments": {"limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenML_search_datasets"]
