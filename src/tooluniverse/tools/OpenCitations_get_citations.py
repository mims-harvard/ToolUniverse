"""
OpenCitations_get_citations

Get the list of papers that cite a given scientific article (its citation count and citing papers...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenCitations_get_citations(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the list of papers that cite a given scientific article (its citation count and citing papers...

    Parameters
    ----------
    doi : str
        DOI of the paper to find citations for. Do not include 'https://doi.org/' pre...
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
        {"name": "OpenCitations_get_citations", "arguments": {"doi": doi}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenCitations_get_citations"]
