"""
Reactome_list_top_pathways

List top-level pathways for a specific species. Returns pathways that have no parent pathways, in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_list_top_pathways(
    species: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List top-level pathways for a specific species. Returns pathways that have no parent pathways, in...

    Parameters
    ----------
    species : str
        Species name or taxonomy ID (e.g., 'Homo sapiens' or '9606'). IMPORTANT: Comm...
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
            "name": "Reactome_list_top_pathways",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Reactome_list_top_pathways"]
