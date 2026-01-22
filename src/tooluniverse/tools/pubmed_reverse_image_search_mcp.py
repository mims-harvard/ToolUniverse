"""
pubmed_reverse_image_search_mcp

[Experimental] Search for papers containing similar figures/images.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_reverse_image_search_mcp(
    image_url: Optional[str] = None,
    keywords: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    [Experimental] Search for papers containing similar figures/images.

    Parameters
    ----------
    image_url : str

    keywords : str
        Keywords extracted from image analysis
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
            "name": "pubmed_reverse_image_search_mcp",
            "arguments": {"image_url": image_url, "keywords": keywords},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_reverse_image_search_mcp"]
