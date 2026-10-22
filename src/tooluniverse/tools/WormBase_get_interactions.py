"""
WormBase_get_interactions

Get physical and genetic interactions for a C. elegans gene. Both lists are independently recover...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WormBase_get_interactions(
    gene_id: str,
    limit: Optional[int] = 150,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get physical and genetic interactions for a C. elegans gene. Both lists are independently recover...

    Parameters
    ----------
    gene_id : str
        WBGene identifier or gene name. Examples: 'WBGene00006818', 'unc-86'.
    limit : int
        Maximum interactions to return per category (default 150).
    offset : int
        Zero-based offset applied independently to physical and genetic lists.
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
        for k, v in {"gene_id": gene_id, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WormBase_get_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WormBase_get_interactions"]
