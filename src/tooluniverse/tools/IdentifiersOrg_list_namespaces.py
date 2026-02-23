"""
IdentifiersOrg_list_namespaces

List all registered namespaces in the Identifiers.org registry with pagination. Returns database ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IdentifiersOrg_list_namespaces(
    page: Optional[int] = 0,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all registered namespaces in the Identifiers.org registry with pagination. Returns database ...

    Parameters
    ----------
    page : int
        Page number (0-based). Default: 0.
    size : int
        Results per page. Default: 20.
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
            "name": "IdentifiersOrg_list_namespaces",
            "arguments": {"page": page, "size": size},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IdentifiersOrg_list_namespaces"]
