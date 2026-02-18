"""
MedicalTermNormalizer

Identifies and corrects misspelled drug or disease names, returning a list of plausible standardi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedicalTermNormalizer(
    raw_terms: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Identifies and corrects misspelled drug or disease names, returning a list of plausible standardi...

    Parameters
    ----------
    raw_terms : str
        A comma- or whitespace-separated string containing one misspelled drug or dis...
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
        {"name": "MedicalTermNormalizer", "arguments": {"raw_terms": raw_terms}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedicalTermNormalizer"]
