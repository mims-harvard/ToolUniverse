"""
pubmed_configure_institution_mcp

Configure institutional link resolver for full-text access. Supports presets (ntu, harvard, etc.)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_configure_institution_mcp(
    preset: Optional[str] = None,
    resolver_url: Optional[str] = None,
    enable: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Configure institutional link resolver for full-text access. Supports presets (ntu, harvard, etc.)...

    Parameters
    ----------
    preset : str
        Preset name (ntu, ncku, harvard, stanford, etc.)
    resolver_url : str
        Custom resolver URL
    enable : bool

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
        {
            "name": "pubmed_configure_institution_mcp",
            "arguments": {
                "preset": preset,
                "resolver_url": resolver_url,
                "enable": enable,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_configure_institution_mcp"]
