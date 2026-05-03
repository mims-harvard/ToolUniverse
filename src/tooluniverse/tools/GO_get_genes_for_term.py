"""
GO_get_genes_for_term

Finds all genes/proteins associated with a specific Gene Ontology term using the Biolink API.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GO_get_genes_for_term(
    id: str,
    taxon: str,
    rows: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Finds all genes/proteins associated with a specific Gene Ontology term using the Biolink API.

    Parameters
    ----------
    id : str
        The standard GO term ID, e.g., 'GO:0006915'.
    taxon : str
        Optional species filter using a NCBI taxon ID. For example, Human is 'NCBITax...
    rows : int
        The number of genes to return. Default is 100.
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
        for k, v in {"id": id, "taxon": taxon, "rows": rows}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GO_get_genes_for_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GO_get_genes_for_term"]
