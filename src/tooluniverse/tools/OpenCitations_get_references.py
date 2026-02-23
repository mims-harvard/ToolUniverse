"""
OpenCitations_get_references

Get the list of papers cited by a given scientific article (its reference list) using OpenCitatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenCitations_get_references(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the list of papers cited by a given scientific article (its reference list) using OpenCitatio...

    Parameters
    ----------
    doi : str
        DOI of the paper to get references for. Do not include 'https://doi.org/' pre...
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
        {"name": "OpenCitations_get_references", "arguments": {"doi": doi}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenCitations_get_references"]
