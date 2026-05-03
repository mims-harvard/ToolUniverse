"""
civic_search_variants

Search for variants in CIViC database. Returns a list of variants with their IDs and names. Use '...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_search_variants(
    limit: Optional[int] = 20,
    query: Optional[str] = None,
    gene: Optional[str] = None,
    gene_name: Optional[str] = None,
    variant_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for variants in CIViC database. Returns a list of variants with their IDs and names. Use '...

    Parameters
    ----------
    limit : int
        Maximum number of variants to return (default: 20, recommended max: 100)
    query : str
        Variant name to search for (e.g., "T790M", "V600E", "exon 19 deletion"). Retu...
    gene : str
        Gene symbol to filter variants by (e.g., 'EGFR', 'BRAF', 'KRAS'). Returns all...
    gene_name : str
        Alias for gene. Gene symbol (e.g., 'TP53', 'BRCA1').
    variant_name : str
        Specific variant name to filter within a gene (e.g., 'L858R', 'V600E', 'T790M...
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
            "limit": limit,
            "query": query,
            "gene": gene,
            "gene_name": gene_name,
            "variant_name": variant_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "civic_search_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_search_variants"]
