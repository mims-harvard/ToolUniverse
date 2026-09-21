"""
PharmacoDB_get_compound

Get detailed information about a compound/drug from PharmacoDB, including chemical annotations (S...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_compound(
    operation: Optional[str] = "get_compound",
    compound_name: Optional[str] = None,
    compound_id: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a compound/drug from PharmacoDB, including chemical annotations (S...

    Parameters
    ----------
    operation : str
        Operation type
    compound_name : str
        Compound name (e.g., 'Paclitaxel', 'Erlotinib'). Mutually exclusive with comp...
    compound_id : int
        PharmacoDB compound database ID (e.g., 49658 for Paclitaxel). Mutually exclus...
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
            "compound_name": compound_name,
            "compound_id": compound_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_compound"]
