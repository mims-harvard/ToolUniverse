"""
PharmacoDB_get_compound

Get detailed information about a compound/drug from PharmacoDB, including chemical annotations (S...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_get_compound(
    operation: str,
    compound_name: Optional[str | Any] = None,
    compound_id: Optional[int | Any] = None,
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
    compound_name : str | Any
        Compound name (e.g., 'Paclitaxel', 'Erlotinib'). Mutually exclusive with comp...
    compound_id : int | Any
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

    return get_shared_client().run_one_function(
        {
            "name": "PharmacoDB_get_compound",
            "arguments": {
                "operation": operation,
                "compound_name": compound_name,
                "compound_id": compound_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_get_compound"]
