"""
NCBIDatasets_get_gene_by_symbol

Look up gene information by gene symbol and organism. Searches NCBI Gene database using official ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIDatasets_get_gene_by_symbol(
    symbol: str,
    taxon: Optional[str] = None,
    organism: Optional[str] = None,
    species: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up gene information by gene symbol and organism. Searches NCBI Gene database using official ...

    Parameters
    ----------
    symbol : str
        Gene symbol. Examples: 'TP53', 'BRCA1', 'INS', 'EGFR'.
    taxon : str
        Organism as common name or taxonomy ID. Examples: 'human', 'mouse', 'rat', '9...
    organism : str
        Synonym for `taxon`. Used when `taxon` is not supplied.
    species : str
        Synonym for `taxon`. Used when neither `taxon` nor `organism` is supplied.
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
            "taxon": taxon,
            "organism": organism,
            "species": species,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBIDatasets_get_gene_by_symbol",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIDatasets_get_gene_by_symbol"]
