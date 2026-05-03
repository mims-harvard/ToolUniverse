"""
ENAPortal_search_samples

Search the European Nucleotide Archive (ENA) for biological samples by taxonomy or text query. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENAPortal_search_samples(
    query: str,
    limit: Optional[int | Any] = None,
    fields: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the European Nucleotide Archive (ENA) for biological samples by taxonomy or text query. Re...

    Parameters
    ----------
    query : str
        ENA search query. Examples: 'tax_tree(562)' (E. coli), 'description="liver"',...
    limit : int | Any
        Maximum results to return (1-100, default 10).
    fields : str | Any
        Comma-separated fields. Default: 'sample_accession,sample_alias,description,t...
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
        for k, v in {"query": query, "limit": limit, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENAPortal_search_samples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENAPortal_search_samples"]
