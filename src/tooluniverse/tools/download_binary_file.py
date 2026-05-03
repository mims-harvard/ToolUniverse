"""
download_binary_file

Download binary files (images, videos, executables) with chunked streaming for better memory mana...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def download_binary_file(
    url: str,
    output_path: str,
    chunk_size: Optional[int] = 1048576,
    timeout: Optional[int] = 30,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download binary files (images, videos, executables) with chunked streaming for better memory mana...

    Parameters
    ----------
    url : str
        HTTP or HTTPS URL to download from
    output_path : str
        Full path where to save the binary file (e.g., /tmp/image.jpg or C:\\Users\\D...
    chunk_size : int
        Download chunk size in bytes (default: 1MB for binary files)
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
        for k, v in {
            "url": url,
            "output_path": output_path,
            "chunk_size": chunk_size,
            "timeout": timeout,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "download_binary_file",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["download_binary_file"]
