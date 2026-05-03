"""
BioImageArchive_search_bioimages

Search the BioImage Archive specifically for biological image datasets (BioImages collection). Th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioImageArchive_search_bioimages(
    query: str,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the BioImage Archive specifically for biological image datasets (BioImages collection). Th...

    Parameters
    ----------
    query : str
        Search query for biological imaging data. Examples: 'cell division', 'neuron ...
    page_size : int | Any
        Number of results per page. Default: 10. Max: 100.
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
        for k, v in {"query": query, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioImageArchive_search_bioimages",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioImageArchive_search_bioimages"]
