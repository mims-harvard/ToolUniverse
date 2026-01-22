"""
pubmed_list_resolver_presets_mcp

List available institutional link resolver presets.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_list_resolver_presets_mcp(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available institutional link resolver presets.

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
        {"name": "pubmed_list_resolver_presets_mcp", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_list_resolver_presets_mcp"]
