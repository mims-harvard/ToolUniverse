"""
odphp_topicsearch

Find specific health topics and get their full content. Use when the user mentions a keyword (e.g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def odphp_topicsearch(
    lang: str,
    topicId: str,
    categoryId: str,
    keyword: str,
    strip_html: bool,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find specific health topics and get their full content. Use when the user mentions a keyword (e.g...

    Parameters
    ----------
    lang : str
        Language code (en or es)
    topicId : str
        Comma-separated topic IDs
    categoryId : str
        Comma-separated category IDs
    keyword : str
        Keyword search for topics
    strip_html : bool
        If true, also return PlainSections[] with HTML removed for each topic
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
            "lang": lang,
            "topicId": topicId,
            "categoryId": categoryId,
            "keyword": keyword,
            "strip_html": strip_html,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "odphp_topicsearch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["odphp_topicsearch"]
