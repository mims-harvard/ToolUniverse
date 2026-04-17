"""
USPTO_get_patent_assignment

Get the chain of title (ownership history) for a US patent application. Returns every assignment ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USPTO_get_patent_assignment(
    applicationNumberText: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the chain of title (ownership history) for a US patent application. Returns every assignment ...

    Parameters
    ----------
    applicationNumberText : str
        The application number of the patent (e.g., '14966067'). This is NOT the pate...
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
    _args = {k: v for k, v in {
        "applicationNumberText": applicationNumberText
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USPTO_get_patent_assignment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["USPTO_get_patent_assignment"]
