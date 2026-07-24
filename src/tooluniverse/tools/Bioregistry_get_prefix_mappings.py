"""
Bioregistry_get_prefix_mappings

Get cross-registry prefix mappings for a Bioregistry prefix. Maps a prefix (e.g. 'chebi', 'go', '...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bioregistry_get_prefix_mappings(
    prefix: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get cross-registry prefix mappings for a Bioregistry prefix. Maps a prefix (e.g. 'chebi', 'go', '...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_prefix_mappings)
    prefix : str
        Bioregistry prefix (e.g., 'chebi', 'go', 'mondo', 'uniprot', 'hgnc')
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
    _args = {
        k: v
        for k, v in {"operation": operation, "prefix": prefix}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Bioregistry_get_prefix_mappings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bioregistry_get_prefix_mappings"]
