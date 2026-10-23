"""
PanglaoDB_cell_types_for_gene

Reverse cell-type lookup for a gene using PanglaoDB (panglaodb.se). Given an official human gene ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanglaoDB_cell_types_for_gene(
    gene: str,
    species: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse cell-type lookup for a gene using PanglaoDB (panglaodb.se). Given an official human gene ...

    Parameters
    ----------
    gene : str
        Official human gene symbol, e.g. 'CD19', 'ALB', 'EPCAM', 'INS'. Case-insensit...
    species : str
        Optional species filter: 'human' (Hs) or 'mouse' (Mm). If omitted, returns al...
    limit : int
        Page size for cell-type records. Default 50. If metadata.has_more is true, co...
    offset : int
        Zero-based result offset. Default 0. Use metadata.next_offset to retrieve the...
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
            "gene": gene,
            "species": species,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PanglaoDB_cell_types_for_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanglaoDB_cell_types_for_gene"]
