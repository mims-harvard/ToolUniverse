"""
RxNorm_get_ndc_properties

Get product and package identification metadata for a National Drug Code (NDC) from the NLM RxNor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxNorm_get_ndc_properties(
    ndc: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get product and package identification metadata for a National Drug Code (NDC) from the NLM RxNor...

    Parameters
    ----------
    ndc : str
        National Drug Code. Accepts hyphenated (e.g., '0781-1506-10') or plain-digit ...
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
            "name": "RxNorm_get_ndc_properties",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxNorm_get_ndc_properties"]
