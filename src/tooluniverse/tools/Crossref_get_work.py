"""
Crossref_get_work

Get complete metadata for a specific scholarly work by its DOI (Digital Object Identifier). Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_get_work(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Get complete metadata for a specific scholarly work by its DOI (Digital Object Identifier). Retur...

    Parameters
    ----------
    doi : str
        Digital Object Identifier in format '10.####/...' (e.g., '10.1038/nature12373...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"doi": doi}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_get_work",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_get_work"]
