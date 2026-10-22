"""
GO_get_annotations_for_gene

Finds GO annotation rows for a gene/protein using GOlr search. Supports exact row-count metadata ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GO_get_annotations_for_gene(
    gene_id: str,
    taxon: Optional[str] = None,
    rows: Optional[int] = 100,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Finds GO annotation rows for a gene/protein using GOlr search. Supports exact row-count metadata ...

    Parameters
    ----------
    gene_id : str
        A gene identifier such as gene symbol (e.g., 'TP53') or database ID.
    taxon : str
        Optional NCBI taxon filter, e.g. 'NCBITaxon:9606' for human. Omit to search a...
    rows : int
        Maximum number of annotations to return. Default: 100. Use a lower value (e.g...
    start : int
        Zero-based annotation-row offset. Use metadata.next_start to retrieve the nex...
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
    _args = {
        k: v
        for k, v in {
            "gene_id": gene_id,
            "taxon": taxon,
            "rows": rows,
            "start": start,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GO_get_annotations_for_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GO_get_annotations_for_gene"]
