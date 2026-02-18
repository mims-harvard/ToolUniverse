"""
ToolOutputSummarizer

AI-powered tool for summarizing long tool outputs, focusing on key information relevant to the or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolOutputSummarizer(
    tool_output: str,
    query_context: str,
    tool_name: str,
    focus_areas: Optional[str] = "key_findings_and_results",
    max_length: Optional[int] = 32000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    AI-powered tool for summarizing long tool outputs, focusing on key information relevant to the or...

    Parameters
    ----------
    tool_output : str
        The original tool output to be summarized
    query_context : str
        Context about the original query that triggered the tool
    tool_name : str
        Name of the tool that generated the output
    focus_areas : str
        Specific areas to focus on in the summary
    max_length : int
        Maximum length of the summary in characters
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
            "name": "ToolOutputSummarizer",
            "arguments": {
                "tool_output": tool_output,
                "query_context": query_context,
                "tool_name": tool_name,
                "focus_areas": focus_areas,
                "max_length": max_length,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolOutputSummarizer"]
