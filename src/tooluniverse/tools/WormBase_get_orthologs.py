"""
WormBase_get_orthologs

Get cross-species orthologs, nematode orthologs, and within-worm paralogs. All three lists are in...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WormBase_get_orthologs(
    gene_id: str,
    ortholog_limit: Optional[int] = 50,
    paralog_limit: Optional[int] = 30,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get cross-species orthologs, nematode orthologs, and within-worm paralogs. All three lists are in...

    Parameters
    ----------
    gene_id : str
        WBGene identifier or gene name. Examples: 'WBGene00006818', 'unc-86'.
    ortholog_limit : int
        Maximum rows per cross-species and nematode ortholog list (default 50).
    paralog_limit : int
        Maximum paralogs per page (default 30).
    offset : int
        Zero-based offset applied independently to all three lists.
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
        for k, v in {
            "gene_id": gene_id,
            "ortholog_limit": ortholog_limit,
            "paralog_limit": paralog_limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WormBase_get_orthologs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WormBase_get_orthologs"]
