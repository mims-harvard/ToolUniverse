"""
ICD10_get_code_info

Get detailed information about a specific ICD-10-CM code including full description, chapter, and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ICD10_get_code_info(
    code: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific ICD-10-CM code including full description, chapter, and...

    Parameters
    ----------
    code : str
        ICD-10-CM code (e.g., 'E11.9', 'I10', 'J44.0')
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
    _args = {k: v for k, v in {"code": code}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ICD10_get_code_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ICD10_get_code_info"]
