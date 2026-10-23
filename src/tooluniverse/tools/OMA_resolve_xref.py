"""
OMA_resolve_xref

Resolve and page through OMA cross-reference matches for a gene symbol, UniProt entry name, or ot...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_resolve_xref(
    search: str,
    limit: Optional[int] = 25,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve and page through OMA cross-reference matches for a gene symbol, UniProt entry name, or ot...

    Parameters
    ----------
    search : str
        Gene symbol (e.g. 'BRCA2'), UniProt entry name (e.g. 'MED4_HUMAN'), or any cr...
    limit : int
        Maximum cross-reference matches to return (default 25, max 1000).
    offset : int
        Zero-based offset into all OMA cross-reference matches.
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
        for k, v in {"search": search, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OMA_resolve_xref",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_resolve_xref"]
