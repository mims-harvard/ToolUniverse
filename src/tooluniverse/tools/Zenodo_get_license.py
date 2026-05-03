"""
Zenodo_get_license

Get detailed information about a specific license by its license ID. Returns complete license met...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Zenodo_get_license(
    license_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific license by its license ID. Returns complete license met...

    Parameters
    ----------
    license_id : str
        License identifier (e.g., 'cc-by-4.0', 'MIT', 'Apache-2.0', 'GPL-3.0'). Find ...
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
    _args = {k: v for k, v in {"license_id": license_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Zenodo_get_license",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Zenodo_get_license"]
