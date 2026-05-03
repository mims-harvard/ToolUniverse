"""
odphp_outlink_fetch

This tool retrieves readable text from ODPHP article links and information sources. This is helpf...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def odphp_outlink_fetch(
    urls: list[str],
    max_chars: int,
    return_html: bool,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    This tool retrieves readable text from ODPHP article links and information sources. This is helpf...

    Parameters
    ----------
    urls : list[str]
        1–3 absolute URLs from AccessibleVersion or RelatedItems.Url
    max_chars : int
        Optional hard cap on extracted text length (e.g., 5000)
    return_html : bool
        If true, also return minimally cleaned HTML
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
            "urls": urls,
            "max_chars": max_chars,
            "return_html": return_html,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "odphp_outlink_fetch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["odphp_outlink_fetch"]
