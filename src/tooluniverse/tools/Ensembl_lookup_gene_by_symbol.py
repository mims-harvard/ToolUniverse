"""
Ensembl_lookup_gene_by_symbol

Look up Ensembl IDs for a gene symbol and species. The complete Ensembl response is exposed throu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_lookup_gene_by_symbol(
    symbol: str,
    species: Optional[str] = "human",
    external_db: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up Ensembl IDs for a gene symbol and species. The complete Ensembl response is exposed throu...

    Parameters
    ----------
    symbol : str
        Gene symbol to look up. Examples: 'TP53', 'BRCA1', 'EGFR', 'BRAF', 'KRAS'.
    species : str
        Species name. Default: 'human'. Examples: 'human', 'mouse', 'rat', 'zebrafish'.
    external_db : str
        Optional: filter by external database. Examples: 'HGNC', 'EntrezGene'.
    limit : int
        Maximum Ensembl IDs returned (default 50).
    offset : int
        Zero-based result offset. Continue with metadata.next_offset.
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
            "symbol": symbol,
            "species": species,
            "external_db": external_db,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Ensembl_lookup_gene_by_symbol",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_lookup_gene_by_symbol"]
