"""
SASBDB_get_entries_by_tag

Find SASBDB small-angle scattering entries associated with a specific tag shortcode. See https://...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SASBDB_get_entries_by_tag(
    tag: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Find SASBDB small-angle scattering entries associated with a specific tag shortcode. See https://...

    Parameters
    ----------
    tag : str
        Tag shortcode to search for (e.g. 'idp' for intrinsically disordered proteins...
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

    return get_shared_client().run_one_function(
        {"name": "SASBDB_get_entries_by_tag", "arguments": {"tag": tag}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SASBDB_get_entries_by_tag"]
