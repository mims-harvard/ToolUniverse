"""
OpenFDA_search_drug_labels

Search FDA drug labels via openFDA with exact totals and skip pagination. Continue with metadata....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_labels(
    search: str,
    limit: Optional[int] = 1,
    skip: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FDA drug labels via openFDA with exact totals and skip pagination. Continue with metadata....

    Parameters
    ----------
    search : str
        Lucene query to search drug labels (e.g., 'openfda.brand_name:aspirin', 'open...
    limit : int
        Maximum number of results (default 1, max 100)
    skip : int
        Number of matching records to skip. Continue with metadata.next_skip.
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
        for k, v in {"search": search, "limit": limit, "skip": skip}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_search_drug_labels",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDA_search_drug_labels"]
