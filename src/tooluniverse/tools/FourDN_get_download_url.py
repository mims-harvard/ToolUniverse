"""
FourDN_get_download_url

Get download URL and DRS (Data Repository Service) API endpoint for 4DN files. Prerequisites: (1)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FourDN_get_download_url(
    operation: str,
    file_accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get download URL and DRS (Data Repository Service) API endpoint for 4DN files. Prerequisites: (1)...

    Parameters
    ----------
    operation : str

    file_accession : str
        4DN file accession (e.g., '4DNFIIA7E3HL'). Obtain by searching with FourDN_se...
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
        for k, v in {"operation": operation, "file_accession": file_accession}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FourDN_get_download_url",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FourDN_get_download_url"]
