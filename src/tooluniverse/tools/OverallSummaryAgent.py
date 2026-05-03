"""
OverallSummaryAgent

AI agent that generates comprehensive overall summary of multi-agent search results
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OverallSummaryAgent(
    user_query: str,
    user_intent: str,
    total_papers: str,
    total_plans: str,
    iterations: str,
    plan_summaries: str,
    context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[str]:
    """
    AI agent that generates comprehensive overall summary of multi-agent search results

    Parameters
    ----------
    user_query : str
        The original research query
    user_intent : str
        The analyzed user intent
    total_papers : str
        Total number of papers found
    total_plans : str
        Total number of search plans executed
    iterations : str
        Number of iterations performed
    plan_summaries : str
        Summaries of all search plans
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
        for k, v in {
            "user_query": user_query,
            "user_intent": user_intent,
            "total_papers": total_papers,
            "total_plans": total_plans,
            "iterations": iterations,
            "plan_summaries": plan_summaries,
            "context": context,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OverallSummaryAgent",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OverallSummaryAgent"]
