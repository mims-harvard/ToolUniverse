"""
KEGG_get_brite_hierarchy

Get the full hierarchical classification tree for a specific KEGG BRITE hierarchy in JSON format....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_brite_hierarchy(
    hierarchy_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full hierarchical classification tree for a specific KEGG BRITE hierarchy in JSON format....

    Parameters
    ----------
    hierarchy_id : str
        KEGG BRITE hierarchy ID. Examples: 'ko01000' (Enzymes), 'ko01001' (Protein ki...
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
            "name": "KEGG_get_brite_hierarchy",
            "arguments": {"hierarchy_id": hierarchy_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_brite_hierarchy"]
