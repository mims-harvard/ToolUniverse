"""
WFGY_triage_llm_rag_failure

Generate a structured prompt bundle (system + user message) to triage LLM/RAG failures using the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WFGY_triage_llm_rag_failure(
    bug_description: str,
    audience: Optional[str] = "engineer",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generate a structured prompt bundle (system + user message) to triage LLM/RAG failures using the ...

    Parameters
    ----------
    bug_description : str
        Free-text description of the LLM/RAG incident. Include the user prompt, retri...
    audience : str
        Target audience for the prompt bundle tone. 'beginner' uses plain language, '...
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
        for k, v in {"bug_description": bug_description, "audience": audience}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WFGY_triage_llm_rag_failure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WFGY_triage_llm_rag_failure"]
