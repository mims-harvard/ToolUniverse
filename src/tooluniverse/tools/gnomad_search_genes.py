"""
gnomad_search_genes

Search for genes in gnomAD by free-text query (typically a gene symbol). Returns matching `ensemb...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_search_genes(
    query: str,
    reference_genome: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for genes in gnomAD by free-text query (typically a gene symbol). Returns matching `ensemb...

    Parameters
    ----------
    query : str
        Gene search string (e.g., 'BRCA1').
    reference_genome : str
        Reference genome for the search.
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
        for k, v in {"query": query, "reference_genome": reference_genome}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_search_genes"]
