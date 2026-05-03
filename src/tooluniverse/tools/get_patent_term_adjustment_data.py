"""
get_patent_term_adjustment_data

Obtains the patent term adjustment details for a given application number.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_patent_term_adjustment_data(
    applicationNumberText: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Obtains the patent term adjustment details for a given application number.

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

    return get_shared_client().run_one_function(
        {
            "name": "get_patent_term_adjustment_data",
            "arguments": {"applicationNumberText": applicationNumberText},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_patent_term_adjustment_data"]
