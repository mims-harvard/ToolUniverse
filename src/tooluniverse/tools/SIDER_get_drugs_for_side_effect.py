"""
SIDER_get_drugs_for_side_effect

Find all drugs associated with a specific side effect in SIDER. Returns drugs known to cause the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIDER_get_drugs_for_side_effect(
    operation: str,
    meddra_code: Optional[str | Any] = None,
    side_effect_name: Optional[str | Any] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find all drugs associated with a specific side effect in SIDER. Returns drugs known to cause the ...

    Parameters
    ----------
    operation : str
        Operation type
    meddra_code : str | Any
        MedDRA concept code / UMLS CUI (e.g., 'C0018681' for headache, 'C0027497' for...
    side_effect_name : str | Any
        Side effect name to search (e.g., 'headache', 'nausea', 'diarrhea'). Will sea...
    limit : int
        Maximum number of drugs to return (default: 50)
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
            "meddra_code": meddra_code,
            "side_effect_name": side_effect_name,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SIDER_get_drugs_for_side_effect",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIDER_get_drugs_for_side_effect"]
