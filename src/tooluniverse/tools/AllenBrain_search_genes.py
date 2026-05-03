"""
AllenBrain_search_genes

Search for genes in the Allen Brain Atlas by gene symbol (acronym) or name. Returns gene metadata...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AllenBrain_search_genes(
    gene_acronym: Optional[str | Any] = None,
    gene_name: Optional[str | Any] = None,
    num_rows: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for genes in the Allen Brain Atlas by gene symbol (acronym) or name. Returns gene metadata...

    Parameters
    ----------
    gene_acronym : str | Any
        Gene symbol/acronym for exact match. Examples: 'Gad1', 'Pvalb', 'Sst', 'Bdnf'...
    gene_name : str | Any
        Gene name for partial match search (alternative to gene_acronym). Example: 'g...
    num_rows : int
        Max results to return. Default: 50.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_acronym": gene_acronym,
            "gene_name": gene_name,
            "num_rows": num_rows,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AllenBrain_search_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AllenBrain_search_genes"]
