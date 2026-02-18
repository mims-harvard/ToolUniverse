"""
DataAnalysisValidityReviewer

Checks statistical choices, assumption testing, and reporting transparency.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataAnalysisValidityReviewer(
    analysis_section: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Checks statistical choices, assumption testing, and reporting transparency.

    Parameters
    ----------
    analysis_section : str

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
            "name": "DataAnalysisValidityReviewer",
            "arguments": {"analysis_section": analysis_section},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DataAnalysisValidityReviewer"]
