"""
OpenCitations_get_citations

Get papers that cite a scientific article using OpenCitations COCI. OpenCitations returns the ful...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenCitations_get_citations(
    doi: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get papers that cite a scientific article using OpenCitations COCI. OpenCitations returns the ful...

    Parameters
    ----------
    doi : str
        DOI of the paper to find citations for. Do not include 'https://doi.org/' pre...
    limit : int
        Number of citations in this client-side page.
    offset : int
        Zero-based citation offset. Continue with metadata.next_offset while metadata...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"doi": doi, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenCitations_get_citations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenCitations_get_citations"]
