"""
DisProt_search

Search DisProt for intrinsically disordered proteins by gene name, protein-name fragment, organis...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisProt_search(
    query: str,
    page_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search DisProt for intrinsically disordered proteins by gene name, protein-name fragment, organis...

    Parameters
    ----------
    query : str
        Gene name (e.g., 'TP53'), protein-name fragment (e.g., 'kinase', 'amyloid'), ...
    page_size : int
        Number of results to return (default 10, max 20).
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
            "name": "DisProt_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisProt_search"]
