"""
ROR_search_organizations

Search the Research Organization Registry (ROR) for research institutions, universities, companie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ROR_search_organizations(
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Research Organization Registry (ROR) for research institutions, universities, companie...

    Parameters
    ----------
    query : str
        Search query for organization name, acronym, or keyword (e.g., 'MIT', 'Harvar...
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
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ROR_search_organizations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ROR_search_organizations"]
