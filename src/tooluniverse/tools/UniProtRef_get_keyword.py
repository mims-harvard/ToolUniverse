"""
UniProtRef_get_keyword

Get detailed information about a specific UniProt keyword by its ID. Returns the full definition,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtRef_get_keyword(
    keyword_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific UniProt keyword by its ID. Returns the full definition,...

    Parameters
    ----------
    keyword_id : str
        UniProt keyword ID in format KW-XXXX. Get IDs from UniProtRef_search_keywords...
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
    _args = {k: v for k, v in {"keyword_id": keyword_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProtRef_get_keyword",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtRef_get_keyword"]
