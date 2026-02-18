"""
ScientificTextSummarizer

Summarizes biomedical research texts, abstracts, or papers with specified length and focus areas....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ScientificTextSummarizer(
    text: str,
    summary_length: str,
    focus_area: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Summarizes biomedical research texts, abstracts, or papers with specified length and focus areas....

    Parameters
    ----------
    text : str
        The biomedical text, abstract, or paper content to be summarized.
    summary_length : str
        Desired length of summary (e.g., '50', '100', '200 words').
    focus_area : str
        What to focus on in the summary (e.g., 'methodology', 'results', 'clinical im...
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
            "name": "ScientificTextSummarizer",
            "arguments": {
                "text": text,
                "summary_length": summary_length,
                "focus_area": focus_area,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ScientificTextSummarizer"]
