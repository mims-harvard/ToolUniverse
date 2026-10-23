"""
MGnify_search_genomes

Search the MGnify genome catalog by GTDB taxonomy lineage with explicit page pagination. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGnify_search_genomes(
    taxonomy: Optional[str] = None,
    page: Optional[int] = 1,
    page_size: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the MGnify genome catalog by GTDB taxonomy lineage with explicit page pagination. Returns ...

    Parameters
    ----------
    taxonomy : str
        GTDB taxonomy lineage filter, matched anywhere in the lineage. Examples: 'Bac...
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
        for k, v in {"taxonomy": taxonomy, "page": page, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGnify_search_genomes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGnify_search_genomes"]
