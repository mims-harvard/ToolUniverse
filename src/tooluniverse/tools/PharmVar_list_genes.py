"""
PharmVar_list_genes

List all pharmacogenes curated by PharmVar (Pharmacogene Variation Consortium). PharmVar is the a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmVar_list_genes(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all pharmacogenes curated by PharmVar (Pharmacogene Variation Consortium). PharmVar is the a...

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
        {"name": "PharmVar_list_genes", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmVar_list_genes"]
