"""
ELM_list_classes

List short linear motif (SLiM) classes from the ELM database. Each class represents a distinct ty...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ELM_list_classes(
    operation: str,
    motif_type: Optional[str | Any] = None,
    query: Optional[str | Any] = None,
    max_results: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List short linear motif (SLiM) classes from the ELM database. Each class represents a distinct ty...

    Parameters
    ----------
    operation : str
        Operation type
    motif_type : str | Any
        Filter by motif functional type. CLV=cleavage, DEG=degradation, DOC=docking, ...
    query : str | Any
        Search keyword to filter by name, identifier, or description. E.g., 'caspase'...
    max_results : int
        Maximum results to return (default: 50, max: 400 covers all classes)
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
            "operation": operation,
            "motif_type": motif_type,
            "query": query,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ELM_list_classes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ELM_list_classes"]
