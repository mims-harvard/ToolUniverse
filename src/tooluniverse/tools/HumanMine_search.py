"""
HumanMine_search

Search HumanMine (InterMine) for genes, proteins, pathways, diseases, and other biological entiti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HumanMine_search(
    q: str,
    size: Optional[int | Any] = None,
    facet_Category: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HumanMine (InterMine) for genes, proteins, pathways, diseases, and other biological entiti...

    Parameters
    ----------
    q : str
        Search query: gene symbol (e.g., 'TP53', 'BRCA1'), gene name, disease name, p...
    size : int | Any
        Maximum number of results to return (default 10, max 100)
    facet_Category : str | Any
        Filter by entity type: 'Gene', 'Protein', 'Pathway', 'Disease', 'Publication'...
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
    _args = {k: v for k, v in {
        "q": q,
                "size": size,
                "facet_Category": facet_Category
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HumanMine_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["HumanMine_search"]
