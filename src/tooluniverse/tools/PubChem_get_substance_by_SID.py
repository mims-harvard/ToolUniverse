"""
PubChem_get_substance_by_SID

Retrieve a PubChem SUBSTANCE (SID, depositor-level) record by its Substance ID. Unlike the CID/co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_get_substance_by_SID(
    sid: int | str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a PubChem SUBSTANCE (SID, depositor-level) record by its Substance ID. Unlike the CID/co...

    Parameters
    ----------
    sid : int | str
        PubChem Substance ID (SID), a positive integer, e.g., 223766453.
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
    _args = {k: v for k, v in {"sid": sid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_get_substance_by_SID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_get_substance_by_SID"]
