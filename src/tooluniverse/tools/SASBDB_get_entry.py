"""
SASBDB_get_entry

Get detailed metadata for a SASBDB small-angle scattering entry by its accession code. Returns ex...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SASBDB_get_entry(
    sasbdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed metadata for a SASBDB small-angle scattering entry by its accession code. Returns ex...

    Parameters
    ----------
    sasbdb_id : str
        SASBDB accession code (e.g. SASDCZ9, SASDFZ9)
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
    _args = {k: v for k, v in {"sasbdb_id": sasbdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SASBDB_get_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SASBDB_get_entry"]
