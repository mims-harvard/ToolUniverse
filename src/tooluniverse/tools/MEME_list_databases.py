"""
MEME_list_databases

List available motif databases on the MEME Suite server for use with FIMO motif scanning and TOMT...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MEME_list_databases(
    operation: str,
    category_filter: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List available motif databases on the MEME Suite server for use with FIMO motif scanning and TOMT...

    Parameters
    ----------
    operation : str
        Operation type
    category_filter : str | Any
        Filter categories by name or description substring. E.g., 'JASPAR', 'human', ...
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
    _args = {k: v for k, v in {
        "operation": operation,
                "category_filter": category_filter
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MEME_list_databases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["MEME_list_databases"]
