"""
FDA_OrangeBook_get_approval_history

Get complete approval history for a drug application including original approval date, supplement...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_OrangeBook_get_approval_history(
    application_number: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get complete approval history for a drug application including original approval date, supplement...

    Parameters
    ----------
    operation : str
        Operation type (fixed)
    application_number : str
        FDA application number (e.g., 'NDA020402')
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
            "operation": operation,
            "application_number": application_number,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_OrangeBook_get_approval_history",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_OrangeBook_get_approval_history"]
