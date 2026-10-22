"""
GOAPI_get_genes_by_function

Get unique genes annotated with a GO term. The upstream /genes route actually returns repeated as...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GOAPI_get_genes_by_function(
    go_id: str,
    rows: Optional[int] = None,
    offset: Optional[int] = 0,
    max_associations_scanned: Optional[int] = None,
    taxon: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get unique genes annotated with a GO term. The upstream /genes route actually returns repeated as...

    Parameters
    ----------
    go_id : str
        Gene Ontology term ID. Examples: 'GO:0006915' (apoptotic process), 'GO:000367...
    rows : int
        Unique genes per locally deduplicated page (default 20, max 1000).
    offset : int
        Zero-based offset after deduplication by gene ID. Continue with metadata.next...
    max_associations_scanned : int
        Optional upstream association-row scan budget. Increase and rerun the same of...
    taxon : str
        Filter by taxon. Format: NCBITaxon:ID. Examples: 'NCBITaxon:9606' (human), 'N...
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
            "go_id": go_id,
            "rows": rows,
            "offset": offset,
            "max_associations_scanned": max_associations_scanned,
            "taxon": taxon,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GOAPI_get_genes_by_function",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GOAPI_get_genes_by_function"]
