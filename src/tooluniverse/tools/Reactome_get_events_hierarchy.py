"""
Reactome_get_events_hierarchy

Get the full event hierarchy (pathways and reactions) for a specific species. Returns complete ne...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_get_events_hierarchy(
    species: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get the full event hierarchy (pathways and reactions) for a specific species. Returns complete ne...

    Parameters
    ----------
    species : str
        Species taxonomy ID (e.g., '9606' for Homo sapiens) or species name. Taxonomy...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"species": species}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Reactome_get_events_hierarchy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Reactome_get_events_hierarchy"]
