"""
pubmed_analyze_figure_mcp

[Experimental] Analyze a scientific figure and extract search keywords for literature search.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def pubmed_analyze_figure_mcp(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    [Experimental] Analyze a scientific figure and extract search keywords for literature search.

    Parameters
    ----------
    image_url : str
        URL of the image to analyze
    image_base64 : str
        Base64-encoded image data
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
            "name": "pubmed_analyze_figure_mcp",
            "arguments": {"image_url": image_url, "image_base64": image_base64},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["pubmed_analyze_figure_mcp"]
