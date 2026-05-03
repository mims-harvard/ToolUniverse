"""
MyGene_batch_query

Query multiple genes at once using a list of gene identifiers. Efficient for retrieving annotatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyGene_batch_query(
    gene_ids: list[str],
    species: Optional[str] = "human",
    fields: Optional[str] = "symbol,name,entrezgene,ensembl.gene",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query multiple genes at once using a list of gene identifiers. Efficient for retrieving annotatio...

    Parameters
    ----------
    gene_ids : list[str]
        List of gene IDs to query. Can mix different ID types (Entrez, Ensembl, symbo...
    species : str
        Species filter for the query.
    fields : str
        Comma-separated list of fields to return for each gene.
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
        for k, v in {"gene_ids": gene_ids, "species": species, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyGene_batch_query",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyGene_batch_query"]
