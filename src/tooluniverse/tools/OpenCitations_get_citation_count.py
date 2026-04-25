"""
OpenCitations_get_citation_count

Get the total citation count for a scientific article using OpenCitations COCI index. Returns the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenCitations_get_citation_count(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the total citation count for a scientific article using OpenCitations COCI index. Returns the...

    Parameters
    ----------
    doi : str
        DOI of the paper to count citations for. Do not include 'https://doi.org/' pr...
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
    _args = {k: v for k, v in {
        "doi": doi
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenCitations_get_citation_count",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenCitations_get_citation_count"]
