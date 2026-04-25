"""
Unpaywall_get_full_text_url

Retrieve full-text PDF and landing page URLs for a scholarly article via its DOI. Returns the bes...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Unpaywall_get_full_text_url(
    doi: str,
    email: Optional[str] = "tools@tooluniverse.org",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve full-text PDF and landing page URLs for a scholarly article via its DOI. Returns the bes...

    Parameters
    ----------
    doi : str
        DOI (Digital Object Identifier) of the article, e.g. '10.1038/nature12373'.
    email : str
        Contact email for Unpaywall API polite pool. Defaults to 'tools@tooluniverse....
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
    _args = {k: v for k, v in {"doi": doi, "email": email}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Unpaywall_get_full_text_url",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Unpaywall_get_full_text_url"]
