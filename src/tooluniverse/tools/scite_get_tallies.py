"""
scite_get_tallies

Get smart citation tallies for a scientific paper using scite.ai. scite analyzes citation context...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def scite_get_tallies(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get smart citation tallies for a scientific paper using scite.ai. scite analyzes citation context...

    Parameters
    ----------
    doi : str
        DOI of the paper to get citation tallies for (e.g., '10.1038/nature12303', '1...
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
    _args = {k: v for k, v in {"doi": doi}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "scite_get_tallies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["scite_get_tallies"]
