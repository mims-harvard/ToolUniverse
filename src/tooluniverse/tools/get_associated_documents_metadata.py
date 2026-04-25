"""
get_associated_documents_metadata

Obtains metadata for documents associated with an application, such as publications and grants.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_associated_documents_metadata(
    applicationNumberText: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Obtains metadata for documents associated with an application, such as publications and grants.

    Parameters
    ----------
    applicationNumberText : str
        The application number of the patent.
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
            "name": "get_associated_documents_metadata",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["get_associated_documents_metadata"]
