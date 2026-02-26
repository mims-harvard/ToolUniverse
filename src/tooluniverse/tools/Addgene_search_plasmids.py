"""
Addgene_search_plasmids

Search Addgene's plasmid catalog by name, gene, species, or vector type. Addgene is a nonprofit g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Addgene_search_plasmids(
    operation: str,
    query: str,
    organism: Optional[str | Any] = None,
    vector_type: Optional[str | Any] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Addgene's plasmid catalog by name, gene, species, or vector type. Addgene is a nonprofit g...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Plasmid name or keyword to search (e.g., 'pSpCas9', 'GFP', 'lentiviral'). Sea...
    organism : str | Any
        Filter by organism/species (e.g., 'Human', 'Mouse', 'E. coli'). Maps to the s...
    vector_type : str | Any
        Filter by vector type (e.g., 'AAV', 'Lentiviral', 'Retroviral', 'Mammalian Ex...
    limit : int
        Maximum number of results to return (default 10, max 100)
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
            "name": "Addgene_search_plasmids",
            "arguments": {
                "operation": operation,
                "query": query,
                "organism": organism,
                "vector_type": vector_type,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Addgene_search_plasmids"]
