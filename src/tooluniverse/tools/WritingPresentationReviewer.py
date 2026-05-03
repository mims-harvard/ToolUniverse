"""
WritingPresentationReviewer

Assesses clarity, organization, grammar, and visual presentation quality.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WritingPresentationReviewer(
    manuscript_text: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Assesses clarity, organization, grammar, and visual presentation quality.

    Parameters
    ----------
    manuscript_text : str

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
        k: v for k, v in {"manuscript_text": manuscript_text}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WritingPresentationReviewer",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WritingPresentationReviewer"]
