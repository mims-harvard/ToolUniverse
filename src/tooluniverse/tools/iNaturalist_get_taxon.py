"""
iNaturalist_get_taxon

Get detailed taxonomy information for a species by its iNaturalist taxon ID. Returns scientific n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iNaturalist_get_taxon(
    taxon_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomy information for a species by its iNaturalist taxon ID. Returns scientific n...

    Parameters
    ----------
    taxon_id : int
        iNaturalist taxon ID. Examples: 41482 (bottlenose dolphin), 43584 (Homo sapie...
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
    _args = {k: v for k, v in {"taxon_id": taxon_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "iNaturalist_get_taxon",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iNaturalist_get_taxon"]
