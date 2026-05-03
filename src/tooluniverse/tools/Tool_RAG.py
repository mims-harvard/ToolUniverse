"""
Tool_RAG

Retrieve related tools from the toolbox based on the provided description
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Tool_RAG(
    description: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve related tools from the toolbox based on the provided description

    Parameters
    ----------
    description : str
        The description of the tool capability required.
    limit : int
        The number of tools to retrieve (default: 10)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"description": description, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Tool_RAG",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Tool_RAG"]
