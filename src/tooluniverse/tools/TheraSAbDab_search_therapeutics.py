"""
TheraSAbDab_search_therapeutics

Search therapeutic antibodies by name or target keyword in Thera-SAbDab. Returns WHO INN name, ta...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TheraSAbDab_search_therapeutics(
    query: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search therapeutic antibodies by name or target keyword in Thera-SAbDab. Returns WHO INN name, ta...

    Parameters
    ----------
    query : str
        Search query - antibody name (e.g., 'trastuzumab', 'pembrolizumab', 'rituximab')
    limit : int
        Maximum matching therapeutics to return
    offset : int
        Zero-based match offset; continue with next_offset
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"query": query, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TheraSAbDab_search_therapeutics",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TheraSAbDab_search_therapeutics"]
