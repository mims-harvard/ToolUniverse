"""
Ensembl_lookup_gene_by_symbol

Look up Ensembl gene IDs for a gene symbol across external databases. Given a gene symbol (e.g., ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_lookup_gene_by_symbol(
    symbol: str,
    species: Optional[str] = None,
    external_db: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up Ensembl gene IDs for a gene symbol across external databases. Given a gene symbol (e.g., ...

    Parameters
    ----------
    symbol : str
        Gene symbol to look up. Examples: 'TP53', 'BRCA1', 'EGFR', 'BRAF', 'KRAS'.
    species : str
        Species name. Default: 'human'. Examples: 'human', 'mouse', 'rat', 'zebrafish'.
    external_db : str | Any
        Optional: filter by external database. Examples: 'HGNC', 'EntrezGene'.
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
            "name": "Ensembl_lookup_gene_by_symbol",
            "arguments": {
                "symbol": symbol,
                "species": species,
                "external_db": external_db,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_lookup_gene_by_symbol"]
