"""
advanced_literature_search_agent

Advanced multi-agent deep literature search system. This is a SEARCH-FIRST system: agents must ex...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def advanced_literature_search_agent(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Advanced multi-agent deep literature search system. This is a SEARCH-FIRST system: agents must ex...

    Parameters
    ----------
    query : str
        Research query or topic to search in academic literature. The agent will auto...
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "advanced_literature_search_agent",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["advanced_literature_search_agent"]
