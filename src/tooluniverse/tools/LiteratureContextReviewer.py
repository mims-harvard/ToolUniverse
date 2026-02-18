"""
LiteratureContextReviewer

Reviews coverage, relevance, and critical synthesis of prior scholarship.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LiteratureContextReviewer(
    paper_title: str,
    literature_review: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Reviews coverage, relevance, and critical synthesis of prior scholarship.

    Parameters
    ----------
    paper_title : str

    literature_review : str
        Full literature-review text
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
            "name": "LiteratureContextReviewer",
            "arguments": {
                "paper_title": paper_title,
                "literature_review": literature_review,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LiteratureContextReviewer"]
