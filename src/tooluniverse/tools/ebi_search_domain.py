"""
ebi_search_domain

Search across a specific EBI domain (e.g., ensembl, uniprot, interpro) using the unified EBI Sear...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ebi_search_domain(
    domain: str,
    query: str,
    size: Optional[int] = 10,
    start: Optional[int] = 0,
    fields: Optional[str] = None,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search across a specific EBI domain (e.g., ensembl, uniprot, interpro) using the unified EBI Sear...

    Parameters
    ----------
    domain : str
        EBI domain to search (e.g., 'ensembl', 'uniprot', 'interpro', 'chembl', 'arra...
    query : str
        Search query string. Supports field-specific queries like 'name:BRCA1' or 'de...
    size : int
        Number of results to return per page (default: 10, max: 100)
    start : int
        Starting position for pagination (default: 0)
    fields : str
        Comma-separated list of fields to return (e.g., 'id,name,description'). If no...
    format : str
        Response format: 'json' or 'xml'
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
            "domain": domain,
            "query": query,
            "size": size,
            "start": start,
            "fields": fields,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ebi_search_domain",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ebi_search_domain"]
