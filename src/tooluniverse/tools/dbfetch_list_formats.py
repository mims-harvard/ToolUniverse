"""
dbfetch_list_formats

List available output formats for a specific database. Note: This returns common format names as ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dbfetch_list_formats(
    db: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    List available output formats for a specific database. Note: This returns common format names as ...

    Parameters
    ----------
    db : str
        Database name
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"db": db}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "dbfetch_list_formats",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dbfetch_list_formats"]
