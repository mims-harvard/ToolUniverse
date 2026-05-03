"""
LOINC_get_code_details

Get detailed information for a specific LOINC code including full name, component, property, syst...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOINC_get_code_details(
    loinc_code: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific LOINC code including full name, component, property, syst...

    Parameters
    ----------
    loinc_code : str
        LOINC code identifier (e.g., '2093-3' for Cholesterol in Serum/Plasma, '4548-...
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
    _args = {k: v for k, v in {"loinc_code": loinc_code}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "LOINC_get_code_details",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOINC_get_code_details"]
