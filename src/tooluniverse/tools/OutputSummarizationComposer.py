"""
OutputSummarizationComposer

Composes output summarization workflow by chunking long outputs, processing each chunk with AI su...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OutputSummarizationComposer(
    tool_output: str,
    query_context: str,
    tool_name: str,
    chunk_size: Optional[int] = 30000,
    focus_areas: Optional[str] = "key_findings_and_results",
    max_summary_length: Optional[int] = 10000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Composes output summarization workflow by chunking long outputs, processing each chunk with AI su...

    Parameters
    ----------
    tool_output : str
        The original tool output to be summarized
    query_context : str
        Context about the original query
    tool_name : str
        Name of the tool that generated the output
    chunk_size : int
        Size of each chunk for processing
    focus_areas : str
        Areas to focus on in summarization
    max_summary_length : int
        Maximum length of final summary
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
            "tool_output": tool_output,
            "query_context": query_context,
            "tool_name": tool_name,
            "chunk_size": chunk_size,
            "focus_areas": focus_areas,
            "max_summary_length": max_summary_length,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OutputSummarizationComposer",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OutputSummarizationComposer"]
