"""
iCite_get_publications

Get citation metrics and research context for PubMed publications using NIH's iCite API. iCite pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iCite_get_publications(
    pmids: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get citation metrics and research context for PubMed publications using NIH's iCite API. iCite pr...

    Parameters
    ----------
    pmids : str
        Comma-separated PubMed IDs to look up (e.g., '24453150,24453148,31510562'). M...
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
    _args = {k: v for k, v in {"pmids": pmids}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "iCite_get_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iCite_get_publications"]
