"""
MGnify_list_biomes

Browse the MGnify biome hierarchy with explicit page pagination. Returns biome identifiers, names...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_list_biomes(
    depth: Optional[int] = None,
    lineage: Optional[str] = None,
    page: Optional[int] = 1,
    page_size: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Browse the MGnify biome hierarchy with explicit page pagination. Returns biome identifiers, names...

    Parameters
    ----------
    depth : int
        Depth of the biome lineage to keep, counting 'root' as 1 (so 'root:Engineered...
    lineage : str
        List this biome and all biomes below it, e.g. 'root:Host-associated:Human' (u...
    page : int
        One-based result page. Continue with metadata.next_page.
    page_size : int
        Results per page (default 25, range 1-100).
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
    _args = {
        k: v
        for k, v in {
            "depth": depth,
            "lineage": lineage,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_list_biomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_list_biomes"]
