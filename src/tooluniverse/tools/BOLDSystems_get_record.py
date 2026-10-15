"""
BOLDSystems_get_record

Retrieve a single BOLD (Barcode of Life Data System) DNA barcode record by its BOLD process ID. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BOLDSystems_get_record(
    process_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a single BOLD (Barcode of Life Data System) DNA barcode record by its BOLD process ID. R...

    Parameters
    ----------
    process_id : str
        BOLD process ID, e.g. 'ABRMM002-06'.
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
    _args = {k: v for k, v in {"process_id": process_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BOLDSystems_get_record",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BOLDSystems_get_record"]
