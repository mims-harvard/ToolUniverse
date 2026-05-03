"""
ChEMBL_get_compound_record

Get compound record information by ChEMBL compound record ID.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_compound_record(
    compound_record_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get compound record information by ChEMBL compound record ID.

    Parameters
    ----------
    compound_record_id : str
        ChEMBL compound record ID
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
    _args = {
        k: v
        for k, v in {"compound_record_id": compound_record_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_compound_record",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_compound_record"]
