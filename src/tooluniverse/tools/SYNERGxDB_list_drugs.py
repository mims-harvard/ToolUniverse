"""
SYNERGxDB_list_drugs

List drugs in the SYNERGxDB database with their identifiers. Returns drug names, IDs, PubChem CID...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SYNERGxDB_list_drugs(
    operation: Optional[str] = None,
    query: Optional[str] = None,
    name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List drugs in the SYNERGxDB database with their identifiers. Returns drug names, IDs, PubChem CID...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Filter by drug name (case-insensitive substring match, e.g., 'imatinib', 'tax...
    name : str
        Alias for query. Filter by drug name.
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
        for k, v in {"operation": operation, "query": query, "name": name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SYNERGxDB_list_drugs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SYNERGxDB_list_drugs"]
