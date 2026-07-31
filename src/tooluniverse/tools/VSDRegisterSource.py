"""
VSDRegisterSource

Explicitly probe and persist an allowlisted HTTPS JSON source. Only GET requests are supported; p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VSDRegisterSource(
    source_id: str,
    endpoint: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    default_params: Optional[dict[str, Any]] = None,
    replace: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Explicitly probe and persist an allowlisted HTTPS JSON source. Only GET requests are supported; p...

    Parameters
    ----------
    source_id : str
        Stable lowercase identifier for the persisted source.
    endpoint : str
        Allowlisted HTTPS JSON endpoint to probe and persist.
    name : str
        Human-readable source name.
    description : str
        Provider-neutral description of the scientific source.
    default_params : dict[str, Any]
        Non-secret scalar GET parameters used for probing and future queries.
    replace : bool
        Replace an existing registration with the same source_id. Defaults to false, ...
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
        for k, v in {
            "source_id": source_id,
            "endpoint": endpoint,
            "name": name,
            "description": description,
            "default_params": default_params,
            "replace": replace,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VSDRegisterSource",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDRegisterSource"]
