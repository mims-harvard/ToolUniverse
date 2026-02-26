"""
SIDER_search_side_effect

Search for a side effect by name in SIDER. Returns matching side effects with their MedDRA codes ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SIDER_search_side_effect(
    operation: str,
    side_effect_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for a side effect by name in SIDER. Returns matching side effects with their MedDRA codes ...

    Parameters
    ----------
    operation : str
        Operation type
    side_effect_name : str
        Side effect name to search (e.g., 'headache', 'nausea', 'diarrhea', 'liver')
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
            "name": "SIDER_search_side_effect",
            "arguments": {"operation": operation, "side_effect_name": side_effect_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SIDER_search_side_effect"]
