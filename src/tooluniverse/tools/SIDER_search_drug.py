"""
SIDER_search_drug

Search the SIDER drug side effects database for a drug by name. Returns matching drugs with SIDER...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIDER_search_drug(
    operation: str,
    drug_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the SIDER drug side effects database for a drug by name. Returns matching drugs with SIDER...

    Parameters
    ----------
    operation : str
        Operation type
    drug_name : str
        Drug name to search for (e.g., 'aspirin', 'ibuprofen', 'metformin', 'warfarin')
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
        for k, v in {"operation": operation, "drug_name": drug_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIDER_search_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIDER_search_drug"]
