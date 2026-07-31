"""
RxNorm_get_ndc_status_history

Get the historical status and RxCUI remapping timeline for an 11-digit National Drug Code (NDC) f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxNorm_get_ndc_status_history(
    ndc: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the historical status and RxCUI remapping timeline for an 11-digit National Drug Code (NDC) f...

    Parameters
    ----------
    ndc : str
        National Drug Code, 11-digit. Accepts hyphenated (e.g., '00093-0058-01') or p...
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
    _args = {k: v for k, v in {"ndc": ndc}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "RxNorm_get_ndc_status_history",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxNorm_get_ndc_status_history"]
