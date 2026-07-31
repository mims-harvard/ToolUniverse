"""
Alliance_get_molecular_interactions

Get molecular (physical) interactions for a gene via the Alliance of Genome Resources (mouse/MGI,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Alliance_get_molecular_interactions(
    gene_id: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get molecular (physical) interactions for a gene via the Alliance of Genome Resources (mouse/MGI,...

    Parameters
    ----------
    gene_id : str
        Alliance gene ID with member prefix, e.g. 'MGI:97490' (Pax6), 'HGNC:8620'.
    limit : int
        Max results (default 20, max 100).
    page : int
        Page number (default 1).
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
        for k, v in {"gene_id": gene_id, "limit": limit, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Alliance_get_molecular_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Alliance_get_molecular_interactions"]
