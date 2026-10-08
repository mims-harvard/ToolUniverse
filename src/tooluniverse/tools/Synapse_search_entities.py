"""
Synapse_search_entities

Search public Synapse.org (Sage Bionetworks) content by keyword: projects, folders, files, tables...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Synapse_search_entities(
    query: str,
    node_type: Optional[str] = None,
    size: Optional[int] = 10,
    start: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search public Synapse.org (Sage Bionetworks) content by keyword: projects, folders, files, tables...

    Parameters
    ----------
    query : str
        Search words, e.g. 'alzheimer proteomics' (all words are matched)
    node_type : str
        Restrict to one entity type: project, folder, file, table, dataset
    size : int
        Hits per page (1-100, default 10)
    start : int
        Offset of the first hit, for paging (default 0)
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
            "query": query,
            "node_type": node_type,
            "size": size,
            "start": start,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Synapse_search_entities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Synapse_search_entities"]
