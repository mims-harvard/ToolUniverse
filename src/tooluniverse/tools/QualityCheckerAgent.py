"""
QualityCheckerAgent

AI agent that checks search result quality and suggests improvements
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def QualityCheckerAgent(
    plans_analysis: str,
    context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[str]:
    """
    AI agent that checks search result quality and suggests improvements

    Parameters
    ----------
    plans_analysis : str
        Analysis of current search plans and their quality scores
    context : str
        Context information from previous steps
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[str]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"plans_analysis": plans_analysis, "context": context}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "QualityCheckerAgent",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["QualityCheckerAgent"]
