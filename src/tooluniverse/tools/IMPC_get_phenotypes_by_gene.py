"""
IMPC_get_phenotypes_by_gene

Get all phenotype annotations for a mouse gene from IMPC knockout screens. Returns MP ontology te...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMPC_get_phenotypes_by_gene(
    gene_symbol: Optional[str] = None,
    mgi_id: Optional[str] = None,
    limit: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all phenotype annotations for a mouse gene from IMPC knockout screens. Returns MP ontology te...

    Parameters
    ----------
    gene_symbol : str
        Mouse gene symbol (e.g., 'Trp53', 'Brca1')
    mgi_id : str
        MGI accession ID (e.g., 'MGI:98834')
    limit : int
        Maximum phenotype records to return (default: 100)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_symbol": gene_symbol,
            "mgi_id": mgi_id,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMPC_get_phenotypes_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMPC_get_phenotypes_by_gene"]
