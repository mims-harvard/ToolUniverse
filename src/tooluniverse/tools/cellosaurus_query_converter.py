"""
cellosaurus_query_converter

Convert natural language queries to Solr syntax for Cellosaurus API searches. Uses semantic simil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cellosaurus_query_converter(
    query: str,
    include_explanation: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Convert natural language queries to Solr syntax for Cellosaurus API searches. Uses semantic simil...

    Parameters
    ----------
    query : str
        Natural language query to convert to Solr syntax (e.g., 'human cancer cells',...
    include_explanation : bool
        Whether to include detailed explanation of the conversion process
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
        for k, v in {"query": query, "include_explanation": include_explanation}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cellosaurus_query_converter",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cellosaurus_query_converter"]
