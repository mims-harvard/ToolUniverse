"""
ResultSummarizerAgent

AI agent that summarizes search results for research plans
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ResultSummarizerAgent(
    plan_title: str,
    plan_description: str,
    paper_count: str,
    papers_text: str,
    context: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[str]:
    """
    AI agent that summarizes search results for research plans

    Parameters
    ----------
    plan_title : str
        The title of the search plan
    plan_description : str
        The description of the search plan
    paper_count : str
        Number of papers found
    papers_text : str
        Formatted text of the papers to summarize
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
            "plan_title": plan_title,
            "plan_description": plan_description,
            "paper_count": paper_count,
            "papers_text": papers_text,
            "context": context,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ResultSummarizerAgent",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ResultSummarizerAgent"]
