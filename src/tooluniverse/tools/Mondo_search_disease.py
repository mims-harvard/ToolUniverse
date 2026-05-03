"""
Mondo_search_disease

Search the Mondo Disease Ontology for diseases by name or keyword. Mondo unifies disease identifi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mondo_search_disease(
    query: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Mondo Disease Ontology for diseases by name or keyword. Mondo unifies disease identifi...

    Parameters
    ----------
    query : str
        Disease name or keyword to search. Examples: 'Alzheimer', 'breast cancer', 't...
    limit : int
        Maximum number of results to return (default: 10, max: 50).
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
    _args = {k: v for k, v in {"query": query, "limit": limit}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Mondo_search_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mondo_search_disease"]
