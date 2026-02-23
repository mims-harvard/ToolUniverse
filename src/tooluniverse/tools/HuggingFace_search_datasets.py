"""
HuggingFace_search_datasets

Search HuggingFace Hub for machine learning datasets by keyword. HuggingFace hosts 100,000+ open ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuggingFace_search_datasets(
    search: str,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HuggingFace Hub for machine learning datasets by keyword. HuggingFace hosts 100,000+ open ...

    Parameters
    ----------
    search : str
        Search query for dataset name or topic (e.g., 'protein sequence', 'medical im...
    limit : int | Any
        Maximum number of results to return (default 20, max 1000)
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
            "name": "HuggingFace_search_datasets",
            "arguments": {"search": search, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuggingFace_search_datasets"]
