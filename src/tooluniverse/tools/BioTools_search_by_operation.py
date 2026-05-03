"""
BioTools_search_by_operation

Search the ELIXIR Bio.tools registry for bioinformatics tools by EDAM operation (what the tool do...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioTools_search_by_operation(
    operation: str,
    page: Optional[int] = 1,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the ELIXIR Bio.tools registry for bioinformatics tools by EDAM operation (what the tool do...

    Parameters
    ----------
    operation : str
        EDAM operation name describing what the tool does. Examples: 'Sequence alignm...
    page : int
        Page number (1-based). Default: 1.
    size : int
        Results per page (1-50). Default: 10.
    format : str
        Response format. Must be 'json'.
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
            "operation": operation,
            "page": page,
            "size": size,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioTools_search_by_operation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioTools_search_by_operation"]
