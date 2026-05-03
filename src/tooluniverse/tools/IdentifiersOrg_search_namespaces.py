"""
IdentifiersOrg_search_namespaces

Search the Identifiers.org registry for namespaces (database prefixes) by keyword. Returns namesp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IdentifiersOrg_search_namespaces(
    content: str,
    page: Optional[int] = 0,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Identifiers.org registry for namespaces (database prefixes) by keyword. Returns namesp...

    Parameters
    ----------
    content : str
        Search term to find in namespace prefixes. Examples: 'pdb', 'gene', 'protein'...
    page : int
        Page number (0-based). Default: 0.
    size : int
        Results per page. Default: 10.
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
        for k, v in {"content": content, "page": page, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IdentifiersOrg_search_namespaces",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IdentifiersOrg_search_namespaces"]
