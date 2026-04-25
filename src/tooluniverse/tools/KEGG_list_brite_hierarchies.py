"""
KEGG_list_brite_hierarchies

List all available KEGG BRITE hierarchy classification files. KEGG BRITE is a collection of hiera...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_list_brite_hierarchies(
    
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all available KEGG BRITE hierarchy classification files. KEGG BRITE is a collection of hiera...

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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_list_brite_hierarchies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["KEGG_list_brite_hierarchies"]
