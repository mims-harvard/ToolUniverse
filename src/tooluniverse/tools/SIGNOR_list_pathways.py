"""
SIGNOR_list_pathways

List curated signaling pathways in the SIGNOR database. Optionally filter by keyword to find path...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIGNOR_list_pathways(
    query: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List curated signaling pathways in the SIGNOR database. Optionally filter by keyword to find path...

    Parameters
    ----------
    query : str
        Optional keyword to filter pathways by name or description (e.g., 'cancer', '...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SIGNOR_list_pathways",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIGNOR_list_pathways"]
