"""
NASANED_lookup_object

Look up an extragalactic astronomical object by name in the NASA/IPAC Extragalactic Database (NED...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NASANED_lookup_object(
    name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up an extragalactic astronomical object by name in the NASA/IPAC Extragalactic Database (NED...

    Parameters
    ----------
    name : str
        Object name in NED format. Examples: 'NGC 1300', 'M31', 'Andromeda Galaxy', '...
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
    _args = {k: v for k, v in {"name": name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NASANED_lookup_object",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NASANED_lookup_object"]
