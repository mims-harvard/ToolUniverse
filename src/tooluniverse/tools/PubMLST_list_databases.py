"""
PubMLST_list_databases

List the organism groups in PubMLST (University of Oxford), the reference resource for multilocus...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMLST_list_databases(
    query: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any] | dict[str, Any]:
    """
    List the organism groups in PubMLST (University of Oxford), the reference resource for multilocus...

    Parameters
    ----------
    query : str
        Text to find in the group name or description, e.g. 'neisseria', 'aureus'. Om...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any] | dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"query": query}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubMLST_list_databases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMLST_list_databases"]
