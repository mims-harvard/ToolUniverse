"""
UniProt_search

Search UniProtKB database with flexible query syntax. Returns protein entries with accession numb...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_search(
    query: str,
    organism: Optional[str] = None,
    limit: Optional[int] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    fields: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search UniProtKB database with flexible query syntax. Returns protein entries with accession numb...

    Parameters
    ----------
    query : str
        Search query using UniProt syntax. Simple: 'MEIOB', 'insulin'. Field searches...
    organism : str
        Optional organism filter. Use common names ('human', 'mouse', 'rat', 'yeast')...
    limit : int
        Maximum number of results to return (default: 25, max: 500). Accepts string o...
    min_length : int
        Minimum sequence length. Auto-converts to 'length:[min TO *]' range query.
    max_length : int
        Maximum sequence length. Auto-converts to 'length:[* TO max]' range query.
    fields : list[str]
        List of field names to return (e.g., ['accession','gene_primary','length','or...
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
            "organism": organism,
            "limit": limit,
            "min_length": min_length,
            "max_length": max_length,
            "fields": fields,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_search"]
