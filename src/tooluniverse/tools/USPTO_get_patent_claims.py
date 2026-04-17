"""
USPTO_get_patent_claims

Extract the full text of every claim from a granted US patent. Returns each claim with its number...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USPTO_get_patent_claims(
    applicationNumberText: Optional[str] = None,
    patent_number: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Extract the full text of every claim from a granted US patent. Returns each claim with its number...

    Parameters
    ----------
    applicationNumberText : str
        The application number (e.g., '14966067'). Provide this OR patent_number.
    patent_number : str
        Patent number in any format (e.g., 'US9629826B2'). Will be resolved to applic...
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
        "applicationNumberText": applicationNumberText,
                "patent_number": patent_number
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USPTO_get_patent_claims",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["USPTO_get_patent_claims"]
