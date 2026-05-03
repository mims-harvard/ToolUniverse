"""
Zenodo_get_record

Get detailed metadata for a specific Zenodo record by its record ID. Returns comprehensive inform...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Zenodo_get_record(
    record_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed metadata for a specific Zenodo record by its record ID. Returns comprehensive inform...

    Parameters
    ----------
    record_id : int
        Zenodo record identifier (e.g., 1234567, 7654321). Find record IDs using Zeno...
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
    _args = {k: v for k, v in {"record_id": record_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Zenodo_get_record",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Zenodo_get_record"]
