"""
BioPortal_search_ontology_terms

Search across 900+ biomedical ontologies in BioPortal (NCBO) for concepts matching a query. BioPo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioPortal_search_ontology_terms(
    query: str,
    ontologies: Optional[str | Any] = None,
    page_size: Optional[int | Any] = None,
    exact_match: Optional[bool | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search across 900+ biomedical ontologies in BioPortal (NCBO) for concepts matching a query. BioPo...

    Parameters
    ----------
    query : str
        Search query for finding ontology terms. Can be disease names, gene functions...
    ontologies : str | Any
        Comma-separated list of ontology acronyms to search within. If null, searches...
    page_size : int | Any
        Number of results to return (default: 10, max: 50).
    exact_match : bool | Any
        If true, only return exact matches (default: false).
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
            "query": query,
            "ontologies": ontologies,
            "page_size": page_size,
            "exact_match": exact_match,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioPortal_search_ontology_terms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioPortal_search_ontology_terms"]
