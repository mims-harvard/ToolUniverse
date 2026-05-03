"""
MyGene_query_genes

Search for genes by keyword, symbol, name, or other identifiers. Returns gene annotations from 30...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyGene_query_genes(
    query: str,
    species: Optional[str] = "human",
    fields: Optional[str] = "symbol,name,entrezgene,ensembl.gene,summary",
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for genes by keyword, symbol, name, or other identifiers. Returns gene annotations from 30...

    Parameters
    ----------
    query : str
        Search query. Can be gene symbol (e.g., 'CDK2'), name ('cyclin dependent kina...
    species : str
        Species filter. Use common name or NCBI taxonomy ID. Examples: 'human', 'mous...
    fields : str
        Comma-separated list of fields to return. Common fields: symbol, name, entrez...
    size : int
        Maximum number of results to return (1-100).
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
            "query": query,
            "species": species,
            "fields": fields,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyGene_query_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyGene_query_genes"]
