"""
call_agentic_human

Produces a concise, practical answer that emulates how a well-informed human would respond to the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def call_agentic_human(
    question: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Produces a concise, practical answer that emulates how a well-informed human would respond to the...

    Parameters
    ----------
    question : str
        The user's question to be answered in a human-like manner.
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
        {"name": "call_agentic_human", "arguments": {"question": question}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["call_agentic_human"]
