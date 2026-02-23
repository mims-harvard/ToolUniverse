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
        PostgREST filter for gene symbol, prefix with 'eq.' (e.g., 'eq.CYP2D6', 'eq.D...
    cpiclevel : str | Any
        PostgREST filter for CPIC evidence level, prefix with 'eq.' (e.g., 'eq.A', 'e...
    limit : int | Any
        Maximum number of results to return (default 50)
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
            "name": "CPIC_search_gene_drug_pairs",
            "arguments": {
                "genesymbol": genesymbol,
                "cpiclevel": cpiclevel,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_search_gene_drug_pairs"]
