"""
EpiGraphDB_search_gene

Search for gene information in EpiGraphDB by gene symbol or Ensembl ID. Returns gene metadata inc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_search_gene(
    gene_name: Optional[str | Any] = None,
    gene_id: Optional[str | Any] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for gene information in EpiGraphDB by gene symbol or Ensembl ID. Returns gene metadata inc...

    Parameters
    ----------
    gene_name : str | Any
        Gene symbol to search for (e.g., 'BRCA1', 'TP53', 'EGFR'). Either gene_name o...
    gene_id : str | Any
        Ensembl gene ID (e.g., 'ENSG00000012048'). Either gene_name or gene_id required.
    limit : int
        Maximum results to return (default 10, max 50).
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
    _args = {k: v for k, v in {
        "gene_name": gene_name,
                "gene_id": gene_id,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_search_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["EpiGraphDB_search_gene"]
