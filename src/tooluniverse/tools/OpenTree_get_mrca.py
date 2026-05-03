"""
OpenTree_get_mrca

Find the Most Recent Common Ancestor (MRCA) of a set of taxa in the Open Tree of Life synthetic p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTree_get_mrca(
    ott_ids: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find the Most Recent Common Ancestor (MRCA) of a set of taxa in the Open Tree of Life synthetic p...

    Parameters
    ----------
    ott_ids : str
        Comma-separated OTT IDs (at least 2). Use OpenTree_match_names to get IDs. Ex...
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
    _args = {k: v for k, v in {"ott_ids": ott_ids}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTree_get_mrca",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTree_get_mrca"]
