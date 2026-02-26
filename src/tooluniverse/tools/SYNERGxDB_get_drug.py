"""
SYNERGxDB_get_drug

Get detailed information about a specific drug in SYNERGxDB by its database ID. Returns drug name...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SYNERGxDB_get_drug(
    operation: str,
    drug_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific drug in SYNERGxDB by its database ID. Returns drug name...

    Parameters
    ----------
    operation : str
        Operation type
    drug_id : int
        SYNERGxDB drug ID (e.g., 11 for Bortezomib)
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
            "name": "SYNERGxDB_get_drug",
            "arguments": {"operation": operation, "drug_id": drug_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SYNERGxDB_get_drug"]
