"""
download_text_content

Download and return text content from URLs. Optimized for text files with automatic encoding dete...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def download_text_content(
    url: str,
    encoding: Optional[str] = None,
    timeout: Optional[int] = 30,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download and return text content from URLs. Optimized for text files with automatic encoding dete...

    Parameters
    ----------
    url : str
        HTTP or HTTPS URL to download text from
    encoding : str
        Text encoding (e.g., utf-8, latin1). Auto-detected if not specified.
    timeout : int
        Request timeout in seconds
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
        for k, v in {"url": url, "encoding": encoding, "timeout": timeout}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "download_text_content",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["download_text_content"]
