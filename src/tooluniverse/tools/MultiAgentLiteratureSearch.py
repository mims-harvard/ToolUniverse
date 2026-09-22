"""
MultiAgentLiteratureSearch

Multi-agent literature search system that uses AI agents to analyze intent, extract keywords, exe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MultiAgentLiteratureSearch(
    query: str,
    max_iterations: Optional[int] = 3,
    quality_threshold: Optional[float] = 0.7,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Multi-agent literature search system that uses AI agents to analyze intent, extract keywords, exe...

    Parameters
    ----------
    query : str
        The research query to search for
    max_iterations : int
        Not currently applied -- the search always runs a single pass. Retained for f...
    quality_threshold : float
        Not currently applied -- QualityCheckerAgent is registered as a dependency bu...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "max_iterations": max_iterations,
            "quality_threshold": quality_threshold,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MultiAgentLiteratureSearch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MultiAgentLiteratureSearch"]
