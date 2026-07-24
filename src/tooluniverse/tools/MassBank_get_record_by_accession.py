"""
MassBank_get_record_by_accession

Retrieve a complete MassBank Europe spectrum record by its accession identifier. Returns the full...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MassBank_get_record_by_accession(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a complete MassBank Europe spectrum record by its accession identifier. Returns the full...

    Parameters
    ----------
    accession : str
        MassBank record accession identifier (e.g., 'MSBNK-Athens_Univ-AU276601', 'MS...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MassBank_get_record_by_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MassBank_get_record_by_accession"]
