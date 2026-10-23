"""
LitVar_search_variants

Retrieve LitVar2 autocomplete top-N variant candidates by rsID, gene, or HGVS text. This is not a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LitVar_search_variants(
    query: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve LitVar2 autocomplete top-N variant candidates by rsID, gene, or HGVS text. This is not a...

    Parameters
    ----------
    query : str
        Search query: rsID (e.g., 'rs328', 'rs7903146'), gene name (e.g., 'BRCA1', 'T...
    limit : int
        Maximum autocomplete candidates (default 10, max 100). The endpoint does not ...
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LitVar_search_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LitVar_search_variants"]
