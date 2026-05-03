"""
BRENDA_get_enzyme_info

Get general enzyme information from BRENDA by EC number. Returns enzyme name, systematic name, an...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BRENDA_get_enzyme_info(
    operation: str,
    ec_number: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get general enzyme information from BRENDA by EC number. Returns enzyme name, systematic name, an...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_enzyme_info)
    ec_number : str
        EC number (e.g., 1.1.1.1)
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

    return get_shared_client().run_one_function(
        {
            "name": "BRENDA_get_enzyme_info",
            "arguments": {"operation": operation, "ec_number": ec_number},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BRENDA_get_enzyme_info"]
