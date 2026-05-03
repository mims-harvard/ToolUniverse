"""
Wikipedia_get_content

Extract content from a Wikipedia article. Can extract introduction, summary, or full article cont...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Wikipedia_get_content(
    title: str,
    language: Optional[str] = "en",
    extract_type: Optional[str] = "summary",
    max_chars: Optional[int] = 2000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Extract content from a Wikipedia article. Can extract introduction, summary, or full article cont...

    Parameters
    ----------
    title : str
        Wikipedia article title (exact title as it appears on Wikipedia)
    language : str
        Wikipedia language code (e.g., 'en' for English, 'zh' for Chinese). Default: ...
    extract_type : str
        Type of content to extract: 'intro' (first paragraph only), 'summary' (first ...
    max_chars : int
        Maximum characters to return for intro/summary (ignored for 'full'). Default:...
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
    _args = {
        k: v
        for k, v in {
            "title": title,
            "language": language,
            "extract_type": extract_type,
            "max_chars": max_chars,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Wikipedia_get_content",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Wikipedia_get_content"]
