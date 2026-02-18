"""
IntentAnalyzerAgent

AI agent that analyzes user research intent and creates comprehensive search plans
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IntentAnalyzerAgent(
    user_query: str,
    context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[str]:
    """
    AI agent that analyzes user research intent and creates comprehensive search plans

    Parameters
    ----------
    user_query : str
        The research query to analyze
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

    return get_shared_client().run_one_function(
        {
            "name": "IntentAnalyzerAgent",
            "arguments": {"user_query": user_query, "context": context},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IntentAnalyzerAgent"]
