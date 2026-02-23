"""
MouseMine_search_alleles

Search MouseMine specifically for mouse alleles and mutants. Returns allele symbols, names, MGI i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MouseMine_search_alleles(
    q: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search MouseMine specifically for mouse alleles and mutants. Returns allele symbols, names, MGI i...

    Parameters
    ----------
    q : str
        Allele search query: gene symbol (e.g., 'Brca1'), allele symbol (e.g., 'Brca1...
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

    return get_shared_client().run_one_function(
        {"name": "MouseMine_search_alleles", "arguments": {"q": q, "size": size}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MouseMine_search_alleles"]
