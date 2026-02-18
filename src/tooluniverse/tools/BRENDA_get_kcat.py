"""
BRENDA_get_kcat

Get kcat (turnover number) values from BRENDA enzyme database. kcat is the maximum number of subs...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BRENDA_get_kcat(
    operation: str,
    ec_number: str,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get kcat (turnover number) values from BRENDA enzyme database. kcat is the maximum number of subs...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_kcat)
    ec_number : str
        EC number
    organism : str
        Optional organism filter
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
            "name": "BRENDA_get_kcat",
            "arguments": {
                "operation": operation,
                "ec_number": ec_number,
                "organism": organism,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BRENDA_get_kcat"]
