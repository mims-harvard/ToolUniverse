"""
TCIA_list_collections

List all publicly available imaging collections in The Cancer Imaging Archive (TCIA). TCIA is a l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_list_collections(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all publicly available imaging collections in The Cancer Imaging Archive (TCIA). TCIA is a l...

    Parameters
    ----------
    No parameters
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

    return get_shared_client().run_one_function(
        {"name": "TCIA_list_collections", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_list_collections"]
