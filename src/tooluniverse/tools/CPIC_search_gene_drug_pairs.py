"""
CPIC_search_gene_drug_pairs

Search CPIC gene-drug pairs by gene symbol and/or CPIC evidence level. Gene symbol should be the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_search_gene_drug_pairs(
    genesymbol: Optional[str | Any] = None,
    cpiclevel: Optional[str | Any] = None,
    limit: Optional[int | Any] = None,
    gene_symbol: Optional[str | Any] = None,
    gene: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search CPIC gene-drug pairs by gene symbol and/or CPIC evidence level. Gene symbol should be the ...

    Parameters
    ----------
    genesymbol : str | Any
        Gene symbol to filter by (e.g., 'CYP2D6', 'DPYD', 'TPMT'). Omit to search all...
    cpiclevel : str | Any
        CPIC evidence level to filter by (e.g., 'A', 'B', 'B/C', 'C', 'D'). Omit to i...
    limit : int | Any
        Maximum number of results to return (default 50)
    gene_symbol : str | Any
        Gene symbol alias (e.g., 'CYP2D6', 'VKORC1') — alternative to genesymbol
    gene : str | Any
        Gene symbol alias (e.g., 'CYP2D6') — alternative to genesymbol
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
            "genesymbol": genesymbol,
            "cpiclevel": cpiclevel,
            "limit": limit,
            "gene_symbol": gene_symbol,
            "gene": gene,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CPIC_search_gene_drug_pairs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_search_gene_drug_pairs"]
