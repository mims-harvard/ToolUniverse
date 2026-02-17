"""
GEO_get_dataset_details

Get detailed metadata for a specific GEO dataset by its accession (GSE ID). Returns comprehensive...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GEO_get_dataset_details(
    geo_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific GEO dataset by its accession (GSE ID). Returns comprehensive...

    Parameters
    ----------
    geo_id : str
        GEO dataset accession (numeric part only, e.g., '200291249' for GSE291249). G...
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
        {"name": "GEO_get_dataset_details", "arguments": {"geo_id": geo_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GEO_get_dataset_details"]
