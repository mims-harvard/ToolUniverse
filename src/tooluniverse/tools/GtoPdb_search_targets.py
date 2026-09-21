"""
GtoPdb_search_targets

Search the Guide to Pharmacology database (GtoPdb) for drug targets including GPCRs, ion channels...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_search_targets(
    name: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    type_: Optional[str] = None,
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Guide to Pharmacology database (GtoPdb) for drug targets including GPCRs, ion channels...

    Parameters
    ----------
    name : str
        Target NAME substring to search. Examples: 'dopamine', 'serotonin receptor', ...
    gene_symbol : str
        HGNC gene symbol for an exact target lookup. Examples: 'CHRNA7' (nicotinic ac...
    type_ : str
        Target type filter, enforced by ToolUniverse against each returned record (Gt...
    query : str
        Name/keyword to search for. Alias for the "name" parameter.
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
            "name": name,
            "gene_symbol": gene_symbol,
            "type": type_,
            "query": query,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GtoPdb_search_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_search_targets"]
