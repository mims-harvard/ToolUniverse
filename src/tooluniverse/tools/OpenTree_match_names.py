"""
OpenTree_match_names

Resolve species names to standardized Open Tree of Life taxonomy IDs (OTT IDs) using the TNRS (Ta...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTree_match_names(
    names: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve species names to standardized Open Tree of Life taxonomy IDs (OTT IDs) using the TNRS (Ta...

    Parameters
    ----------
    names : str
        Comma-separated list of species or taxon names to resolve. Examples: 'Homo sa...
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
    _args = {k: v for k, v in {"names": names}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTree_match_names",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTree_match_names"]
