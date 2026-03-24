"""
AOPWiki_get_aop

Get detailed information about a specific Adverse Outcome Pathway (AOP) from AOPWiki by AOP ID. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AOPWiki_get_aop(
    aop_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific Adverse Outcome Pathway (AOP) from AOPWiki by AOP ID. R...

    Parameters
    ----------
    aop_id : int
        AOP numeric identifier. Find IDs using AOPWiki_list_aops. Example: 3 (mitocho...
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
    _args = {k: v for k, v in {"aop_id": aop_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AOPWiki_get_aop",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AOPWiki_get_aop"]
