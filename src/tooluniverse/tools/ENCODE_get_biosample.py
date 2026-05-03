"""
ENCODE_get_biosample

Get detailed metadata for a specific ENCODE biosample by its accession ID. Returns comprehensive ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCODE_get_biosample(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed metadata for a specific ENCODE biosample by its accession ID. Returns comprehensive ...

    Parameters
    ----------
    accession : str
        ENCODE biosample accession identifier (format: ENCBS######, e.g., 'ENCBS000AA...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ENCODE_get_biosample",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCODE_get_biosample"]
