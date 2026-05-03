"""
DrugCentral_search

Search for drugs in DrugCentral by name, returning DrugCentral-curated data including drug names ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugCentral_search(
    query: str,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for drugs in DrugCentral by name, returning DrugCentral-curated data including drug names ...

    Parameters
    ----------
    query : str
        Drug name or identifier to search for. Examples: 'metformin', 'aspirin', 'ima...
    size : int
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
    _args = {k: v for k, v in {"query": query, "size": size}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DrugCentral_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugCentral_search"]
