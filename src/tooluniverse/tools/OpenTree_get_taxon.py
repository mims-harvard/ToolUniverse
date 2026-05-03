"""
OpenTree_get_taxon

Get detailed taxonomy information for a taxon from the Open Tree of Life by its OTT ID. Returns t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTree_get_taxon(
    ott_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomy information for a taxon from the Open Tree of Life by its OTT ID. Returns t...

    Parameters
    ----------
    ott_id : int
        Open Tree Taxonomy ID. Examples: 770315 (Homo sapiens), 417950 (Pan troglodyt...
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
    _args = {k: v for k, v in {"ott_id": ott_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTree_get_taxon",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTree_get_taxon"]
