"""
QuestionRephraser

Generates three distinct paraphrases of a given question while ensuring answer options remain val...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def QuestionRephraser(
    question: str,
    options: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generates three distinct paraphrases of a given question while ensuring answer options remain val...

    Parameters
    ----------
    question : str
        The original question text to be rephrased
    options : str
        Answer options (e.g., multiple choice options) that should remain valid for t...
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
        for k, v in {"question": question, "options": options}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "QuestionRephraser",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["QuestionRephraser"]
