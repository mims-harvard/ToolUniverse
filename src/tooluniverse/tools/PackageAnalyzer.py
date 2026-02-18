"""
PackageAnalyzer

Analyzes package candidates and recommends the best options based on quality metrics and suitability
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PackageAnalyzer(
    tool_description: str,
    package_candidates: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyzes package candidates and recommends the best options based on quality metrics and suitability

    Parameters
    ----------
    tool_description : str
        Description of the tool being generated
    package_candidates : str
        JSON string containing package candidates with their metadata (from PyPI, sea...
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
            "name": "PackageAnalyzer",
            "arguments": {
                "tool_description": tool_description,
                "package_candidates": package_candidates,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PackageAnalyzer"]
