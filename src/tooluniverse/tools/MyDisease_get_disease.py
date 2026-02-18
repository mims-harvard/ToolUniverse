"""
MyDisease_get_disease

Get comprehensive disease annotations from MyDisease.info, a BioThings disease aggregator that in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyDisease_get_disease(
    disease_id: str,
    fields: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive disease annotations from MyDisease.info, a BioThings disease aggregator that in...

    Parameters
    ----------
    disease_id : str
        Disease identifier. Supports MONDO IDs (e.g., 'MONDO:0005148' for T2DM), DOID...
    fields : str
        Comma-separated list of data fields to return. Options: 'mondo', 'disease_ont...
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
        {
            "name": "MyDisease_get_disease",
            "arguments": {"disease_id": disease_id, "fields": fields},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyDisease_get_disease"]
