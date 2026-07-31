"""
VSDQuerySource

Run a bounded, DNS-pinned HTTPS GET against one explicitly registered VSD JSON source. Redirects,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VSDQuerySource(
    source_id: str,
    params: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run a bounded, DNS-pinned HTTPS GET against one explicitly registered VSD JSON source. Redirects,...

    Parameters
    ----------
    source_id : str
        Previously registered VSD source identifier.
    params : dict[str, Any]
        Non-secret scalar GET parameters merged with the source defaults.
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
        for k, v in {"source_id": source_id, "params": params}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VSDQuerySource",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDQuerySource"]
