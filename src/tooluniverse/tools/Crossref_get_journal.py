"""
Crossref_get_journal

Get metadata for a specific journal by its ISSN (International Standard Serial Number). Returns j...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_get_journal(
    issn: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Get metadata for a specific journal by its ISSN (International Standard Serial Number). Returns j...

    Parameters
    ----------
    issn : str
        Journal ISSN in format ####-#### (e.g., '1476-4687' for Nature, '1932-6203' f...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"issn": issn}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_get_journal",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_get_journal"]
