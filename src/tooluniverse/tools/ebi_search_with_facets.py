"""
ebi_search_with_facets

Search EBI domain with faceted filtering and returns facet information. Use facetcount to request...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ebi_search_with_facets(
    domain: str,
    query: str,
    facets: Optional[str] = None,
    facetcount: Optional[int] = 10,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search EBI domain with faceted filtering and returns facet information. Use facetcount to request...

    Parameters
    ----------
    domain : str
        EBI domain to search (e.g., 'ensembl', 'uniprot', 'interpro')
    query : str
        Search query string
    facets : str
        Optional filter for results using facet values in format 'FACET_NAME:value' (...
    facetcount : int
        Number of facet values to return per facet category (default: 10). Set to 0 t...
    size : int
        Number of results to return (default: 10)
    format : str

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
            "domain": domain,
            "query": query,
            "facets": facets,
            "facetcount": facetcount,
            "size": size,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ebi_search_with_facets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ebi_search_with_facets"]
