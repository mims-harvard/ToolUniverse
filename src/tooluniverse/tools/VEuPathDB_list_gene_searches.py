"""
VEuPathDB_list_gene_searches

List all available gene search strategies in VEuPathDB. Returns the search types that can be used...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VEuPathDB_list_gene_searches(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all available gene search strategies in VEuPathDB. Returns the search types that can be used...

    Parameters
    ----------
    No parameters
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

    return get_shared_client().run_one_function(
        {"name": "VEuPathDB_list_gene_searches", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VEuPathDB_list_gene_searches"]
