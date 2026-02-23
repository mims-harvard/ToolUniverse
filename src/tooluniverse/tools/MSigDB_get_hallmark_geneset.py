"""
MSigDB_get_hallmark_geneset

Retrieve a Hallmark gene set from MSigDB. The Hallmark collection (H) contains 50 gene sets repre...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MSigDB_get_hallmark_geneset(
    pathway_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a Hallmark gene set from MSigDB. The Hallmark collection (H) contains 50 gene sets repre...

    Parameters
    ----------
    pathway_name : str
        Hallmark pathway name without the 'HALLMARK_' prefix (will be auto-prepended)...
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
        {
            "name": "MSigDB_get_hallmark_geneset",
            "arguments": {"pathway_name": pathway_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MSigDB_get_hallmark_geneset"]
