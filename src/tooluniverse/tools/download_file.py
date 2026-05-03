"""
download_file

Download files from HTTP/HTTPS URLs with cross-platform support (Windows, Mac, Linux). Similar to...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def download_file(
    url: str,
    output_path: Optional[str] = None,
    timeout: Optional[int] = 30,
    return_content: Optional[bool] = False,
    chunk_size: Optional[int] = 8192,
    follow_redirects: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download files from HTTP/HTTPS URLs with cross-platform support (Windows, Mac, Linux). Similar to...

    Parameters
    ----------
    url : str
        HTTP or HTTPS URL to download from (e.g., https://example.com/file.txt)
    output_path : str
        Optional path to save the file. If not specified, file will be saved to syste...
    timeout : int
        Request timeout in seconds
    return_content : bool
        If true, return file content as text instead of saving to disk (default: false)
    chunk_size : int
        Download chunk size in bytes (default: 8192)
    follow_redirects : bool
        Follow HTTP redirects (default: true)
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
            "timeout": timeout,
            "return_content": return_content,
            "chunk_size": chunk_size,
            "follow_redirects": follow_redirects,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "download_file",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["download_file"]
