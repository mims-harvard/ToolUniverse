"""
HumanMine_search_pathways

Search HumanMine specifically for biological pathways by name or identifier. Integrates pathway d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HumanMine_search_pathways(
    q: str,
    size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search HumanMine specifically for biological pathways by name or identifier. Integrates pathway d...

    Parameters
    ----------
    q : str
        Pathway search query: pathway name (e.g., 'apoptosis', 'cell cycle', 'PI3K-Ak...
    size : int | Any
        Maximum number of results to return (default 10, max 100)
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
    _args = {k: v for k, v in {
        "q": q,
                "size": size
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HumanMine_search_pathways",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["HumanMine_search_pathways"]
