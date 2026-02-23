"""
MouseMine_search

Search MouseMine, the InterMine data warehouse for mouse (Mus musculus) genomics data from MGI (M...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MouseMine_search(
    q: str,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    facet_Category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MouseMine, the InterMine data warehouse for mouse (Mus musculus) genomics data from MGI (M...

    Parameters
    ----------
    q : str
        Search query: gene symbol (e.g., 'Brca1', 'Tp53', 'Sox9'), protein name, dise...
    size : int
        Number of results to return (default: 10, max: 100).
    format : str
        Response format. Must be 'json'.
    facet_Category : str
        Filter results by entity category. Options include: 'ProteinCodingGene', 'Gen...
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
            "name": "MouseMine_search",
            "arguments": {
                "q": q,
                "size": size,
                "format": format,
                "facet_Category": facet_Category,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MouseMine_search"]
