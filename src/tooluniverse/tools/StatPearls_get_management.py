"""
StatPearls_get_management

How a disease, injury, condition or surgical problem is treated and managed, in one call: finds t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def StatPearls_get_management(
    condition: str,
    limit: Optional[int] = 2,
    include_evaluation: Optional[bool] = False,
    include_archived: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    How a disease, injury, condition or surgical problem is treated and managed, in one call: finds t...

    Parameters
    ----------
    condition : str
        Name of the disease, injury, condition, procedure or drug, e.g. 'scaphoid fra...
    limit : int
        Number of chapters to return (1-3, default 2).
    include_evaluation : bool
        Also return each chapter's Evaluation (diagnostic work-up) section (default f...
    include_archived : bool
        Also consider archived chapters, which the publisher no longer maintains (def...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "condition": condition,
            "limit": limit,
            "include_evaluation": include_evaluation,
            "include_archived": include_archived,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "StatPearls_get_management",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["StatPearls_get_management"]
