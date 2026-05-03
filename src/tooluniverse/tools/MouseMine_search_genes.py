"""
MouseMine_search_genes

Search MouseMine specifically for mouse protein-coding genes. This is a convenience wrapper that ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MouseMine_search_genes(
    q: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MouseMine specifically for mouse protein-coding genes. This is a convenience wrapper that ...

    Parameters
    ----------
    q : str
        Gene search query: gene symbol (e.g., 'Brca1', 'Tp53'), gene name, or keyword.
    size : int
        Number of results to return (default: 10).
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
    _args = {k: v for k, v in {"q": q, "size": size}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MouseMine_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MouseMine_search_genes"]
