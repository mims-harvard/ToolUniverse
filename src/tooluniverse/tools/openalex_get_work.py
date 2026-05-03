"""
openalex_get_work

Get a single OpenAlex work (paper) by OpenAlex Work ID (W...). You can pass either the short ID (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def openalex_get_work(
    openalex_id: str,
    mailto: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Get a single OpenAlex work (paper) by OpenAlex Work ID (W...). You can pass either the short ID (...

    Parameters
    ----------
    openalex_id : str
        OpenAlex Work ID (W...) or full OpenAlex URL.
    mailto : str
        Optional contact email for OpenAlex polite pool.
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
    _args = {
        k: v
        for k, v in {"openalex_id": openalex_id, "mailto": mailto}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "openalex_get_work",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["openalex_get_work"]
