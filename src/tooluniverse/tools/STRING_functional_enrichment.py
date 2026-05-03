"""
STRING_functional_enrichment

Identify enriched biological functions, pathways, and processes for a protein set using STRING (S...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def STRING_functional_enrichment(
    protein_ids: list[str],
    species: Optional[int] = 9606,
    category: Optional[str] = "Process",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Identify enriched biological functions, pathways, and processes for a protein set using STRING (S...

    Parameters
    ----------
    protein_ids : list[str]
        List of protein identifiers (UniProt IDs, gene names, Ensembl IDs). Minimum 3...
    species : int
        NCBI taxonomy ID (default: 9606 for human)
    category : str
        Enrichment category: 'Process' (GO Biological Process), 'Component' (GO Cellu...
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
            "protein_ids": protein_ids,
            "species": species,
            "category": category,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "STRING_functional_enrichment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["STRING_functional_enrichment"]
