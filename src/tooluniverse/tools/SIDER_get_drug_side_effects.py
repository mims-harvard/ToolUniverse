"""
SIDER_get_drug_side_effects

Get the list of known side effects for a drug from SIDER, including frequency data when available...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIDER_get_drug_side_effects(
    operation: str,
    drug_name: Optional[str | Any] = None,
    sider_drug_id: Optional[str | Any] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the list of known side effects for a drug from SIDER, including frequency data when available...

    Parameters
    ----------
    operation : str
        Operation type
    drug_name : str | Any
        Drug name (e.g., 'ibuprofen', 'metformin'). Will search SIDER and use first m...
    sider_drug_id : str | Any
        SIDER drug ID (PubChem CID) from SIDER_search_drug results (e.g., '3672' for ...
    limit : int
        Maximum number of side effects to return (default: 50)
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
    _args = {k: v for k, v in {
        "operation": operation,
                "drug_name": drug_name,
                "sider_drug_id": sider_drug_id,
                "limit": limit
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SIDER_get_drug_side_effects",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["SIDER_get_drug_side_effects"]
