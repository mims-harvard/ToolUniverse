"""
PROSITE_get_entry

Retrieve a PROSITE protein motif/domain entry by its accession number. Returns the entry name, de...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PROSITE_get_entry(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a PROSITE protein motif/domain entry by its accession number. Returns the entry name, de...

    Parameters
    ----------
    accession : str
        PROSITE accession number starting with 'PS'. Examples: 'PS00001' (N-glycosyla...
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
    _args = {k: v for k, v in {
        "accession": accession
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PROSITE_get_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["PROSITE_get_entry"]
